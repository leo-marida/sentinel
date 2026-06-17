# SENTINEL — AI-Native DevSecOps Copilot
### Claude Code Project Specification · Complete Build Guide

---

## 0. Project Overview

Sentinel is a production-grade, multi-agent DevSecOps copilot. It monitors GitHub repositories for security vulnerabilities and code quality issues, triages them using a **LangGraph** state machine with **MCP** tool integrations, routes findings through a **human-in-the-loop approval** flow, and streams remediation reports token-by-token to a **Next.js** real-time dashboard.

**What makes it impressive architecturally:**
- LangGraph state machine with persistent checkpointing (durable agent execution)
- MCP server exposing GitHub, Jira-compatible ticketing, and Slack notification tools
- Human-in-the-loop: agent pauses mid-graph, waits for user approval, resumes from exact state
- Dual-stage LLM routing: `gpt-4.1-mini` for fast classification, `gpt-4o` for deep analysis
- pgvector RAG over historical vulnerability embeddings for contextual remediation
- LangSmith tracing on every graph execution (free Developer tier: 5,000 traces/month)
- Server-Sent Events (SSE) streaming from FastAPI → Next.js dashboard
- Full audit log in Supabase Postgres

**Live demo flow:** User pastes a GitHub repo URL → Sentinel scans it → findings appear in real-time → user approves/rejects each finding → agent auto-creates a Jira ticket + Slack notification → remediation report streams to screen.

---

## 1. Tech Stack

### AI & Orchestration
| Tool | Purpose | Cost |
|---|---|---|
| `gpt-4.1-mini` (OpenAI) | Fast classification, triage routing, embedding | ~$0.40/1M input tokens |
| `gpt-4o` (OpenAI) | Deep vulnerability analysis, remediation plans | ~$2.50/1M input tokens |
| LangGraph (`langgraph>=0.2`) | Agent state machine, checkpointing, HITL | Free (open source) |
| LangChain (`langchain>=0.3`) | Tool wrappers, prompt templates, RAG chain | Free (open source) |
| LangSmith | Tracing, evals, debugging | Free (5,000 traces/month) |
| OpenAI Embeddings (`text-embedding-3-small`) | Code chunk embeddings for pgvector RAG | ~$0.02/1M tokens |

### Backend
| Tool | Purpose | Cost |
|---|---|---|
| FastAPI + Python 3.11 | REST API, SSE streaming, MCP server | Free |
| Supabase | Postgres + pgvector + Auth | Free (500MB, pgvector included) |
| Semgrep (OSS) | Static analysis / SAST scanning | Free |
| Bandit | Python security linting | Free |
| PyGitHub | GitHub repo access via API | Free |

### Frontend
| Tool | Purpose | Cost |
|---|---|---|
| Next.js 15 (App Router) | Dashboard UI | Free |
| TypeScript | Type safety | Free |
| Tailwind CSS v4 | Styling | Free |
| shadcn/ui | Component library | Free |
| Lucide React | Icons | Free |

### Infrastructure
| Service | Purpose | Cost |
|---|---|---|
| Vercel | Next.js frontend hosting | Free (Hobby tier) |
| Render | FastAPI backend hosting | Free (spins down after 15 min inactivity — fine for portfolio) |
| Supabase | Database + pgvector | Free tier |
| LangSmith | Observability | Free Developer tier |
| GitHub Actions | CI/CD pipeline | Free (2,000 min/month) |

> **Important — Render free tier:** The backend will spin down after 15 minutes of inactivity and take ~30 seconds to cold-start on the next request. This is acceptable for a portfolio project. Add a "Waking up server..." loading state in the frontend to handle this gracefully.

> **Important — Supabase free tier:** Projects pause after 7 days of inactivity. The frontend should catch connection errors and show a clear "Database is starting up" message. Supabase unpauses within ~20 seconds after the first request.

---

## 2. Repository Structure

