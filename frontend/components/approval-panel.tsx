"use client";

import { AlertTriangle, CheckCircle2, Loader2, XCircle } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { useApproval } from "@/hooks/use-approval";
import type { Finding } from "@/lib/types";

export function ApprovalPanel({
  scanId,
  findings,
  onSubmitted,
}: {
  scanId: string;
  findings: Finding[];
  onSubmitted: () => void;
}) {
  const { submit, isSubmitting } = useApproval(scanId);

  const approvedCount = findings.filter((f) => f.approval_status === "approved").length;
  const rejectedCount = findings.filter((f) => f.approval_status === "rejected").length;
  const pendingCount = findings.filter((f) => f.approval_status === "pending").length;
  const isEmpty = findings.length === 0;

  async function handleSubmit() {
    const decisions = findings
      .filter((f) => f.approval_status !== "pending")
      .map((f) => ({
        finding_id: f.id,
        decision: f.approval_status as "approved" | "rejected",
      }));

    const result = await submit(decisions);
    if (result.ok) {
      toast.success(
        `Submitted: ${result.data.approved} approved, ${result.data.rejected} rejected.`
      );
      onSubmitted();
    } else {
      toast.error(result.message);
    }
  }

  return (
    <div className="sticky bottom-4 z-40 mx-auto flex w-full max-w-3xl flex-col gap-3 rounded-xl border border-border/60 bg-card/95 p-4 shadow-lg backdrop-blur sm:flex-row sm:items-center sm:justify-between">
      <div className="flex flex-wrap items-center gap-4 text-sm">
        {isEmpty ? (
          <span className="text-muted-foreground">
            No findings to review — confirm to let the pipeline finish.
          </span>
        ) : (
          <>
            <span className="flex items-center gap-1.5 text-success">
              <CheckCircle2 className="size-4" /> {approvedCount} approved
            </span>
            <span className="flex items-center gap-1.5 text-muted-foreground">
              <XCircle className="size-4" /> {rejectedCount} rejected
            </span>
            {pendingCount > 0 && (
              <span className="flex items-center gap-1.5 text-medium">
                <AlertTriangle className="size-4" /> {pendingCount} need a decision
              </span>
            )}
          </>
        )}
      </div>
      <Button
        size="lg"
        className="gap-2"
        disabled={pendingCount > 0 || isSubmitting}
        onClick={handleSubmit}
      >
        {isSubmitting && <Loader2 className="size-4 animate-spin" />}
        {isSubmitting ? "Submitting…" : isEmpty ? "Continue" : "Submit decisions"}
      </Button>
    </div>
  );
}
