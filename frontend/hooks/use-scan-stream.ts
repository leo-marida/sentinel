"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { openScanStream } from "@/lib/sse";
import type { Finding, ScanEvent, ScanStatus, ScanSummary } from "@/lib/types";

export type StreamConnectionState =
  | "idle"
  | "connecting"
  | "open"
  | "connection_lost";

export interface StreamLogEntry {
  id: string;
  message: string;
  level: "info" | "success" | "warning" | "error";
}

const MAX_RECONNECT_ATTEMPTS = 5;

export function useScanStream(
  scanId: string | null,
  initialStatus?: ScanStatus
) {
  const [connection, setConnection] = useState<StreamConnectionState>("idle");
  const [status, setStatus] = useState<ScanStatus | undefined>(initialStatus);
  const [findings, setFindings] = useState<Finding[]>([]);
  const [summary, setSummary] = useState<ScanSummary | null>(null);
  const [streamError, setStreamError] = useState<string | null>(null);
  const [log, setLog] = useState<StreamLogEntry[]>([]);
  const [generation, setGeneration] = useState(0);

  const reconnectAttempts = useRef(0);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const pushLog = useCallback(
    (message: string, level: StreamLogEntry["level"] = "info") => {
      setLog((prev) =>
        [...prev, { id: crypto.randomUUID(), message, level }].slice(-200)
      );
    },
    []
  );

  const isComplete = status === "complete" || status === "failed";
  const isFailed = status === "failed";

  const reconnect = useCallback(() => {
    reconnectAttempts.current = 0;
    setConnection("connecting");
    setGeneration((g) => g + 1);
  }, []);

  useEffect(() => {
    if (!scanId || isComplete) return;

    // Reflects the start of a new connection attempt; subsequent transitions
    // (open/connection_lost) happen inside the EventSource callbacks below.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setConnection("connecting");
    const es = openScanStream(
      scanId,
      (event: ScanEvent) => {
        reconnectAttempts.current = 0;
        setConnection("open");

        switch (event.type) {
          case "connected":
            pushLog("Connected to live scan stream.", "info");
            break;
          case "status":
            setStatus(event.status);
            pushLog(`Status: ${event.status.replace(/_/g, " ")}`, "info");
            break;
          case "finding":
            setFindings((prev) => {
              if (prev.some((f) => f.id === event.finding.id)) return prev;
              return [...prev, event.finding];
            });
            pushLog(
              `Finding discovered: ${event.finding.title} [${event.finding.severity}]`,
              "warning"
            );
            break;
          case "done":
            setSummary(event.summary ?? null);
            pushLog("Pipeline finished.", "success");
            es.close();
            break;
          case "error":
            setStreamError(event.message);
            pushLog(event.message || "Stream error.", "error");
            break;
          case "timeout":
            pushLog("Stream idle timeout reached — reconnecting…", "warning");
            es.close();
            setGeneration((g) => g + 1);
            break;
        }
      },
      () => {
        if (reconnectAttempts.current >= MAX_RECONNECT_ATTEMPTS) {
          setConnection("connection_lost");
          pushLog("Connection lost — give up after repeated retries.", "error");
          es.close();
          return;
        }
        reconnectAttempts.current += 1;
        const delay = Math.min(1000 * 2 ** reconnectAttempts.current, 15000);
        pushLog(
          `Connection issue — retrying in ${Math.round(delay / 1000)}s…`,
          "warning"
        );
        es.close();
        reconnectTimer.current = setTimeout(
          () => setGeneration((g) => g + 1),
          delay
        );
      }
    );

    return () => {
      es.close();
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
    };
  }, [scanId, generation, isComplete, pushLog]);

  const updateFindingApproval = useCallback(
    (findingId: string, decision: "approved" | "rejected") => {
      setFindings((prev) =>
        prev.map((f) =>
          f.id === findingId ? { ...f, approval_status: decision } : f
        )
      );
    },
    []
  );

  const hydrateFromServer = useCallback(
    (serverFindings: Finding[], serverStatus?: ScanStatus) => {
      setFindings(serverFindings);
      if (serverStatus) setStatus(serverStatus);
    },
    []
  );

  return {
    connection,
    status,
    findings,
    summary,
    streamError,
    isComplete,
    isFailed,
    log,
    updateFindingApproval,
    hydrateFromServer,
    reconnect,
  };
}
