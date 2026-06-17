import {
  Bell,
  BrainCircuit,
  Check,
  FileText,
  Loader2,
  Radar,
  Tags,
  Ticket,
  UserCheck,
  X,
} from "lucide-react";
import { cn } from "@/lib/utils";
import type { ScanStatus } from "@/lib/types";

type NodeState = "pending" | "active" | "done" | "failed";

const NODES = [
  { key: "scanner", label: "Scanner", icon: Radar },
  { key: "classifier", label: "Classifier", icon: Tags },
  { key: "analyzer", label: "Analyzer", icon: BrainCircuit },
  { key: "human_review", label: "Human Review", icon: UserCheck },
  { key: "ticket_creator", label: "Tickets", icon: Ticket },
  { key: "notifier", label: "Notify", icon: Bell },
  { key: "reporter", label: "Report", icon: FileText },
] as const;

/**
 * The backend only reports coarse statuses (queued, awaiting_approval,
 * creating_tickets, complete, failed) — scanner/classifier/analyzer all run
 * silently inside "queued" with no per-node signal, so they're grouped as a
 * single active cluster rather than faking step-by-step granularity.
 */
function computeNodeStates(
  status: ScanStatus | undefined
): Record<string, NodeState> {
  const states: Record<string, NodeState> = {};
  for (const node of NODES) states[node.key] = "pending";

  if (!status || status === "queued" || status === "scanning") {
    states.scanner = "active";
    states.classifier = "active";
    states.analyzer = "active";
    return states;
  }

  if (status === "classifying") {
    states.scanner = "done";
    states.classifier = "active";
    return states;
  }

  if (status === "analyzing") {
    states.scanner = "done";
    states.classifier = "done";
    states.analyzer = "active";
    return states;
  }

  if (status === "awaiting_approval") {
    states.scanner = "done";
    states.classifier = "done";
    states.analyzer = "done";
    states.human_review = "active";
    return states;
  }

  if (status === "creating_tickets") {
    states.scanner = "done";
    states.classifier = "done";
    states.analyzer = "done";
    states.human_review = "done";
    states.ticket_creator = "active";
    states.notifier = "active";
    return states;
  }

  if (status === "complete") {
    for (const node of NODES) states[node.key] = "done";
    return states;
  }

  if (status === "failed") {
    states.scanner = "done";
    states.classifier = "done";
    states.analyzer = "done";
    return states;
  }

  return states;
}

const STATE_STYLES: Record<NodeState, string> = {
  pending: "border-border/60 text-muted-foreground bg-muted/30",
  active: "border-primary/50 text-primary bg-primary/10 ring-2 ring-primary/20",
  done: "border-success/40 text-success bg-success/10",
  failed: "border-destructive/50 text-destructive bg-destructive/10",
};

const CONNECTOR_STYLES: Record<NodeState, string> = {
  pending: "bg-border/60",
  active: "bg-primary/40",
  done: "bg-success/40",
  failed: "bg-destructive/40",
};

export function GraphStatus({
  status,
  failed,
}: {
  status: ScanStatus | undefined;
  failed?: boolean;
}) {
  const states = computeNodeStates(status);

  return (
    <div className="flex items-center gap-0 overflow-x-auto rounded-lg border border-border/60 bg-card/50 p-4">
      {NODES.map((node, i) => {
        const state = states[node.key];
        const Icon = node.icon;
        const isLast = i === NODES.length - 1;
        return (
          <div key={node.key} className="flex items-center">
            <div className="flex flex-col items-center gap-1.5">
              <div
                className={cn(
                  "flex size-10 shrink-0 items-center justify-center rounded-full border transition-colors",
                  STATE_STYLES[state]
                )}
              >
                {state === "active" ? (
                  <Loader2 className="size-4 animate-spin" />
                ) : state === "done" ? (
                  <Check className="size-4" />
                ) : (
                  <Icon className="size-4" />
                )}
              </div>
              <span
                className={cn(
                  "whitespace-nowrap text-[11px] font-medium",
                  state === "active"
                    ? "text-primary"
                    : state === "done"
                      ? "text-success"
                      : "text-muted-foreground"
                )}
              >
                {node.label}
              </span>
            </div>
            {!isLast && (
              <div
                className={cn(
                  "mx-1.5 mb-5 h-0.5 w-8 shrink-0 rounded-full sm:w-12",
                  CONNECTOR_STYLES[state === "done" ? "done" : "pending"]
                )}
              />
            )}
          </div>
        );
      })}
      {failed && (
        <div className="ml-3 flex items-center gap-1.5 rounded-full border border-destructive/50 bg-destructive/10 px-2.5 py-1 text-xs font-medium text-destructive">
          <X className="size-3.5" />
          Pipeline failed
        </div>
      )}
    </div>
  );
}
