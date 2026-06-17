import { CheckCircle2, Loader2, ShieldAlert, UserCheck, XCircle } from "lucide-react";
import { cn } from "@/lib/utils";
import type { ScanStatus } from "@/lib/types";

const STATUS_CONFIG: Record<
  ScanStatus,
  { label: string; className: string; icon: typeof Loader2; spin?: boolean }
> = {
  queued: {
    label: "Queued",
    className: "bg-muted/40 text-muted-foreground border-border/60",
    icon: Loader2,
    spin: true,
  },
  scanning: {
    label: "Scanning",
    className: "bg-primary/10 text-primary border-primary/30",
    icon: Loader2,
    spin: true,
  },
  classifying: {
    label: "Classifying",
    className: "bg-primary/10 text-primary border-primary/30",
    icon: Loader2,
    spin: true,
  },
  analyzing: {
    label: "Analyzing",
    className: "bg-primary/10 text-primary border-primary/30",
    icon: Loader2,
    spin: true,
  },
  awaiting_approval: {
    label: "Awaiting approval",
    className: "bg-medium/15 text-medium border-medium/30",
    icon: UserCheck,
  },
  creating_tickets: {
    label: "Creating tickets",
    className: "bg-primary/10 text-primary border-primary/30",
    icon: Loader2,
    spin: true,
  },
  complete: {
    label: "Complete",
    className: "bg-success/15 text-success border-success/30",
    icon: CheckCircle2,
  },
  failed: {
    label: "Failed",
    className: "bg-destructive/15 text-destructive border-destructive/30",
    icon: XCircle,
  },
};

export function ScanStatusBadge({
  status,
  className,
}: {
  status: ScanStatus | undefined;
  className?: string;
}) {
  const config = status ? STATUS_CONFIG[status] : undefined;
  const Icon = config?.icon ?? ShieldAlert;

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-medium",
        config?.className ?? "bg-muted/40 text-muted-foreground border-border/60",
        className
      )}
    >
      <Icon className={cn("size-3", config?.spin && "animate-spin")} />
      {config?.label ?? "Unknown"}
    </span>
  );
}
