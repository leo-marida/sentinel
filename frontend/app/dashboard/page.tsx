"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowUpRight, FolderSearch, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { ScanStatusBadge } from "@/components/scan-status-badge";
import { getScan } from "@/lib/api";
import { getScanHistory, type ScanHistoryEntry } from "@/lib/scan-history";
import type { Scan } from "@/lib/types";

interface ScanRow {
  entry: ScanHistoryEntry;
  scan: Scan | null;
  failed: boolean;
}

async function loadRows(entries: ScanHistoryEntry[]): Promise<ScanRow[]> {
  const results = await Promise.allSettled(
    entries.map((entry) => getScan(entry.scanId))
  );
  return entries.map((entry, i) => {
    const result = results[i];
    return {
      entry,
      scan: result.status === "fulfilled" ? result.value : null,
      failed: result.status === "rejected",
    };
  });
}

export default function DashboardPage() {
  const [rows, setRows] = useState<ScanRow[] | null>(null);
  const [isRefreshing, setIsRefreshing] = useState(false);

  useEffect(() => {
    loadRows(getScanHistory()).then(setRows);
  }, []);

  async function handleRefresh() {
    const entries = getScanHistory();
    setIsRefreshing(true);
    try {
      setRows(await loadRows(entries));
    } finally {
      setIsRefreshing(false);
    }
  }

  return (
    <div className="mx-auto max-w-3xl px-4 py-12">
      <div className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Scans</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Scan history is stored locally in this browser.
          </p>
        </div>
        <Button
          variant="outline"
          size="sm"
          className="gap-2"
          onClick={handleRefresh}
          disabled={isRefreshing || rows === null}
        >
          <RefreshCw className={isRefreshing ? "size-3.5 animate-spin" : "size-3.5"} />
          Refresh
        </Button>
      </div>

      {rows === null && (
        <div className="flex flex-col gap-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-20 w-full rounded-xl" />
          ))}
        </div>
      )}

      {rows !== null && rows.length === 0 && (
        <Card className="flex flex-col items-center gap-3 px-6 py-16 text-center">
          <FolderSearch className="size-8 text-muted-foreground" />
          <p className="text-sm text-muted-foreground">
            No scans yet. Start one from the home page.
          </p>
          <Button asChild size="sm" className="mt-2">
            <Link href="/">New scan</Link>
          </Button>
        </Card>
      )}

      <div className="flex flex-col gap-3">
        {rows?.map(({ entry, scan, failed }) => (
          <Link key={entry.scanId} href={`/dashboard/${entry.scanId}`}>
            <Card className="flex-row items-center justify-between gap-4 px-5 py-4 transition-colors hover:border-primary/40">
              <div className="flex flex-col gap-1.5">
                <span className="font-mono text-sm font-medium">
                  {entry.repoName}
                </span>
                <span className="text-xs text-muted-foreground">
                  {new Date(entry.createdAt).toLocaleString()}
                </span>
              </div>
              <div className="flex items-center gap-3">
                {failed ? (
                  <span className="text-xs text-muted-foreground">
                    Unable to load
                  </span>
                ) : (
                  <ScanStatusBadge status={scan?.status} />
                )}
                <ArrowUpRight className="size-4 text-muted-foreground" />
              </div>
            </Card>
          </Link>
        ))}
      </div>
    </div>
  );
}
