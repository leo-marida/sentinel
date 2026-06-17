"use client";

import { useEffect, useRef } from "react";
import { AlertCircle, CheckCircle2, Info, TriangleAlert } from "lucide-react";
import { ScrollArea } from "@/components/ui/scroll-area";
import { cn } from "@/lib/utils";
import type { StreamLogEntry } from "@/hooks/use-scan-stream";

const LEVEL_ICON: Record<StreamLogEntry["level"], typeof Info> = {
  info: Info,
  success: CheckCircle2,
  warning: TriangleAlert,
  error: AlertCircle,
};

const LEVEL_CLASS: Record<StreamLogEntry["level"], string> = {
  info: "text-muted-foreground",
  success: "text-success",
  warning: "text-medium",
  error: "text-destructive",
};

export function StreamViewer({ log }: { log: StreamLogEntry[] }) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [log.length]);

  return (
    <ScrollArea className="h-56 rounded-lg border border-border/60 bg-card/50">
      <div className="flex flex-col gap-1.5 p-3">
        {log.length === 0 && (
          <p className="px-1 py-2 text-xs text-muted-foreground">
            Waiting for activity…
          </p>
        )}
        {log.map((entry) => {
          const Icon = LEVEL_ICON[entry.level];
          return (
            <div
              key={entry.id}
              className={cn(
                "flex items-start gap-2 rounded-md px-2 py-1.5 font-mono text-xs animate-in fade-in slide-in-from-bottom-1",
                LEVEL_CLASS[entry.level]
              )}
            >
              <Icon className="mt-0.5 size-3.5 shrink-0" />
              <span className="break-all text-foreground/90">{entry.message}</span>
            </div>
          );
        })}
        <div ref={bottomRef} />
      </div>
    </ScrollArea>
  );
}