```
sentinel/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                    # FastAPI app entry point
│   │   ├── config.py                  # Pydantic Settings (env vars)
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── routes/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── scans.py           # POST /scans, GET /scans/{id}
│   │   │   │   ├── stream.py          # GET /scans/{id}/stream (SSE)
│   │   │   │   ├── approvals.py       # POST /scans/{id}/approve, /reject
│   │   │   │   └── health.py          # GET /health
│   │   │   └── deps.py                # FastAPI dependency injection
│   │   ├── agent/
│   │   │   ├── __init__.py
│   │   │   ├── graph.py               # LangGraph state machine definition
│   │   │   ├── state.py               # SentinelState TypedDict
│   │   │   ├── nodes/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── scanner.py         # Node: run Semgrep + Bandit
│   │   │   │   ├── classifier.py      # Node: gpt-4.1-mini triage
│   │   │   │   ├── analyzer.py        # Node: gpt-4o deep analysis + RAG
│   │   │   │   ├── human_review.py    # Node: interrupt for HITL approval
│   │   │   │   ├── ticket_creator.py  # Node: create Jira-style ticket
│   │   │   │   ├── notifier.py        # Node: Slack notification
│   │   │   │   └── reporter.py        # Node: stream final report
│   │   │   └── checkpointer.py        # Supabase-backed checkpoint saver
│   │   ├── mcp/
│   │   │   ├── __init__.py
│   │   │   └── server.py              # MCP server exposing tools
│   │   ├── rag/
│   │   │   ├── __init__.py
│   │   │   ├── embedder.py            # Embed code chunks with text-embedding-3-small
│   │   │   └── retriever.py           # pgvector similarity search
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── github_service.py      # Fetch repo files via PyGitHub
│   │   │   ├── scanner_service.py     # Semgrep + Bandit runners
│   │   │   └── notification_service.py # Slack webhook sender
│   │   ├── db/
│   │   │   ├── __init__.py
│   │   │   ├── client.py              # Supabase async client
│   │   │   └── models.py              # SQLAlchemy / raw SQL models
│   │   └── utils/
│   │       ├── __init__.py
│   │       ├── security.py            # API key hashing, rate limiting
│   │       └── streaming.py           # SSE event formatter
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── test_graph.py
│   │   ├── test_scanner.py
│   │   └── test_api.py
│   ├── pyproject.toml
│   ├── requirements.txt
│   ├── .env.example
│   └── Dockerfile
├── frontend/
│   ├── app/
│   │   ├── layout.tsx
│   │   ├── page.tsx                   # Landing / scan input
│   │   ├── dashboard/
│   │   │   ├── page.tsx               # Scan list
│   │   │   └── [scanId]/
│   │   │       └── page.tsx           # Live scan view + HITL approval UI
│   │   └── api/
│   │       └── proxy/
│   │           └── route.ts           # Next.js API route (proxies to backend)
│   ├── components/
│   │   ├── ui/                        # shadcn/ui components
│   │   ├── scan-input.tsx
│   │   ├── finding-card.tsx
│   │   ├── approval-panel.tsx
│   │   ├── stream-viewer.tsx          # SSE consumer + live text renderer
│   │   ├── severity-badge.tsx
│   │   └── graph-status.tsx           # Live LangGraph node progress
│   ├── lib/
│   │   ├── api.ts                     # API client (fetch wrapper)
│   │   ├── sse.ts                     # EventSource / SSE hook
│   │   └── types.ts                   # Shared TypeScript types
│   ├── hooks/
│   │   ├── use-scan-stream.ts         # SSE hook for live updates
│   │   └── use-approval.ts            # Approval mutation hook
│   ├── next.config.ts
│   ├── tailwind.config.ts
│   ├── tsconfig.json
│   └── package.json
├── .github/
│   └── workflows/
│       ├── backend-ci.yml             # Python tests + lint on PR
│       └── frontend-ci.yml            # TypeScript typecheck + build on PR
├── docker-compose.yml                 # Local dev: backend + supabase local
├── .env.example
└── README.md
```

---

## 3. Environment Variables

### Backend `.env`
```env
# OpenAI
OPENAI_API_KEY=sk-...
OPENAI_FAST_MODEL=gpt-4.1-mini          # Classification, triage
OPENAI_SMART_MODEL=gpt-4o               # Deep analysis
OPENAI_EMBEDDING_MODEL=text-embedding-3-small

# Supabase
SUPABASE_URL=https://xxxx.supabase.co
SUPABASE_ANON_KEY=eyJ...
SUPABASE_SERVICE_ROLE_KEY=eyJ...        # Server-side only, never expose to client
DATABASE_URL=postgresql+asyncpg://postgres:password@db.xxxx.supabase.co:5432/postgres

# GitHub
GITHUB_TOKEN=ghp_...                    # Personal access token (read:repo scope only)

# LangSmith
LANGSMITH_API_KEY=ls__...
LANGSMITH_PROJECT=sentinel
LANGCHAIN_TRACING_V2=true

# Slack (optional — webhook URL for notifications)
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...

# App
API_SECRET_KEY=<generate: openssl rand -hex 32>
CORS_ORIGINS=http://localhost:3000,https://sentinel-frontend.vercel.app
ENVIRONMENT=development                 # development | production
```

### Frontend `.env.local`
```env
NEXT_PUBLIC_API_URL=http://localhost:8000   # dev
# NEXT_PUBLIC_API_URL=https://sentinel-api.onrender.com  # prod
```

> **Security rule:** Never put `SUPABASE_SERVICE_ROLE_KEY` or `OPENAI_API_KEY` in any frontend env var. All AI calls happen server-side in the FastAPI backend only.

---

## 4. Database Schema (Supabase / PostgreSQL)

Run these in the Supabase SQL editor. Enable the pgvector extension first.

