import { AlertTriangle, Flame, Info, ShieldQuestion, TriangleAlert } from "lucide-react";
import { cn } from "@/lib/utils";
import type { Severity } from "@/lib/types";

const SEVERITY_CONFIG: Record<
  Severity,
  { label: string; icon: typeof Flame; className: string }
> = {
  critical: {
    label: "Critical",
    icon: Flame,
    className: "bg-critical/15 text-critical border-critical/30",
  },
  high: {
    label: "High",
    icon: TriangleAlert,
    className: "bg-high/15 text-high border-high/30",
  },
  medium: {
    label: "Medium",
    icon: AlertTriangle,
    className: "bg-medium/15 text-medium border-medium/30",
  },
  low: {
    label: "Low",
    icon: ShieldQuestion,
    className: "bg-low/15 text-low border-low/30",
  },
  info: {
    label: "Info",
    icon: Info,
    className: "bg-info/15 text-info border-info/30",
  },
};

export function SeverityBadge({
  severity,
  className,
}: {
  severity: Severity;
  className?: string;
}) {
  const config = SEVERITY_CONFIG[severity] ?? SEVERITY_CONFIG.info;
  const Icon = config.icon;
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-xs font-medium",
        config.className,
        className
      )}
    >
      <Icon className="size-3" />
      {config.label}
    </span>
  );
}
