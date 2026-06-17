"use client";

import { useEffect, useRef, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import {
  AlertCircle,
  ArrowLeft,
  ExternalLink,
  WifiOff,
} from "lucide-react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import { GraphStatus } from "@/components/graph-status";
import { StreamViewer } from "@/components/stream-viewer";
import { FindingCard } from "@/components/finding-card";
import { ApprovalPanel } from "@/components/approval-panel";
import { ScanStatusBadge } from "@/components/scan-status-badge";
import { useScanStream } from "@/hooks/use-scan-stream";
import { ApiError, getScan, getScanFindings } from "@/lib/api";
import type { Finding, Scan } from "@/lib/types";

type LoadState = "loading" | "ready" | "not_found" | "error";

export default function ScanDetailPage() {
  const { scanId } = useParams<{ scanId: string }>();

  const [initialScan, setInitialScan] = useState<Scan | null>(null);
  const [initialFindings, setInitialFindings] = useState<Finding[]>([]);
  const [loadState, setLoadState] = useState<LoadState>("loading");

  useEffect(() => {
    let cancelled = false;
    Promise.all([getScan(scanId), getScanFindings(scanId)])
      .then(([scan, findings]) => {
        if (cancelled) return;
        setInitialScan(scan);
        setInitialFindings(findings);
        setLoadState("ready");
      })
      .catch((err) => {
        if (cancelled) return;
        setLoadState(err instanceof ApiError && err.status === 404 ? "not_found" : "error");
      });
    return () => {
      cancelled = true;
    };
  }, [scanId]);

  const isFinal = initialScan?.status === "complete" || initialScan?.status === "failed";

  const stream = useScanStream(
    loadState === "ready" && !isFinal ? scanId : null,
    initialScan?.status
  );

  const { hydrateFromServer } = stream;
  const hydrated = useRef(false);
  useEffect(() => {
    if (loadState === "ready" && !isFinal && !hydrated.current) {
      hydrated.current = true;
      hydrateFromServer(initialFindings, initialScan?.status);
    }
  }, [loadState, isFinal, initialFindings, initialScan?.status, hydrateFromServer]);

  // The SSE stream never re-emits findings whose fields changed in place
  // (e.g. ticket_id / approval_status after a decision is submitted), so once
  // the pipeline reports "done" we refetch once to get authoritative final state.
  const [finalScan, setFinalScan] = useState<Scan | null>(null);
  const [finalFindings, setFinalFindings] = useState<Finding[] | null>(null);
  useEffect(() => {
    if (!isFinal && stream.isComplete && scanId) {
      Promise.all([getScan(scanId), getScanFindings(scanId)])
        .then(([scan, findings]) => {
          setFinalScan(scan);
          setFinalFindings(findings);
        })
        .catch(() => {});
    }
  }, [stream.isComplete, isFinal, scanId]);

  if (loadState === "loading") {
    return (
      <div className="mx-auto max-w-3xl px-4 py-12">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="mt-4 h-20 w-full rounded-xl" />
        <Skeleton className="mt-4 h-56 w-full rounded-xl" />
      </div>
    );
  }

  if (loadState === "not_found") {
    return (
      <div className="mx-auto max-w-3xl px-4 py-12">
        <Card className="flex flex-col items-center gap-3 px-6 py-16 text-center">
          <AlertCircle className="size-8 text-muted-foreground" />
          <p className="text-sm text-muted-foreground">
            We couldn&apos;t find a scan with that id.
          </p>
          <Button asChild size="sm" className="mt-2">
            <Link href="/dashboard">Back to scans</Link>
          </Button>
        </Card>
      </div>
    );
  }

  if (loadState === "error") {
    return (
      <div className="mx-auto max-w-3xl px-4 py-12">
        <Alert variant="destructive">
          <AlertCircle />
          <AlertTitle>Failed to load scan</AlertTitle>
          <AlertDescription>
            The backend may still be waking up. Try refreshing in a moment.
          </AlertDescription>
        </Alert>
      </div>
    );
  }

  const scan = isFinal ? initialScan : finalScan ?? initialScan;
  const status = isFinal ? initialScan?.status : finalScan?.status ?? stream.status;
  const findings = isFinal ? initialFindings : finalFindings ?? stream.findings;
  const summary = isFinal
    ? initialScan?.summary ?? null
    : finalScan?.summary ?? stream.summary ?? null;
  const isAwaitingApproval = !isFinal && status === "awaiting_approval";

  return (
    <div className="mx-auto max-w-3xl px-4 py-12 pb-32">
      <Link
        href="/dashboard"
        className="mb-6 inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="size-3.5" />
        Back to scans
      </Link>

      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex flex-col gap-1.5">
          <h1 className="font-mono text-xl font-semibold tracking-tight">
            {scan?.repo_name}
          </h1>
          {scan?.repo_url && (
            <a
              href={scan.repo_url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-primary"
            >
              {scan.repo_url}
              <ExternalLink className="size-3" />
            </a>
          )}
        </div>
        <ScanStatusBadge status={status} />
      </div>

      <Separator className="my-6" />

      <GraphStatus status={status} failed={status === "failed"} />

      {scan?.error_message && status === "failed" && (
        <Alert variant="destructive" className="mt-4">
          <AlertCircle />
          <AlertTitle>Pipeline failed</AlertTitle>
          <AlertDescription>{scan.error_message}</AlertDescription>
        </Alert>
      )}

      {stream.connection === "connection_lost" && (
        <Alert variant="destructive" className="mt-4">
          <WifiOff />
          <AlertTitle>Connection lost</AlertTitle>
          <AlertDescription>
            Lost the live connection to the scan after several retries.{" "}
            <button
              type="button"
              onClick={stream.reconnect}
              className="underline underline-offset-2"
            >
              Try reconnecting
            </button>
            .
          </AlertDescription>
        </Alert>
      )}

      {!isFinal && (
        <div className="mt-6">
          <StreamViewer log={stream.log} />
        </div>
      )}

      {summary && (
        <div className="mt-6 flex flex-wrap gap-2 text-xs">
          <SummaryChip label="Total" count={summary.total_findings} />
          <SummaryChip label="Critical" count={summary.critical} className="text-critical" />
          <SummaryChip label="High" count={summary.high} className="text-high" />
          <SummaryChip label="Medium" count={summary.medium} className="text-medium" />
          <SummaryChip label="Low" count={summary.low} className="text-low" />
        </div>
      )}

      <div className="mt-8 flex flex-col gap-4">
        {findings.length === 0 && !isFinal && !isAwaitingApproval && (
          <p className="text-center text-sm text-muted-foreground">
            No findings reported yet — agents are still working.
          </p>
        )}
        {findings.length === 0 && isAwaitingApproval && (
          <p className="text-center text-sm text-muted-foreground">
            No findings were reported for this scan.
          </p>
        )}
        {findings.map((finding) => (
          <FindingCard
            key={finding.id}
            finding={finding}
            editable={isAwaitingApproval}
            onDecisionChange={stream.updateFindingApproval}
          />
        ))}
      </div>

      {isAwaitingApproval && (
        <ApprovalPanel scanId={scanId} findings={findings} onSubmitted={() => {}} />
      )}
    </div>
  );
}

function SummaryChip({
  label,
  count,
  className,
}: {
  label: string;
  count: number;
  className?: string;
}) {
  return (
    <span className="inline-flex items-center gap-1.5 rounded-full border border-border/60 bg-card/50 px-3 py-1">
      <span className={className}>{count}</span>
      <span className="text-muted-foreground">{label}</span>
    </span>
  );
}