```sql
-- Enable pgvector
CREATE EXTENSION IF NOT EXISTS vector;

-- Scans table
CREATE TABLE scans (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  repo_url TEXT NOT NULL,
  repo_name TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'queued',
  -- status: queued | scanning | classifying | analyzing | awaiting_approval | creating_tickets | complete | failed
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  completed_at TIMESTAMPTZ,
  summary JSONB,                        -- { total_findings, critical, high, medium, low }
  error_message TEXT
);

-- Findings table
CREATE TABLE findings (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  scan_id UUID NOT NULL REFERENCES scans(id) ON DELETE CASCADE,
  file_path TEXT NOT NULL,
  line_start INTEGER,
  line_end INTEGER,
  rule_id TEXT NOT NULL,               -- Semgrep rule ID or Bandit check
  severity TEXT NOT NULL,              -- critical | high | medium | low | info
  title TEXT NOT NULL,
  description TEXT NOT NULL,
  raw_output JSONB,                    -- Original scanner output
  ai_analysis TEXT,                    -- GPT-4o deep analysis
  remediation TEXT,                    -- Suggested fix
  approval_status TEXT DEFAULT 'pending', -- pending | approved | rejected
  approved_at TIMESTAMPTZ,
  ticket_id TEXT,                      -- External ticket reference
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Code embeddings for RAG
CREATE TABLE code_embeddings (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  scan_id UUID REFERENCES scans(id) ON DELETE CASCADE,
  file_path TEXT NOT NULL,
  chunk_index INTEGER NOT NULL,
  content TEXT NOT NULL,
  embedding VECTOR(1536),              -- text-embedding-3-small dimension
  metadata JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Vulnerability knowledge base (pre-seeded for RAG context)
CREATE TABLE vuln_knowledge (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  cve_id TEXT,
  title TEXT NOT NULL,
  description TEXT NOT NULL,
  remediation TEXT NOT NULL,
  severity TEXT NOT NULL,
  tags TEXT[],
  embedding VECTOR(1536),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Agent checkpoints (LangGraph durable state)
CREATE TABLE agent_checkpoints (
  thread_id TEXT NOT NULL,
  checkpoint_id TEXT NOT NULL,
  parent_id TEXT,
  checkpoint JSONB NOT NULL,
  metadata JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (thread_id, checkpoint_id)
);

-- Audit log
CREATE TABLE audit_log (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  scan_id UUID REFERENCES scans(id) ON DELETE SET NULL,
  event_type TEXT NOT NULL,
  payload JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_findings_scan_id ON findings(scan_id);
CREATE INDEX idx_findings_severity ON findings(severity);
CREATE INDEX idx_findings_approval ON findings(approval_status);
CREATE INDEX idx_code_embeddings_scan_id ON code_embeddings(scan_id);
CREATE INDEX idx_embeddings_vector ON code_embeddings USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX idx_vuln_knowledge_vector ON vuln_knowledge USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX idx_checkpoints_thread ON agent_checkpoints(thread_id);

-- Row Level Security (enable but keep permissive for now — lock down for prod)
ALTER TABLE scans ENABLE ROW LEVEL SECURITY;
ALTER TABLE findings ENABLE ROW LEVEL SECURITY;
ALTER TABLE code_embeddings ENABLE ROW LEVEL SECURITY;

-- Service role bypasses RLS automatically
-- For now: allow all via service role key (backend only)
```

---

## 5. Backend Implementation

### 5.1 FastAPI Entry Point (`app/main.py`)

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.api.routes import scans, stream, approvals, health
from app.db.client import init_db

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield

app = FastAPI(
    title="Sentinel API",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.ENVIRONMENT == "development" else None,
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH"],
    allow_headers=["*"],
)

app.include_router(health.router, tags=["health"])
app.include_router(scans.router, prefix="/api/v1", tags=["scans"])
app.include_router(stream.router, prefix="/api/v1", tags=["stream"])
app.include_router(approvals.router, prefix="/api/v1", tags=["approvals"])
```

### 5.2 Config (`app/config.py`)

```python
from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    OPENAI_API_KEY: str
    OPENAI_FAST_MODEL: str = "gpt-4.1-mini"
    OPENAI_SMART_MODEL: str = "gpt-4o"
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"

    SUPABASE_URL: str
    SUPABASE_ANON_KEY: str
    SUPABASE_SERVICE_ROLE_KEY: str
    DATABASE_URL: str

    GITHUB_TOKEN: str

    LANGSMITH_API_KEY: str = ""
    LANGSMITH_PROJECT: str = "sentinel"

    SLACK_WEBHOOK_URL: str = ""

    API_SECRET_KEY: str
    CORS_ORIGINS: List[str] = ["http://localhost:3000"]
    ENVIRONMENT: str = "development"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()
```

### 5.3 LangGraph Agent State (`app/agent/state.py`)

```python
from typing import TypedDict, Annotated, List, Optional
from langgraph.graph.message import add_messages

class Finding(TypedDict):
    id: str
    file_path: str
    line_start: int
    line_end: int
    rule_id: str
    severity: str          # critical | high | medium | low | info
    title: str
    description: str
    raw_output: dict
    ai_analysis: Optional[str]
    remediation: Optional[str]
    approval_status: str   # pending | approved | rejected

class SentinelState(TypedDict):
    # Core
    scan_id: str
    repo_url: str
    repo_name: str

    # Pipeline data
    files: List[dict]                  # {path, content}
    raw_findings: List[dict]           # Raw scanner output
    findings: List[Finding]            # Enriched findings
    approved_findings: List[Finding]   # Post-HITL approved subset
    report: Optional[str]              # Final markdown report

    # Control flow
    current_node: str
    error: Optional[str]
    stream_tokens: Annotated[List[str], add_messages]  # For SSE
