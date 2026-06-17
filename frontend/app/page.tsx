import {
  BrainCircuit,
  GitBranch,
  Radio,
  ShieldCheck,
  UserCheck,
  Workflow,
} from "lucide-react";
import { ScanInput } from "@/components/scan-input";
import { RecentScansStrip } from "@/components/recent-scans-strip";

const FEATURES = [
  {
    icon: GitBranch,
    title: "LangGraph orchestration",
    description:
      "A durable, checkpointed state machine routes findings through scanner, classifier, analyzer, and reporter agents.",
  },
  {
    icon: UserCheck,
    title: "Human-in-the-loop approval",
    description:
      "The graph pauses before acting on findings — nothing gets ticketed or notified without your sign-off.",
  },
  {
    icon: BrainCircuit,
    title: "Dual-model RAG analysis",
    description:
      "Fast triage on gpt-4.1-mini, deep remediation on gpt-4o, grounded in a pgvector vulnerability knowledge base.",
  },
  {
    icon: Radio,
    title: "Live SSE streaming",
    description:
      "Watch findings, status changes, and pipeline progress arrive in real time as the agents work.",
  },
  {
    icon: Workflow,
    title: "MCP tool integrations",
    description:
      "GitHub fetch, ticket creation, and Slack notifications exposed as standardized MCP tools.",
  },
  {
    icon: ShieldCheck,
    title: "Full audit trail",
    description:
      "Every scan, decision, and ticket is persisted to Postgres for a complete, reviewable history.",
  },
];

export default function Home() {
  return (
    <div className="flex flex-col items-center">
      <section className="flex w-full flex-col items-center px-4 pt-20 pb-16 text-center sm:pt-28">
        <span className="mb-5 inline-flex items-center gap-1.5 rounded-full border border-primary/30 bg-primary/10 px-3 py-1 text-xs font-medium text-primary">
          Multi-agent · LangGraph · RAG
        </span>
        <h1 className="max-w-2xl text-4xl font-semibold tracking-tight text-glow sm:text-5xl">
          Ship secure code, <span className="text-primary">faster.</span>
        </h1>
        <p className="mt-4 max-w-lg text-balance text-muted-foreground">
          Paste a GitHub repo. Sentinel scans it, triages findings with an
          LLM pipeline, and waits for your approval before it touches
          anything.
        </p>
        <div className="mt-8 flex w-full flex-col items-center">
          <ScanInput />
          <RecentScansStrip />
        </div>
      </section>

      <section className="w-full border-t border-border/60 bg-card/20 px-4 py-16">
        <div className="mx-auto max-w-5xl">
          <h2 className="text-center text-sm font-medium uppercase tracking-wider text-muted-foreground">
            How it works
          </h2>
          <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {FEATURES.map((feature) => (
              <div
                key={feature.title}
                className="rounded-xl border border-border/60 bg-card/50 p-5 transition-colors hover:border-primary/30"
              >
                <feature.icon className="size-5 text-primary" />
                <h3 className="mt-3 text-sm font-semibold">{feature.title}</h3>
                <p className="mt-1.5 text-sm text-muted-foreground">
                  {feature.description}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>
    </div>
  );
}
