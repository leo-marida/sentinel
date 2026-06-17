"""Tests for the FastAPI HTTP layer: health, scan creation/retrieval, and approvals.

The Supabase client is never hit for real here — routes that use the `get_db`
dependency are exercised via FastAPI's dependency_overrides, while approvals.py
and stream.py (which call get_supabase() directly) are patched at the module
level they're imported into.
"""
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient
from postgrest.exceptions import APIError

from app.api.deps import get_db
from app.main import app


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


class TestCreateScan:
    def _db_returning_scan_row(self, scan_id="scan-1"):
        db = MagicMock()
        db.table.return_value.insert.return_value.execute.return_value.data = [
            {
                "id": scan_id,
                "repo_url": "https://github.com/owner/repo",
                "repo_name": "owner/repo",
                "status": "queued",
            }
        ]
        return db

    def test_rejects_non_github_url(self, client):
        response = client.post("/api/v1/scans", json={"repo_url": "https://gitlab.com/owner/repo"})
        assert response.status_code == 400

    def test_rejects_url_without_owner_and_repo(self, client):
        response = client.post("/api/v1/scans", json={"repo_url": "https://github.com/owner"})
        assert response.status_code == 400

    def test_creates_scan_and_dispatches_background_job(self, client, monkeypatch):
        app.dependency_overrides[get_db] = lambda: self._db_returning_scan_row()
        dispatched = {}
        monkeypatch.setattr(
            "app.api.routes.scans.run_async_in_thread",
            lambda coro_func, *args: dispatched.update(scan_id=args[0]),
        )

        response = client.post("/api/v1/scans", json={"repo_url": "https://github.com/owner/repo"})

        assert response.status_code == 201
        body = response.json()
        assert body == {
            "scan_id": "scan-1",
            "status": "queued",
            "repo_url": "https://github.com/owner/repo",
            "repo_name": "owner/repo",
        }
        assert dispatched["scan_id"] == "scan-1"

    def test_returns_500_when_insert_fails(self, client):
        db = MagicMock()
        db.table.return_value.insert.return_value.execute.return_value.data = []
        app.dependency_overrides[get_db] = lambda: db

        response = client.post("/api/v1/scans", json={"repo_url": "https://github.com/owner/repo"})

        assert response.status_code == 500

    def test_rate_limit_exceeded_after_five_requests(self, client, monkeypatch):
        app.dependency_overrides[get_db] = lambda: self._db_returning_scan_row()
        monkeypatch.setattr("app.api.routes.scans.run_async_in_thread", lambda *a, **kw: None)

        for _ in range(5):
            r = client.post("/api/v1/scans", json={"repo_url": "https://github.com/owner/repo"})
            assert r.status_code == 201

        r = client.post("/api/v1/scans", json={"repo_url": "https://github.com/owner/repo"})
        assert r.status_code == 429


class TestGetScan:
    def test_returns_scan_when_found(self, client):
        db = MagicMock()
        chain = db.table.return_value.select.return_value.eq.return_value.single
        chain.return_value.execute.return_value.data = {
            "id": "scan-1",
            "status": "complete",
        }
        app.dependency_overrides[get_db] = lambda: db

        response = client.get("/api/v1/scans/scan-1")

        assert response.status_code == 200
        assert response.json()["status"] == "complete"

    def test_returns_404_when_missing(self, client):
        db = MagicMock()
        chain = db.table.return_value.select.return_value.eq.return_value.single
        chain.return_value.execute.return_value.data = None
        app.dependency_overrides[get_db] = lambda: db

        response = client.get("/api/v1/scans/missing")

        assert response.status_code == 404

    def test_returns_404_when_postgrest_raises_for_zero_rows(self, client):
        """Real postgrest-py raises APIError on .single() with zero matching rows
        instead of returning data=None — this must still surface as 404, not 500.
        """
        db = MagicMock()
        chain = db.table.return_value.select.return_value.eq.return_value.single
        chain.return_value.execute.side_effect = APIError({"message": "no rows"})
        app.dependency_overrides[get_db] = lambda: db

        response = client.get("/api/v1/scans/missing")

        assert response.status_code == 404