```

### 5.4 LangGraph State Machine (`app/agent/graph.py`)

```python
import asyncio
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from app.agent.state import SentinelState
from app.agent.nodes import (
    scanner, classifier, analyzer,
    human_review, ticket_creator, notifier, reporter
)
from app.agent.checkpointer import SupabaseCheckpointer

def should_deep_analyze(state: SentinelState) -> str:
    """Route: skip deep analysis if no findings after classification."""
    critical_or_high = [
        f for f in state["findings"]
        if f["severity"] in ("critical", "high")
    ]
    return "analyzer" if critical_or_high else "reporter"

def should_create_tickets(state: SentinelState) -> str:
    """Route: only create tickets if any findings were approved."""
    approved = [f for f in state["findings"] if f["approval_status"] == "approved"]
    return "ticket_creator" if approved else "reporter"

def build_sentinel_graph(checkpointer=None):
    graph = StateGraph(SentinelState)

    # Register nodes
    graph.add_node("scanner", scanner.run)
    graph.add_node("classifier", classifier.run)
    graph.add_node("analyzer", analyzer.run)
    graph.add_node("human_review", human_review.run)   # HITL interrupt node
    graph.add_node("ticket_creator", ticket_creator.run)
    graph.add_node("notifier", notifier.run)
    graph.add_node("reporter", reporter.run)

    # Edges
    graph.set_entry_point("scanner")
    graph.add_edge("scanner", "classifier")
    graph.add_conditional_edges("classifier", should_deep_analyze)
    graph.add_edge("analyzer", "human_review")
    graph.add_conditional_edges("human_review", should_create_tickets)
    graph.add_edge("ticket_creator", "notifier")
    graph.add_edge("notifier", "reporter")
    graph.add_edge("reporter", END)

    return graph.compile(
        checkpointer=checkpointer or MemorySaver(),
        interrupt_before=["human_review"],  # HITL: pause before this node
    )

sentinel_graph = build_sentinel_graph()
```

### 5.5 Classifier Node (`app/agent/nodes/classifier.py`)

```python
"""
Uses gpt-4.1-mini for fast, cheap triage classification.
Model choice: gpt-4.1-mini is 83% cheaper than gpt-4o-mini while being smarter.
At ~$0.40/1M input tokens it costs fractions of a cent per scan.
"""
from openai import AsyncOpenAI
from app.config import settings
from app.agent.state import SentinelState, Finding
import json
import uuid

client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

CLASSIFY_SYSTEM = """You are a security triage expert. Given a list of raw scanner findings,
classify each one. Return ONLY valid JSON — an array of objects with fields:
id, severity (critical|high|medium|low|info), title, description.
Be concise. Do not invent findings not in the input."""

async def run(state: SentinelState) -> dict:
    if not state["raw_findings"]:
        return {"findings": [], "current_node": "classifier"}

    # Batch classify all raw findings in one call (cost efficient)
    raw_text = json.dumps(state["raw_findings"][:50], indent=2)  # Cap at 50

    response = await client.chat.completions.create(
        model=settings.OPENAI_FAST_MODEL,    # gpt-4.1-mini
        temperature=0,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": CLASSIFY_SYSTEM},
            {"role": "user", "content": f"Classify these findings:\n{raw_text}"},
        ],
        max_tokens=2000,
    )

    classified = json.loads(response.choices[0].message.content)
    findings_list = classified.get("findings", classified) if isinstance(classified, dict) else classified

    findings: list[Finding] = []
    for i, raw in enumerate(state["raw_findings"][:50]):
        enriched = findings_list[i] if i < len(findings_list) else {}
        findings.append(Finding(
            id=str(uuid.uuid4()),
            file_path=raw.get("path", "unknown"),
            line_start=raw.get("start", {}).get("line", 0),
            line_end=raw.get("end", {}).get("line", 0),
            rule_id=raw.get("check_id", raw.get("test_id", "unknown")),
            severity=enriched.get("severity", "medium"),
            title=enriched.get("title", raw.get("extra", {}).get("message", "Finding")),
            description=enriched.get("description", ""),
            raw_output=raw,
            ai_analysis=None,
            remediation=None,
            approval_status="pending",
        ))

    return {"findings": findings, "current_node": "classifier"}
```

### 5.6 Analyzer Node (`app/agent/nodes/analyzer.py`)

```python
"""
Uses gpt-4o for deep, contextual vulnerability analysis with RAG.
Only runs on critical/high severity findings to keep costs low.
"""
from openai import AsyncOpenAI
from app.config import settings
from app.agent.state import SentinelState
from app.rag.retriever import retrieve_similar_vulns

client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

ANALYZE_SYSTEM = """You are a senior application security engineer.
Analyze the security finding and provide:
1. Root cause explanation (2-3 sentences)
2. Concrete remediation steps (numbered list, code examples where helpful)
3. Severity justification
Be precise and actionable. Reference the similar historical vulnerabilities provided."""

