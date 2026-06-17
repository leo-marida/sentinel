"use client";

import { useCallback, useState } from "react";
import { ApiError, submitApproval } from "@/lib/api";
import type { ApprovalDecision, ApprovalResponse } from "@/lib/types";

export function useApproval(scanId: string) {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<ApprovalResponse | null>(null);

  const submit = useCallback(
    async (
      decisions: ApprovalDecision[]
    ): Promise<
      { ok: true; data: ApprovalResponse } | { ok: false; message: string }
    > => {
      setIsSubmitting(true);
      setError(null);
      try {
        const res = await submitApproval(scanId, decisions);
        setResult(res);
        return { ok: true, data: res };
      } catch (err) {
        const message =
          err instanceof ApiError
            ? err.message
            : "Failed to submit approval decisions. Please try again.";
        setError(message);
        return { ok: false, message };
      } finally {
        setIsSubmitting(false);
      }
    },
    [scanId]
  );

  return { submit, isSubmitting, error, result };
}
