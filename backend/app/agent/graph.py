"""
LangGraph state machine for Sentinel.
Compiled with interrupt_before=["human_review"] for HITL approval.
"""
import logging

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from app.agent.nodes import (
    analyzer,
    classifier,
    human_review,
    notifier,
    reporter,
    scanner,
    ticket_creator,
)
from app.agent.state import SentinelState

logger = logging.getLogger(__name__)


def _should_deep_analyze(state: SentinelState) -> str:
    """Skip deep analysis if there are no critical/high findings."""
    critical_high = [
        f for f in state.get("findings", [])
        if f["severity"] in ("critical", "high")
    ]
    return "analyzer" if critical_high else "human_review"


def _should_create_tickets(state: SentinelState) -> str:
    """Only create tickets if any findings were approved."""
    approved = [f for f in state.get("findings", []) if f["approval_status"] == "approved"]
    return "ticket_creator" if approved else "reporter"


def build_sentinel_graph(checkpointer=None):
    graph = StateGraph(SentinelState)

    graph.add_node("scanner", scanner.run)
    graph.add_node("classifier", classifier.run)
    graph.add_node("analyzer", analyzer.run)
    graph.add_node("human_review", human_review.run)
    graph.add_node("ticket_creator", ticket_creator.run)
    graph.add_node("notifier", notifier.run)
    graph.add_node("reporter", reporter.run)

    graph.set_entry_point("scanner")
    graph.add_edge("scanner", "classifier")
    graph.add_conditional_edges("classifier", _should_deep_analyze)
    graph.add_edge("analyzer", "human_review")
    graph.add_conditional_edges("human_review", _should_create_tickets)
    graph.add_edge("ticket_creator", "notifier")
    graph.add_edge("notifier", "reporter")
    graph.add_edge("reporter", END)

    return graph.compile(
        checkpointer=checkpointer or MemorySaver(),
        interrupt_before=["human_review"],
    )


sentinel_graph = build_sentinel_graph()