async def run(state: SentinelState) -> dict:
    critical_high = [
        f for f in state["findings"]
        if f["severity"] in ("critical", "high")
    ]

    updated_findings = list(state["findings"])

    for finding in critical_high:
        # RAG: fetch similar historical vulnerabilities from pgvector
        similar_context = await retrieve_similar_vulns(
            query=f"{finding['title']} {finding['description']}",
            top_k=3,
        )

        context_text = "\n\n".join([
            f"[Similar: {v['title']}]\n{v['remediation']}"
            for v in similar_context
        ]) or "No similar historical findings available."

        response = await client.chat.completions.create(
            model=settings.OPENAI_SMART_MODEL,    # gpt-4o
            temperature=0.2,
            messages=[
                {"role": "system", "content": ANALYZE_SYSTEM},
                {"role": "user", "content": (
                    f"**Finding:** {finding['title']}\n"
                    f"**File:** {finding['file_path']} (line {finding['line_start']})\n"
                    f"**Description:** {finding['description']}\n\n"
                    f"**Similar historical vulnerabilities:**\n{context_text}"
                )},
            ],
            max_tokens=800,
        )

        analysis = response.choices[0].message.content

        # Update the finding in place
        for i, f in enumerate(updated_findings):
            if f["id"] == finding["id"]:
                updated_findings[i] = {**f, "ai_analysis": analysis}
                break

    return {"findings": updated_findings, "current_node": "analyzer"}
```

### 5.7 HITL Node (`app/agent/nodes/human_review.py`)

```python
"""
Human-in-the-loop node. The LangGraph graph is compiled with
interrupt_before=["human_review"], so execution pauses BEFORE this node runs.
The API endpoint POST /scans/{id}/approve resumes the graph with updated state.
This node itself just marks approved findings.
"""
from app.agent.state import SentinelState

async def run(state: SentinelState) -> dict:
    """
    By the time this runs, the frontend has already submitted approvals.
    The graph was resumed with the updated findings (approval_status set).
    This node just filters and passes through.
    """
    approved = [
        f for f in state["findings"]
        if f["approval_status"] == "approved"
    ]
    return {
        "approved_findings": approved,
        "current_node": "human_review",
    }
```

### 5.8 SSE Stream Endpoint (`app/api/routes/stream.py`)

```python
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from app.db.client import get_supabase
import asyncio
import json

router = APIRouter()

async def scan_event_generator(scan_id: str):
    """
    Polls Supabase for scan status updates and streams them as SSE events.
    In production, replace with Supabase Realtime for push-based updates.
    """
    supabase = get_supabase()
    last_status = None
    last_finding_count = 0

    yield f"data: {json.dumps({'type': 'connected', 'scan_id': scan_id})}\n\n"

    for _ in range(300):  # Max 5 min (300 * 1s)
        await asyncio.sleep(1)

        scan = supabase.table("scans").select("*").eq("id", scan_id).single().execute()
        if not scan.data:
            yield f"data: {json.dumps({'type': 'error', 'message': 'Scan not found'})}\n\n"
            return

        scan_data = scan.data

        # Stream status changes
        if scan_data["status"] != last_status:
            last_status = scan_data["status"]
            yield f"data: {json.dumps({'type': 'status', 'status': scan_data['status']})}\n\n"

        # Stream new findings
        findings = (
            supabase.table("findings")
            .select("*")
            .eq("scan_id", scan_id)
            .order("created_at")
            .execute()
        )
        if findings.data and len(findings.data) > last_finding_count:
            new_findings = findings.data[last_finding_count:]
            last_finding_count = len(findings.data)
            for finding in new_findings:
                yield f"data: {json.dumps({'type': 'finding', 'finding': finding})}\n\n"

        if scan_data["status"] in ("complete", "failed"):
            yield f"data: {json.dumps({'type': 'done', 'summary': scan_data.get('summary')})}\n\n"
            return

    yield f"data: {json.dumps({'type': 'timeout'})}\n\n"

@router.get("/scans/{scan_id}/stream")
async def stream_scan(scan_id: str):
    return StreamingResponse(
        scan_event_generator(scan_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",        # Disable Nginx buffering
            "Connection": "keep-alive",
        },
    )
