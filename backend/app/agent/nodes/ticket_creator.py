"""
Ticket creator node: writes a ticket reference to each approved finding in Supabase.
"""
import logging

from app.agent.state import SentinelState
from app.db.client import get_supabase

logger = logging.getLogger(__name__)


async def run(state: SentinelState) -> dict:
    approved = state.get("approved_findings", [])
    if not approved:
        logger.info("[ticket_creator] No approved findings — skipping")
        return {"current_node": "ticket_creator"}

    db = get_supabase()
    for finding in approved:
        ticket_id = f"SENTINEL-{finding['id'][:8].upper()}"
        db.table("findings").update({"ticket_id": ticket_id}).eq("id", finding["id"]).execute()
        logger.info("[ticket_creator] Created ticket %s", ticket_id)

    return {"current_node": "ticket_creator"}