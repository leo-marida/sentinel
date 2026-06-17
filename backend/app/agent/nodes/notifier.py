"""
Notifier node: sends a Slack webhook notification with scan summary.
Skips silently if SLACK_WEBHOOK_URL is not configured.
"""
import logging

import httpx

from app.agent.state import SentinelState
from app.config import settings

logger = logging.getLogger(__name__)


async def run(state: SentinelState) -> dict:
    if not settings.SLACK_WEBHOOK_URL:
        logger.info("[notifier] No Slack webhook configured — skipping")
        return {"current_node": "notifier"}

    approved = state.get("approved_findings", [])
    message = (
        f":shield: *Sentinel scan complete* for `{state['repo_name']}`\n"
        f"{len(approved)} finding(s) approved and ticketed."
    )

    try:
        async with httpx.AsyncClient() as http:
            await http.post(settings.SLACK_WEBHOOK_URL, json={"text": message}, timeout=10)
        logger.info("[notifier] Slack notification sent")
    except Exception as e:
        logger.warning("[notifier] Slack notification failed: %s", e)

    return {"current_node": "notifier"}