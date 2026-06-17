"""
Raw SQL schema lives in SENTINEL.md Section 4.
Run it in the Supabase SQL editor before starting the backend.

This module contains Python dataclasses mirroring the DB tables
for type hints -- the actual DB operations use the supabase-py client.
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional


@dataclass
class Scan:
    id: str
    repo_url: str
    repo_name: str
    status: str
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None
    summary: Optional[dict[str, Any]] = None
    error_message: Optional[str] = None


@dataclass
class Finding:
    id: str
    scan_id: str
    file_path: str
    rule_id: str
    severity: str
    title: str
    description: str
    raw_output: dict[str, Any]
    created_at: datetime
    line_start: Optional[int] = None
    line_end: Optional[int] = None
    ai_analysis: Optional[str] = None
    remediation: Optional[str] = None
    approval_status: str = "pending"
    approved_at: Optional[datetime] = None
    ticket_id: Optional[str] = None