```

### 5.9 Approval Endpoint (`app/api/routes/approvals.py`)

```python
"""
Resume the paused LangGraph graph after human review.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List
from app.agent.graph import sentinel_graph
from app.db.client import get_supabase

router = APIRouter()

class ApprovalDecision(BaseModel):
    finding_id: str
    decision: str  # "approved" | "rejected"

class ApprovalRequest(BaseModel):
    decisions: List[ApprovalDecision]

@router.post("/scans/{scan_id}/approve")
async def submit_approval(scan_id: str, body: ApprovalRequest):
    supabase = get_supabase()

    # Persist approval decisions to DB
    for decision in body.decisions:
        supabase.table("findings").update(
            {"approval_status": decision.decision}
        ).eq("id", decision.finding_id).eq("scan_id", scan_id).execute()

    # Fetch current graph state
    config = {"configurable": {"thread_id": scan_id}}
    current_state = await sentinel_graph.aget_state(config)
    if not current_state:
        raise HTTPException(status_code=404, detail="Scan state not found")

    # Update findings in graph state with approval decisions
    findings = current_state.values.get("findings", [])
    decision_map = {d.finding_id: d.decision for d in body.decisions}
    updated_findings = [
        {**f, "approval_status": decision_map.get(f["id"], f["approval_status"])}
        for f in findings
    ]

    # Update state and resume graph
    await sentinel_graph.aupdate_state(
        config,
        {"findings": updated_findings},
        as_node="human_review",
    )

    # Resume graph execution from HITL checkpoint
    await sentinel_graph.ainvoke(None, config=config)

    return {"status": "resumed", "scan_id": scan_id}
```

### 5.10 MCP Server (`app/mcp/server.py`)

```python
"""
MCP server exposing Sentinel tools for agent use.
Uses the mcp Python SDK (pip install mcp).
"""
from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.types import Tool, TextContent
import mcp.types as types
from app.services.github_service import fetch_repo_files
from app.services.notification_service import send_slack_notification
from app.db.client import get_supabase
import json

app = Server("sentinel-mcp")

@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="fetch_github_repo",
            description="Fetch all source files from a GitHub repository for analysis",
            inputSchema={
                "type": "object",
                "properties": {
                    "repo_url": {"type": "string", "description": "GitHub repo URL"},
                    "max_files": {"type": "integer", "default": 100},
                },
                "required": ["repo_url"],
            },
        ),
        Tool(
            name="create_ticket",
            description="Create a security ticket for an approved finding",
            inputSchema={
                "type": "object",
                "properties": {
                    "finding_id": {"type": "string"},
                    "title": {"type": "string"},
                    "description": {"type": "string"},
                    "severity": {"type": "string"},
                },
                "required": ["finding_id", "title", "description", "severity"],
            },
        ),
        Tool(
            name="send_notification",
            description="Send a Slack notification about scan results",
            inputSchema={
                "type": "object",
                "properties": {
                    "message": {"type": "string"},
                    "scan_id": {"type": "string"},
                },
                "required": ["message"],
            },
        ),
    ]

@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    supabase = get_supabase()

    if name == "fetch_github_repo":
        files = await fetch_repo_files(
            repo_url=arguments["repo_url"],
            max_files=arguments.get("max_files", 100),
        )
        return [TextContent(type="text", text=json.dumps({"files": files, "count": len(files)}))]

    elif name == "create_ticket":
        # Store ticket in Supabase findings table
        supabase.table("findings").update(
            {"ticket_id": f"SENTINEL-{arguments['finding_id'][:8].upper()}"}
        ).eq("id", arguments["finding_id"]).execute()
        return [TextContent(type="text", text=json.dumps({"ticket_created": True}))]

    elif name == "send_notification":
        await send_slack_notification(
            message=arguments["message"],
            scan_id=arguments.get("scan_id"),
        )
        return [TextContent(type="text", text=json.dumps({"notified": True}))]

    raise ValueError(f"Unknown tool: {name}")
```

---

## 6. Frontend Implementation

### 6.1 SSE Hook (`frontend/hooks/use-scan-stream.ts`)

```typescript
import { useEffect, useRef, useState, useCallback } from "react";

export type ScanEvent =
  | { type: "connected"; scan_id: string }
  | { type: "status"; status: string }
  | { type: "finding"; finding: Finding }
  | { type: "done"; summary: ScanSummary }
  | { type: "error"; message: string }
  | { type: "timeout" };

export interface Finding {
  id: string;
  file_path: string;
  line_start: number;
  severity: "critical" | "high" | "medium" | "low" | "info";
  title: string;
  description: string;
  ai_analysis?: string;
  remediation?: string;
  approval_status: "pending" | "approved" | "rejected";
}

export interface ScanSummary {
  total_findings: number;
  critical: number;
  high: number;
  medium: number;
  low: number;
}

export function useScanStream(scanId: string | null) {
  const [status, setStatus] = useState<string>("idle");
  const [findings, setFindings] = useState<Finding[]>([]);
  const [summary, setSummary] = useState<ScanSummary | null>(null);
  const [isComplete, setIsComplete] = useState(false);
  const eventSourceRef = useRef<EventSource | null>(null);

  useEffect(() => {
    if (!scanId) return;

    const apiUrl = process.env.NEXT_PUBLIC_API_URL;
    const es = new EventSource(`${apiUrl}/api/v1/scans/${scanId}/stream`);
    eventSourceRef.current = es;

    es.onmessage = (event) => {
      const data: ScanEvent = JSON.parse(event.data);

      switch (data.type) {
        case "status":
          setStatus(data.status);
          break;
        case "finding":
          setFindings((prev) => {
            const exists = prev.find((f) => f.id === data.finding.id);
            if (exists) return prev;
            return [...prev, data.finding];
          });
          break;
        case "done":
          setSummary(data.summary);
          setIsComplete(true);
          es.close();
          break;
        case "error":
          setStatus("failed");
          es.close();
          break;
        case "timeout":
          es.close();
          break;
      }
    };

    es.onerror = () => {
      setStatus("connection_lost");
      es.close();
    };

    return () => {
      es.close();
    };
  }, [scanId]);

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

  return { status, findings, summary, isComplete, updateFindingApproval };
}
```

### 6.2 Severity Badge Component (`frontend/components/severity-badge.tsx`)

```typescript
const SEVERITY_CONFIG = {
  critical: { label: "Critical", className: "bg-red-100 text-red-800 border-red-200" },
  high:     { label: "High",     className: "bg-orange-100 text-orange-800 border-orange-200" },
  medium:   { label: "Medium",   className: "bg-yellow-100 text-yellow-800 border-yellow-200" },
  low:      { label: "Low",      className: "bg-blue-100 text-blue-800 border-blue-200" },
  info:     { label: "Info",     className: "bg-gray-100 text-gray-700 border-gray-200" },
} as const;

export function SeverityBadge({ severity }: { severity: keyof typeof SEVERITY_CONFIG }) {
  const config = SEVERITY_CONFIG[severity] ?? SEVERITY_CONFIG.info;
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border ${config.className}`}>
      {config.label}
    </span>
  );
}
```

---

## 7. Python Dependencies (`backend/requirements.txt`)

```txt
# Web framework
fastapi==0.115.0
uvicorn[standard]==0.30.0
pydantic==2.8.0
pydantic-settings==2.4.0

# AI / LangGraph
openai==1.45.0
langchain==0.3.0
langchain-openai==0.2.0
langgraph==0.2.20
langsmith==0.1.100

# MCP
mcp==1.0.0

# Database
supabase==2.7.0
asyncpg==0.29.0
sqlalchemy[asyncio]==2.0.35

# GitHub
PyGithub==2.4.0

# Security scanning
semgrep==1.90.0
bandit==1.7.10

# Utilities
httpx==0.27.0
python-dotenv==1.0.1
tenacity==9.0.0         # Retry logic for API calls

# Dev / testing
pytest==8.3.0
pytest-asyncio==0.24.0
pytest-cov==5.0.0
ruff==0.6.0             # Linting
```

---

## 8. Deployment

### 8.1 Backend → Render

1. Push backend code to GitHub (in `backend/` directory)
2. Go to [render.com](https://render.com) → New → Web Service
3. Connect GitHub repo, set **Root Directory** to `backend`
4. Settings:
   - **Runtime:** Python 3.11
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - **Instance Type:** Free
5. Add all environment variables from `.env` in the Render dashboard
6. Deploy — URL will be `https://sentinel-api.onrender.com`

> Add a `/health` endpoint that returns `{"status": "ok"}`. The frontend should hit this on load and show a "Server warming up..." skeleton if it gets a connection error (Render cold start).

### 8.2 Frontend → Vercel

1. Push frontend code to GitHub (in `frontend/` directory)
2. Go to [vercel.com](https://vercel.com) → New Project → Import repo
3. Set **Root Directory** to `frontend`
4. Framework preset: **Next.js** (auto-detected)
5. Add environment variable:
   - `NEXT_PUBLIC_API_URL` = `https://sentinel-api.onrender.com`
6. Deploy — URL will be `https://sentinel-frontend.vercel.app`

### 8.3 CI/CD (`.github/workflows/backend-ci.yml`)

```yaml
name: Backend CI

on:
  push:
    branches: [main]
    paths: ["backend/**"]
  pull_request:
    paths: ["backend/**"]

jobs:
  test:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: backend

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python 3.11
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"
          cache: "pip"

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Lint with ruff
        run: ruff check .

      - name: Run tests
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
          SUPABASE_URL: ${{ secrets.SUPABASE_URL }}
          SUPABASE_ANON_KEY: ${{ secrets.SUPABASE_ANON_KEY }}
          SUPABASE_SERVICE_ROLE_KEY: ${{ secrets.SUPABASE_SERVICE_ROLE_KEY }}
          DATABASE_URL: ${{ secrets.DATABASE_URL }}
          GITHUB_TOKEN: ${{ secrets.GH_TOKEN }}
          API_SECRET_KEY: test-secret-key
        run: pytest tests/ -v --cov=app --cov-report=term-missing
```

---

## 9. Build Order (Phase by Phase)

Follow this order exactly. Each phase produces a working, testable artifact.

### Phase 1 — Foundation (Day 1–2)
- [ ] Init monorepo, set up `pyproject.toml`, install deps
- [ ] Set up Supabase project, run schema SQL, verify pgvector works
- [ ] FastAPI skeleton: `main.py`, `config.py`, `health.py`
- [ ] Supabase client connection with service role key
- [ ] POST `/api/v1/scans` creates a scan row and returns `scan_id`
- [ ] GET `/api/v1/scans/{id}` returns scan status
- [ ] **Test:** `curl -X POST localhost:8000/api/v1/scans -d '{"repo_url":"..."}'`

### Phase 2 — Scanner + Classifier (Day 3–4)
- [ ] `github_service.py`: fetch repo file tree + file contents via PyGitHub API
- [ ] `scanner_service.py`: run Semgrep (OSS ruleset) + Bandit on fetched code
- [ ] `state.py`: define `SentinelState`
- [ ] Classifier node: gpt-4.1-mini batch classification of raw findings
- [ ] Write findings to Supabase `findings` table
- [ ] **Test:** point at a public GitHub repo with known vulnerabilities, verify findings appear in DB

### Phase 3 — LangGraph State Machine (Day 5–6)
- [ ] `graph.py`: wire all nodes, conditional edges, compile with MemorySaver first
- [ ] Analyzer node: gpt-4o deep analysis (no RAG yet — add dummy context)
- [ ] HITL node + `interrupt_before=["human_review"]` compiles and pauses correctly
- [ ] Reporter node: generates markdown summary
- [ ] Background task: `asyncio.create_task(sentinel_graph.ainvoke(...))` from scan endpoint
- [ ] **Test:** invoke graph manually, verify it pauses at `human_review`

### Phase 4 — RAG + pgvector (Day 7)
- [ ] `embedder.py`: embed code chunks with `text-embedding-3-small`, upsert to `code_embeddings`
- [ ] Seed `vuln_knowledge` table with 20–30 common CWEs (OWASP Top 10)
- [ ] `retriever.py`: pgvector cosine similarity search via raw SQL
- [ ] Wire retriever into analyzer node
- [ ] **Test:** verify RAG returns relevant context for a SQL injection finding

### Phase 5 — SSE Streaming + HITL API (Day 8–9)
- [ ] SSE stream endpoint: polls DB, yields events as `text/event-stream`
- [ ] Approval endpoint: updates DB + resumes LangGraph graph
- [ ] Ticket creator node: writes ticket reference to findings table
- [ ] Notifier node: sends Slack webhook (optional — skip if no webhook)
- [ ] Supabase-backed checkpointer (replace MemorySaver with persistent storage)
- [ ] **Test:** full end-to-end flow — scan → stream events → approve → resume → complete

### Phase 6 — Frontend (Day 10–12)
- [ ] Next.js 15 App Router scaffold with Tailwind + shadcn/ui
- [ ] Landing page: repo URL input, start scan button
- [ ] Dashboard page: scan list with status chips
- [ ] Scan detail page: SSE-powered live feed with `useScanStream` hook
- [ ] Finding cards: severity badge, description, AI analysis, approve/reject buttons
- [ ] Approval panel: submit decisions → POST to `/approve` endpoint
- [ ] Graph status bar: visual node progress (scanner → classifier → analyzer → review → done)
- [ ] Render cold-start handling: "Server warming up..." state
- [ ] **Test:** full UI flow end-to-end

### Phase 7 — LangSmith + CI/CD + Deploy (Day 13–14)
- [ ] Enable LangSmith tracing (set env vars — it's automatic with LangChain)
- [ ] GitHub Actions CI: lint + test on every PR
- [ ] Deploy backend to Render, verify health endpoint
- [ ] Deploy frontend to Vercel, verify CORS + SSE works cross-origin
- [ ] Run one full production scan, verify LangSmith dashboard shows traces
- [ ] Update resume with live link
- [ ] Write `README.md` with architecture diagram, local setup, and demo GIF

---

## 10. Security Best Practices

- **Never log full OpenAI API responses** — they may contain sensitive code
- **Rate limit scan endpoint:** max 5 scans per IP per hour (use a simple in-memory dict or Redis)
- **Validate GitHub URLs:** only allow `github.com` URLs, reject everything else
- **Sanitize repo content before embedding:** strip secrets, tokens, private keys from file content before sending to OpenAI
- **Row Level Security:** enable RLS on all Supabase tables; use service role key only in backend
- **CORS:** explicitly list allowed origins, never use `*` in production
- **Secret scanning:** add `.env` and `*.pem` to `.gitignore` before first commit
- **Input validation:** use Pydantic models on all API inputs, never pass raw user input to shell commands
- **Semgrep sandboxing:** run Semgrep as a subprocess with a timeout (`timeout=60`), never as a shell command with user-controlled arguments
- **API key on frontend:** zero OpenAI or Supabase service-role keys in frontend env vars — all AI calls go through the backend

---

## 11. Cost Estimate (Per Scan)

| Item | Usage | Cost |
|---|---|---|
| gpt-4.1-mini (classifier) | ~2K tokens | ~$0.001 |
| gpt-4o (analyzer, 5 findings) | ~15K tokens | ~$0.04 |
| text-embedding-3-small (50 chunks) | ~25K tokens | ~$0.0005 |
| Supabase storage | ~50KB | Free |
| **Total per scan** | | **~$0.04** |

At this cost, your OpenAI credits will cover thousands of scans for demo purposes.

---

## 12. README Talking Points (For Interviews)

When asked about Sentinel in a technical interview, lead with these:

1. **"The agent uses LangGraph's interrupt mechanism for human-in-the-loop"** — pause state is persisted in Supabase, survives server restarts
2. **"Dual-model routing"** — gpt-4.1-mini for $0.001 classification, gpt-4o only for critical/high findings
3. **"MCP server exposes tools"** — GitHub fetch, ticket creation, Slack notification as standardized MCP tools
4. **"RAG over vulnerability knowledge base"** — pgvector cosine similarity pulls historical CVE context into the analyzer prompt
5. **"LangSmith traces every graph execution"** — can show the interviewer a live trace dashboard
6. **"SSE streams findings token by token"** — interviewer can watch the dashboard update live during the demo

---

*Generated by Claude · Sentinel Project Specification v1.0*
