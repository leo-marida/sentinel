"""
Approval endpoint: persists human decisions to DB and resumes the paused LangGraph.
Flow: frontend submits approve/reject per finding → DB updated → graph resumed →
      ticket_creator + notifier + reporter nodes run → scan status → complete.
"""
import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.agent.graph import sentinel_graph
from app.db.client import get_supabase
from app.utils.background import run_async_in_thread

logger = logging.getLogger(__name__)
router = APIRouter()


class ApprovalDecision(BaseModel):
    finding_id: str
    decision: str  # "approved" | "rejected"


class ApprovalRequest(BaseModel):
    decisions: list[ApprovalDecision]


async def _resume_graph(scan_id: str, updated_findings: list) -> None:
    """Resume the paused graph after HITL decisions are submitted."""
    config = {"configurable": {"thread_id": scan_id}}
    try:
        # Update the graph state with approval decisions, marking human_review as done.
        # as_node="human_review" makes LangGraph skip re-running that node on resume, so
        # approved_findings must be computed here too — human_review.run()'s own filtering
        # logic never executes once we mark it complete this way.
        approved_findings = [f for f in updated_findings if f["approval_status"] == "approved"]
        # Two separate calls, not one: human_review's conditional edge (_should_create_tickets)
        # is attached as a writer on human_review itself, and its reader re-reads channel state
        # from the checkpoint as it was BEFORE this update is persisted — so if the data write
        # and the as_node="human_review" trigger happen in the same call, the branch sees stale
        # (pre-approval) findings and always routes to "reporter", skipping ticket_creator.
        # Writing via "analyzer" first (no branch attached there) persists the real data; the
        # second call's branch read then sees the committed, correct state.
        await sentinel_graph.aupdate_state(
            config,
            {"findings": updated_findings, "approved_findings": approved_findings},
            as_node="analyzer",
        )
        await sentinel_graph.aupdate_state(
            config, {"current_node": "human_review"}, as_node="human_review"
        )
        # Resume execution — runs ticket_creator → notifier → reporter
        await sentinel_graph.ainvoke(None, config=config)
        logger.info("[approvals] Graph resumed and completed for scan %s", scan_id)
    except Exception as e:
        logger.error("[approvals] Graph resume failed for scan %s: %s", scan_id, e)
        db = get_supabase()
        db.table("scans").update({
            "status": "failed",
            "error_message": f"Graph resume failed: {e}",
        }).eq("id", scan_id).execute()


@router.post("/scans/{scan_id}/approve")
async def submit_approval(scan_id: str, body: ApprovalRequest) -> Any:
    db = get_supabase()

    # Verify scan exists and is waiting for approval
    scan_result = db.table("scans").select("status").eq("id", scan_id).single().execute()
    if not scan_result.data:
        raise HTTPException(status_code=404, detail="Scan not found")
    if scan_result.data["status"] != "awaiting_approval":
        raise HTTPException(
            status_code=409,
            detail=f"Scan is not awaiting approval (status: {scan_result.data['status']})",
        )

    # Persist approval decisions to DB
    decision_map = {d.finding_id: d.decision for d in body.decisions}
    for finding_id, decision in decision_map.items():
        db.table("findings").update(
            {"approval_status": decision}
        ).eq("id", finding_id).eq("scan_id", scan_id).execute()

    # Fetch current graph state to get the full findings list
    config = {"configurable": {"thread_id": scan_id}}
    try:
        current_state = await sentinel_graph.aget_state(config)
        findings = current_state.values.get("findings", []) if current_state else []
    except Exception as e:
        logger.warning("[approvals] Could not fetch graph state: %s — loading from DB", e)
        findings = []

    # If graph state is gone (server restart), rebuild findings from DB
    if not findings:
        findings_result = db.table("findings").select("*").eq("scan_id", scan_id).execute()
        db_findings = findings_result.data or []
        findings = [
            {
                "id": f["id"],
                "file_path": f["file_path"],
                "line_start": f.get("line_start", 0),
                "line_end": f.get("line_end", 0),
                "rule_id": f["rule_id"],
                "severity": f["severity"],
                "title": f["title"],
                "description": f["description"],
                "raw_output": f.get("raw_output", {}),
                "ai_analysis": f.get("ai_analysis"),
                "remediation": f.get("remediation"),
                "approval_status": f["approval_status"],
            }
            for f in db_findings
        ]

    # Apply decisions to findings in state
    updated_findings = [
        {**f, "approval_status": decision_map.get(f["id"], f["approval_status"])}
        for f in findings
    ]

    # Update scan status to signal processing
    db.table("scans").update({"status": "creating_tickets"}).eq("id", scan_id).execute()

    # Resume graph in an isolated thread + event loop so endpoint returns
    # immediately and the synchronous Supabase calls inside don't block
    # FastAPI's main loop (see app/utils/background.py).
    run_async_in_thread(_resume_graph, scan_id, updated_findings)

    approved_count = sum(1 for d in body.decisions if d.decision == "approved")
    return {
        "status": "resumed",
        "scan_id": scan_id,
        "approved": approved_count,
        "rejected": len(body.decisions) - approved_count,
    }