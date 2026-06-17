"""Tests for the MCP server's tool listing and tool-call dispatch."""
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.mcp import server


async def test_list_tools_exposes_all_three_tools():
    tools = await server.list_tools()
    assert {t.name for t in tools} == {
        "fetch_github_repo",
        "create_ticket",
        "send_notification",
    }


async def test_fetch_github_repo_wraps_github_service(monkeypatch):
    fake_files = [{"path": "a.py", "content": "x = 1"}]
    monkeypatch.setattr(
        "app.mcp.server.fetch_repo_files", AsyncMock(return_value=fake_files)
    )

    result = await server.call_tool(
        "fetch_github_repo", {"repo_url": "https://github.com/owner/repo"}
    )

    assert len(result) == 1
    assert '"count": 1' in result[0].text


async def test_create_ticket_writes_ticket_id_to_supabase(monkeypatch):
    db = MagicMock()
    monkeypatch.setattr("app.mcp.server.get_supabase", lambda: db)

    result = await server.call_tool(
        "create_ticket",
        {
            "finding_id": "abcdef1234567890",
            "title": "t",
            "description": "d",
            "severity": "high",
        },
    )

    db.table.assert_called_with("findings")
    update_call = db.table.return_value.update.call_args.args[0]
    assert update_call["ticket_id"] == "SENTINEL-ABCDEF12"
    assert "ticket_created" in result[0].text


async def test_send_notification_delegates_to_notification_service(monkeypatch):
    sent = AsyncMock(return_value=True)
    monkeypatch.setattr("app.mcp.server.send_slack_notification", sent)

    result = await server.call_tool(
        "send_notification", {"message": "hello", "scan_id": "scan-1"}
    )

    sent.assert_awaited_once_with(message="hello", scan_id="scan-1")
    assert '"notified": true' in result[0].text


async def test_unknown_tool_raises_value_error():
    with pytest.raises(ValueError):
        await server.call_tool("not_a_real_tool", {})
