"""
SSE stream endpoint: polls Supabase every second and emits typed events.
Frontend opens EventSource to this endpoint and receives live scan updates.
"""
import asyncio
import json
import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.db.client import get_supabase

logger = logging.getLogger(__name__)
router = APIRouter()


async def _scan_event_generator(scan_id: str):
    db = get_supabase()
    last_status = None
    last_finding_count = 0

    yield f"data: {json.dumps({'type': 'connected', 'scan_id': scan_id})}\n\n"

    for _ in range(300):  # max 5 min
        await asyncio.sleep(1)

        try:
            scan_result = db.table("scans").select("*").eq("id", scan_id).single().execute()
        except Exception as e:
            logger.warning("[stream] Supabase poll failed: %s", e)
            continue

        if not scan_result.data:
            yield f"data: {json.dumps({'type': 'error', 'message': 'Scan not found'})}\n\n"
            return

        scan = scan_result.data

        # Emit status change events
        if scan["status"] != last_status:
            last_status = scan["status"]
            yield f"data: {json.dumps({'type': 'status', 'status': scan['status']})}\n\n"

        # Emit new findings as they arrive
        try:
            findings_result = (
                db.table("findings")
                .select("*")
                .eq("scan_id", scan_id)
                .order("created_at")
                .execute()
            )
            findings = findings_result.data or []
        except Exception:
            findings = []

        if len(findings) > last_finding_count:
            for finding in findings[last_finding_count:]:
                yield f"data: {json.dumps({'type': 'finding', 'finding': finding})}\n\n"
            last_finding_count = len(findings)

        if scan["status"] in ("complete", "failed"):
            done_payload = {
                "type": "done",
                "summary": scan.get("summary"),
                "report": scan.get("report"),
            }
            yield f"data: {json.dumps(done_payload)}\n\n"
            return

    yield f"data: {json.dumps({'type': 'timeout'})}\n\n"


@router.get("/scans/{scan_id}/stream")
async def stream_scan(scan_id: str):
    # Verify scan exists
    db = get_supabase()
    result = db.table("scans").select("id").eq("id", scan_id).single().execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Scan not found")

    return StreamingResponse(
        _scan_event_generator(scan_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )