"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowUpRight, History } from "lucide-react";
import { getScanHistory, type ScanHistoryEntry } from "@/lib/scan-history";

export function RecentScansStrip() {
  const [entries, setEntries] = useState<ScanHistoryEntry[]>([]);

  useEffect(() => {
    // Read localStorage only after mount to avoid a server/client hydration mismatch.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setEntries(getScanHistory().slice(0, 5));
  }, []);

  if (entries.length === 0) return null;

  return (
    <div className="mt-10 w-full max-w-xl">
      <div className="mb-2 flex items-center gap-1.5 text-xs font-medium text-muted-foreground">
        <History className="size-3.5" />
        Recent scans
      </div>
      <div className="flex flex-col gap-1.5">
        {entries.map((entry) => (
          <Link
            key={entry.scanId}
            href={`/dashboard/${entry.scanId}`}
            className="group flex items-center justify-between rounded-lg border border-border/60 bg-card/40 px-3 py-2 text-sm transition-colors hover:border-primary/40 hover:bg-card/70"
          >
            <span className="truncate font-mono text-xs text-foreground/90">
              {entry.repoName}
            </span>
            <ArrowUpRight className="size-3.5 shrink-0 text-muted-foreground transition-colors group-hover:text-primary" />
          </Link>
        ))}
      </div>
      <Link
        href="/dashboard"
        className="mt-2 inline-block text-xs text-primary hover:underline"
      >
        View all scans →
      </Link>
    </div>
  );
}