class TestGetScanFindings:
    def test_returns_findings_list(self, client):
        db = MagicMock()
        chain = db.table.return_value.select.return_value.eq.return_value.order
        chain.return_value.execute.return_value.data = [{"id": "f1"}]
        app.dependency_overrides[get_db] = lambda: db

        response = client.get("/api/v1/scans/scan-1/findings")

        assert response.status_code == 200
        assert response.json() == [{"id": "f1"}]

    def test_returns_empty_list_when_data_is_none(self, client):
        db = MagicMock()
        chain = db.table.return_value.select.return_value.eq.return_value.order
        chain.return_value.execute.return_value.data = None
        app.dependency_overrides[get_db] = lambda: db

        response = client.get("/api/v1/scans/scan-1/findings")

        assert response.json() == []


_FINDING = {
    "id": "f1",
    "file_path": "a.py",
    "line_start": 1,
    "line_end": 1,
    "rule_id": "r1",
    "severity": "high",
    "title": "t",
    "description": "d",
    "raw_output": {},
    "ai_analysis": None,
    "remediation": None,
    "approval_status": "pending",
}


class TestSubmitApproval:
    def _patch_scan_status(self, monkeypatch, status):
        db = MagicMock()
        chain = db.table.return_value.select.return_value.eq.return_value.single
        chain.return_value.execute.return_value.data = (
            {"status": status} if status is not None else None
        )
        monkeypatch.setattr("app.api.routes.approvals.get_supabase", lambda: db)
        return db

    def test_404_when_scan_missing(self, client, monkeypatch):
        self._patch_scan_status(monkeypatch, status=None)

        response = client.post("/api/v1/scans/missing/approve", json={"decisions": []})

        assert response.status_code == 404

    def test_404_when_postgrest_raises_for_zero_rows(self, client, monkeypatch):
        """Real postgrest-py raises APIError on .single() with zero matching rows
        instead of returning data=None — this must still surface as 404, not 500.
        """
        db = MagicMock()
        chain = db.table.return_value.select.return_value.eq.return_value.single
        chain.return_value.execute.side_effect = APIError({"message": "no rows"})
        monkeypatch.setattr("app.api.routes.approvals.get_supabase", lambda: db)

        response = client.post("/api/v1/scans/missing/approve", json={"decisions": []})

        assert response.status_code == 404

    def test_409_when_not_awaiting_approval(self, client, monkeypatch):
        self._patch_scan_status(monkeypatch, status="complete")

        response = client.post("/api/v1/scans/scan-1/approve", json={"decisions": []})

        assert response.status_code == 409

    def test_resumes_graph_using_findings_from_checkpoint(self, client, monkeypatch):
        self._patch_scan_status(monkeypatch, status="awaiting_approval")
        graph_state = MagicMock()
        graph_state.values = {"findings": [dict(_FINDING)]}
        monkeypatch.setattr(
            "app.api.routes.approvals.sentinel_graph.aget_state",
            AsyncMock(return_value=graph_state),
        )
        dispatched = {}
        monkeypatch.setattr(
            "app.api.routes.approvals.run_async_in_thread",
            lambda coro_func, *args: dispatched.update(scan_id=args[0], findings=args[1]),
        )

        response = client.post(
            "/api/v1/scans/scan-1/approve",
            json={"decisions": [{"finding_id": "f1", "decision": "approved"}]},
        )

        assert response.status_code == 200
        assert response.json() == {
            "status": "resumed",
            "scan_id": "scan-1",
            "approved": 1,
            "rejected": 0,
        }
        assert dispatched["findings"][0]["approval_status"] == "approved"

    def test_falls_back_to_db_when_checkpoint_state_is_gone(self, client, monkeypatch):
        db = self._patch_scan_status(monkeypatch, status="awaiting_approval")
        monkeypatch.setattr(
            "app.api.routes.approvals.sentinel_graph.aget_state",
            AsyncMock(side_effect=RuntimeError("no checkpoint")),
        )
        db.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
            dict(_FINDING)
        ]
        dispatched = {}
        monkeypatch.setattr(
            "app.api.routes.approvals.run_async_in_thread",
            lambda coro_func, *args: dispatched.update(findings=args[1]),
        )

        response = client.post(
            "/api/v1/scans/scan-1/approve",
            json={"decisions": [{"finding_id": "f1", "decision": "rejected"}]},
        )

        assert response.status_code == 200
        assert dispatched["findings"][0]["approval_status"] == "rejected"
