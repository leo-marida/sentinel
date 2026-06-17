"""
Reporter node: generates a markdown summary report from all findings.
Streams tokens via state["stream_tokens"] for SSE (Phase 5).
"""
import logging
from datetime import datetime, timezone

from app.agent.state import SentinelState
from app.db.client import get_supabase

logger = logging.getLogger(__name__)


_SEVERITY_EMOJI = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🔵", "info": "⚪"}


def _severity_emoji(severity: str) -> str:
    return _SEVERITY_EMOJI.get(severity, "⚪")


async def run(state: SentinelState) -> dict:
    findings = state.get("findings", [])
    approved = state.get("approved_findings", [])
    scan_id = state["scan_id"]

    severity_order = ["critical", "high", "medium", "low", "info"]
    counts: dict[str, int] = {s: 0 for s in severity_order}
    for f in findings:
        if f["severity"] in counts:
            counts[f["severity"]] += 1

    lines: list[str] = [
        "# Sentinel Security Report",
        f"**Repository:** `{state['repo_name']}`",
        f"**Scan ID:** `{scan_id}`",
        f"**Generated:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        "",
        "## Executive Summary",
        f"Sentinel identified **{len(findings)} finding(s)** across the repository.",
        "",
        "| Severity | Count |",
        "|---|---|",
    ]
    for sev in severity_order:
        if counts[sev]:
            lines.append(f"| {_severity_emoji(sev)} {sev.capitalize()} | {counts[sev]} |")

    if findings:
        lines += ["", "## Findings"]
        for f in sorted(findings, key=lambda x: severity_order.index(x["severity"])):
            lines += [
                f"### {_severity_emoji(f['severity'])} {f['title']}",
                f"**Severity:** {f['severity'].capitalize()}  ",
                f"**File:** `{f['file_path']}` (line {f['line_start']})  ",
                f"**Rule:** `{f['rule_id']}`",
                "",
                f"{f['description']}",
            ]
            if f.get("ai_analysis"):
                lines += ["", "**AI Analysis:**", f["ai_analysis"]]
            lines.append("")

    if approved:
        lines += [
            "## Approved & Ticketed",
            f"{len(approved)} finding(s) were approved and tickets created.",
            "",
        ]

    lines += [
        "## Key Takeaways",
        "Review and remediate findings starting with the highest severity.",
    ]

    report = "\n".join(lines)

    db = get_supabase()
    db.table("scans").update({
        "status": "complete",
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "total_findings": len(findings),
            **counts,
        },
    }).eq("id", scan_id).execute()

    logger.info("[reporter] Report generated for scan %s", scan_id)
    return {"report": report, "current_node": "reporter"}