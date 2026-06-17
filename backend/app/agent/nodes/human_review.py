"""
HITL node. The graph is compiled with interrupt_before=["human_review"],
so execution pauses BEFORE this node. When the frontend submits approvals,
the graph is resumed and this node filters approved findings.
"""
import logging

from app.agent.state import SentinelState

logger = logging.getLogger(__name__)


async def run(state: SentinelState) -> dict:
    approved = [
        f for f in state.get("findings", [])
        if f["approval_status"] == "approved"
    ]
    logger.info("[human_review] %d findings approved", len(approved))
    return {
        "approved_findings": approved,
        "current_node": "human_review",
    }