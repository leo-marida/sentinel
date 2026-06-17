from typing import Annotated, List, Optional, TypedDict

from langgraph.graph.message import add_messages


class Finding(TypedDict):
    id: str
    file_path: str
    line_start: int
    line_end: int
    rule_id: str
    severity: str           # critical | high | medium | low | info
    title: str
    description: str
    raw_output: dict
    ai_analysis: Optional[str]
    remediation: Optional[str]
    approval_status: str    # pending | approved | rejected


class SentinelState(TypedDict):
    # Core
    scan_id: str
    repo_url: str
    repo_name: str

    # Pipeline data
    files: List[dict]               # {path, content}
    raw_findings: List[dict]        # Raw scanner output
    findings: List[Finding]         # Enriched findings
    approved_findings: List[Finding]
    report: Optional[str]

    # Control flow
    current_node: str
    error: Optional[str]
    stream_tokens: Annotated[List[str], add_messages]