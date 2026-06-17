export type Severity = "critical" | "high" | "medium" | "low" | "info";

export type ApprovalStatus = "pending" | "approved" | "rejected";

export type ScanStatus =
  | "queued"
  | "scanning"
  | "classifying"
  | "analyzing"
  | "awaiting_approval"
  | "creating_tickets"
  | "complete"
  | "failed";

export interface Finding {
  id: string;
  scan_id: string;
  file_path: string;
  line_start: number;
  line_end: number;
  rule_id: string;
  severity: Severity;
  title: string;
  description: string;
  raw_output?: Record<string, unknown> | null;
  ai_analysis?: string | null;
  remediation?: string | null;
  approval_status: ApprovalStatus;
  approved_at?: string | null;
  ticket_id?: string | null;
  created_at?: string;
}

export interface ScanSummary {
  total_findings: number;
  critical: number;
  high: number;
  medium: number;
  low: number;
  info?: number;
}

export interface Scan {
  id: string;
  repo_url: string;
  repo_name: string;
  status: ScanStatus;
  created_at: string;
  updated_at: string;
  completed_at: string | null;
  summary: ScanSummary | null;
  error_message: string | null;
}

export type ScanEvent =
  | { type: "connected"; scan_id: string }
  | { type: "status"; status: ScanStatus }
  | { type: "finding"; finding: Finding }
  | { type: "done"; summary: ScanSummary | null }
  | { type: "error"; message: string }
  | { type: "timeout" };

export interface ApprovalDecision {
  finding_id: string;
  decision: "approved" | "rejected";
}

export interface ApprovalResponse {
  status: string;
  scan_id: string;
  approved: number;
  rejected: number;
}

export interface CreateScanResponse {
  scan_id: string;
  status: ScanStatus;
  repo_url: string;
  repo_name: string;
}
