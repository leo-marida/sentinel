import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from supabase import Client

from app.agent.graph import sentinel_graph
from app.agent.state import SentinelState
from app.api.deps import get_db
from app.db.client import get_supabase
from app.utils.background import run_async_in_thread
from app.utils.security import check_rate_limit, validate_github_url

logger = logging.getLogger(__name__)
router = APIRouter()


class ScanRequest(BaseModel):
    repo_url: str


class ScanResponse(BaseModel):
    scan_id: str
    status: str
    repo_url: str
    repo_name: str


def _extract_repo_name(repo_url: str) -> str:
    parts = repo_url.rstrip("/").split("/")
    return f"{parts[-2]}/{parts[-1]}"


async def _run_graph(scan_id: str, repo_url: str, repo_name: str) -> None:
    """
    Run the LangGraph pipeline. Invoked via run_async_in_thread() in its own
    thread + event loop, isolated from FastAPI's main loop — the Supabase
    client used throughout this pipeline is synchronous and would otherwise
    block every other request for the pipeline's full duration.
    """
    logger.info("[graph] Starting pipeline for scan %s repo=%s", scan_id, repo_name)
    db = get_supabase()
    config = {"configurable": {"thread_id": scan_id}}
    initial_state = SentinelState(
        scan_id=scan_id,
        repo_url=repo_url,
        repo_name=repo_name,
        files=[],
        raw_findings=[],
        findings=[],
        approved_findings=[],
        report=None,
        current_node="start",
        error=None,
        stream_tokens=[],
    )
    try:
        await sentinel_graph.ainvoke(initial_state, config=config)

        state = await sentinel_graph.aget_state(config)
        findings = state.values.get("findings", []) if state else []
        logger.info("[graph] Graph paused with %d findings for scan %s", len(findings), scan_id)

        if findings:
            rows = [
                {
                    "id": f["id"],
                    "scan_id": scan_id,
                    "file_path": f["file_path"],
                    "line_start": f["line_start"],
                    "line_end": f["line_end"],
                    "rule_id": f["rule_id"],
                    "severity": f["severity"],
                    "title": f["title"],
                    "description": f["description"],
                    "raw_output": f["raw_output"],
                    "ai_analysis": f.get("ai_analysis"),
                    "approval_status": "pending",
                }
                for f in findings
            ]
            db.table("findings").insert(rows).execute()

        severity_counts: dict[str, int] = {
            "critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0
        }
        for f in findings:
            if f["severity"] in severity_counts:
                severity_counts[f["severity"]] += 1

        db.table("scans").update({
            "status": "awaiting_approval",
            "summary": {"total_findings": len(findings), **severity_counts},
        }).eq("id", scan_id).execute()
        logger.info("[graph] Scan %s reached awaiting_approval", scan_id)

    except Exception as e:
        logger.error("[graph] Scan %s failed: %s", scan_id, e, exc_info=True)
        try:
            db.table("scans").update({
                "status": "failed",
                "error_message": str(e),
            }).eq("id", scan_id).execute()
        except Exception as db_err:
            logger.error("[graph] Also failed to update scan status: %s", db_err)


@router.post("/scans", response_model=ScanResponse, status_code=201)
async def create_scan(
    body: ScanRequest,
    request: Request,
    db: Client = Depends(get_db),
) -> Any:
    check_rate_limit(request)
    validate_github_url(body.repo_url)

    repo_name = _extract_repo_name(body.repo_url)

    result = db.table("scans").insert({
        "repo_url": body.repo_url,
        "repo_name": repo_name,
        "status": "queued",
    }).execute()

    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to create scan")

    scan = result.data[0]
    scan_id = scan["id"]

    run_async_in_thread(_run_graph, scan_id, body.repo_url, repo_name)
    logger.info("[scans] Queued background pipeline thread for scan %s", scan_id)

    return ScanResponse(
        scan_id=scan_id,
        status=scan["status"],
        repo_url=scan["repo_url"],
        repo_name=scan["repo_name"],
    )


@router.get("/scans/{scan_id}")
async def get_scan(scan_id: str, db: Client = Depends(get_db)) -> Any:
    result = db.table("scans").select("*").eq("id", scan_id).single().execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Scan not found")
    return result.data


@router.get("/scans/{scan_id}/findings")
async def get_scan_findings(scan_id: str, db: Client = Depends(get_db)) -> Any:
    result = db.table("findings").select("*").eq("scan_id", scan_id).order("created_at").execute()
    return result.data or []