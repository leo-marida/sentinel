"use client";

import { CheckCircle2, ChevronDown, MapPin, Tag, Ticket, XCircle } from "lucide-react";
import ReactMarkdown from "react-markdown";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { SeverityBadge } from "@/components/severity-badge";
import { cn } from "@/lib/utils";
import type { Finding } from "@/lib/types";

export function FindingCard({
  finding,
  editable,
  onDecisionChange,
}: {
  finding: Finding;
  editable: boolean;
  onDecisionChange?: (findingId: string, decision: "approved" | "rejected") => void;
}) {
  const hasDetails = Boolean(finding.ai_analysis || finding.remediation);

  return (
    <Card className="border-border/60 bg-card/50">
      <CardHeader className="flex-row items-start justify-between gap-4 space-y-0">
        <div className="flex flex-col gap-1.5">
          <div className="flex flex-wrap items-center gap-2">
            <SeverityBadge severity={finding.severity} />
            <Badge variant="outline" className="gap-1 font-mono text-[11px]">
              <Tag className="size-3" />
              {finding.rule_id}
            </Badge>
            {finding.ticket_id && (
              <Badge className="gap-1 bg-success/15 text-success border-success/30 hover:bg-success/15">
                <Ticket className="size-3" />
                {finding.ticket_id}
              </Badge>
            )}
          </div>
          <h3 className="text-sm font-semibold leading-snug">{finding.title}</h3>
          <p className="flex items-center gap-1 font-mono text-xs text-muted-foreground">
            <MapPin className="size-3" />
            {finding.file_path}
            {finding.line_start ? `:${finding.line_start}` : ""}
            {finding.line_end && finding.line_end !== finding.line_start
              ? `-${finding.line_end}`
              : ""}
          </p>
        </div>

        <DecisionControl
          finding={finding}
          editable={editable}
          onDecisionChange={onDecisionChange}
        />
      </CardHeader>

      <CardContent className="flex flex-col gap-3">
        <p className="text-sm text-muted-foreground">{finding.description}</p>

        {hasDetails && (
          <details className="group rounded-md border border-border/60 bg-muted/20 open:bg-muted/30">
            <summary className="flex cursor-pointer list-none items-center justify-between px-3 py-2 text-xs font-medium text-foreground/90">
              AI Analysis & Remediation
              <ChevronDown className="size-3.5 text-muted-foreground transition-transform group-open:rotate-180" />
            </summary>
            <div className="flex flex-col gap-3 border-t border-border/60 px-3 py-3 text-sm">
              {finding.ai_analysis && (
                <div className="prose prose-sm dark:prose-invert max-w-none prose-headings:text-sm prose-headings:font-semibold prose-headings:text-foreground/90 prose-p:text-muted-foreground prose-li:text-muted-foreground prose-strong:text-foreground/90 prose-code:rounded prose-code:bg-muted prose-code:px-1 prose-code:py-0.5 prose-code:text-xs prose-pre:bg-muted/60 prose-pre:text-xs">
                  <ReactMarkdown>{finding.ai_analysis}</ReactMarkdown>
                </div>
              )}
              {finding.remediation && (
                <div className="rounded-md border border-primary/20 bg-primary/5 p-2.5 text-sm">
                  <span className="font-medium text-primary">Remediation: </span>
                  <span className="text-foreground/90">{finding.remediation}</span>
                </div>
              )}
            </div>
          </details>
        )}
      </CardContent>
    </Card>
  );
}

function DecisionControl({
  finding,
  editable,
  onDecisionChange,
}: {
  finding: Finding;
  editable: boolean;
  onDecisionChange?: (findingId: string, decision: "approved" | "rejected") => void;
}) {
  if (!editable) {
    if (finding.approval_status === "approved") {
      return (
        <Badge className="shrink-0 gap-1 bg-success/15 text-success border-success/30 hover:bg-success/15">
          <CheckCircle2 className="size-3" />
          Approved
        </Badge>
      );
    }
    if (finding.approval_status === "rejected") {
      return (
        <Badge variant="outline" className="shrink-0 gap-1 text-muted-foreground">
          <XCircle className="size-3" />
          Rejected
        </Badge>
      );
    }
    return (
      <Badge variant="outline" className="shrink-0 text-muted-foreground">
        Pending
      </Badge>
    );
  }

  return (
    <div className="flex shrink-0 gap-1.5">
      <Button
        type="button"
        size="sm"
        variant={finding.approval_status === "approved" ? "default" : "outline"}
        className={cn(
          "h-8 gap-1",
          finding.approval_status === "approved" && "bg-success text-success-foreground hover:bg-success/90"
        )}
        onClick={() => onDecisionChange?.(finding.id, "approved")}
      >
        <CheckCircle2 className="size-3.5" />
        Approve
      </Button>
      <Button
        type="button"
        size="sm"
        variant={finding.approval_status === "rejected" ? "default" : "outline"}
        className={cn(
          "h-8 gap-1",
          finding.approval_status === "rejected" && "bg-destructive text-white hover:bg-destructive/90"
        )}
        onClick={() => onDecisionChange?.(finding.id, "rejected")}
      >
        <XCircle className="size-3.5" />
        Reject
      </Button>
    </div>
  );
}
