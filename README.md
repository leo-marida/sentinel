# Sentinel — AI-Native DevSecOps Copilot

Sentinel is a production-grade, multi-agent DevSecOps copilot. Paste a GitHub repo URL and it scans the code for security vulnerabilities, triages findings through a **LangGraph** state machine, routes them through a **human-in-the-loop approval** step, and streams a remediation report live to a **Next.js** dashboard.

**Live demo flow:** paste a repo URL → Sentinel scans it with Semgrep + Bandit → findings stream in over SSE in real time → an LLM analyst explains root cause + remediation for each finding → you approve/reject each one → the graph resumes, creates tickets, and produces a final report.

**🔗 Live app:** [sentinel-pied-ten.vercel.app](https://sentinel-pied-ten.vercel.app)
**🔗 Backend API:** [sentinel-backend-txyj.onrender.com](https://sentinel-backend-txyj.onrender.com) ([`/health`](https://sentinel-backend-txyj.onrender.com/health))

> Backend is on Render's free tier and spins down after 15 min idle — the first request may take ~30s to cold-start.

---

## Architecture

```
┌─────────────┐        POST /scans         ┌──────────────────────────────────┐
│  Next.js UI │ ─────────────────────────▶ │            FastAPI               │
│ (Vercel)    │                            │           (Render)               │
│             │ ◀───── SSE stream ──────── │                                  │
└─────────────┘   GET /scans/{id}/stream   │   ┌────────────────────────┐     │
       ▲                                   │   │   LangGraph state machine     │
       │            POST /approve          │   │                          │     │
       └──────────────────────────────────▶│   │  scanner → classifier   │     │
                                            │   │     ↓         (gpt-4.1-mini)  │
                                            │   │  analyzer (gpt-4o + RAG)│     │
                                            │   │     ↓                   │     │
                                            │   │  human_review ⏸ (HITL) │     │
                                            │   │     ↓ resumes on /approve│    │
                                            │   │  ticket_creator → notifier│   │
                                            │   │     ↓                   │     │
                                            │   │  reporter (streams md) │     │
                                            │   └────────────────────────┘     │
                                            │            │         │           │
                                            │     Semgrep/Bandit   │           │
                                            │      (subprocess)    │           │
                                            │                      ▼           │
                                            │            ┌──────────────────┐  │
                                            │            │ Supabase Postgres│  │
                                            │            │   + pgvector     │  │
                                            │            │ (scans, findings,│  │
                                            │            │  checkpoints,    │  │
                                            │            │  vuln_knowledge) │  │
                                            │            └──────────────────┘  │
                                            └──────────────────────────────────┘
```

The LangGraph checkpoint is persisted in Supabase, so the `human_review` interrupt survives a server restart — the graph resumes from the exact node it paused at once a decision is submitted.

---

## Tech Stack

| Layer | Tools |
|---|---|
| Orchestration | LangGraph, LangChain, LangSmith tracing |
| LLMs | `gpt-4.1-mini` (classification), `gpt-4o` (deep analysis + report) |
| RAG | OpenAI `text-embedding-3-small` + pgvector cosine similarity |
| Scanning | Semgrep (OSS ruleset), Bandit |
| Backend | FastAPI, Python 3.11, Supabase (Postgres + pgvector), MCP server |
| Frontend | Next.js 16 (App Router), TypeScript, Tailwind CSS v4, shadcn/ui |
| Streaming | Server-Sent Events (SSE), native `EventSource` |
| Infra | Docker + docker-compose (local), Render (backend), Vercel (frontend), GitHub Actions (CI) |

---

## Running locally

### Option A — Docker (backend + Postgres/pgvector)

```bash
cp .env.example backend/.env   # fill in OPENAI_API_KEY, SUPABASE_*, etc.
docker compose up --build
```

This brings up:
- `postgres` — `pgvector/pgvector:pg16` on `5432`
- `backend` — FastAPI on `8000`

Then run the frontend separately (Docker Compose only covers the backend + DB, per the project spec):

```bash
cd frontend
cp .env.local.example .env.local   # NEXT_PUBLIC_API_URL=http://localhost:8000
npm install
npm run dev
```

### Option B — Manual (no Docker)

```bash
# backend
cd backend
cp .env.example .env
python -m venv .venv && .venv/Scripts/activate   # or source .venv/bin/activate on macOS/Linux
pip install -r requirements.txt
uvicorn app.main:app --reload

# frontend (separate terminal)
cd frontend
cp .env.local.example .env.local
npm install
npm run dev
```

Open `http://localhost:3000`, paste a public GitHub repo URL (e.g. `https://github.com/we45/Vulnerable-Flask-App`), and watch the scan stream in live.

---

## Testing

```bash
# backend
cd backend
ruff check .
pytest tests/ -v --cov=app --cov-report=term-missing

# frontend
cd frontend
npm run lint
npx tsc --noEmit
npm run build
```

Both are wired into GitHub Actions (`.github/workflows/backend-ci.yml`, `frontend-ci.yml`) and run on every push/PR touching their respective directories.

---

## Deployment

| Service | Hosts | Live URL | Notes |
|---|---|---|---|
| [Render](https://render.com) | FastAPI backend | [sentinel-backend-txyj.onrender.com](https://sentinel-backend-txyj.onrender.com) | Free tier spins down after 15 min idle — first request after that takes ~30s to cold-start. Auto-deploys on push to `main` via `render.yaml` blueprint |
| [Vercel](https://vercel.com) | Next.js frontend | [sentinel-pied-ten.vercel.app](https://sentinel-pied-ten.vercel.app) | `NEXT_PUBLIC_API_URL` points at the Render backend URL |
| [Supabase](https://supabase.com) | Postgres + pgvector | — | Free tier pauses after 7 days idle, unpauses ~20s after first request |

See `SENTINEL.md` §8 for exact dashboard setup steps.

---

## What this project demonstrates

| Claim | Where it's proved |
|---|---|
| LangGraph HITL orchestration | `agent/graph.py` — `interrupt_before=["human_review"]`, resumed via `POST /scans/{id}/approve`, checkpoint persisted in Supabase so it survives restarts |
| Dual-model LLM routing | `gpt-4.1-mini` for triage classification, `gpt-4o` reserved for analyzer + report generation |
| MCP tool integrations | `mcp/server.py` exposes GitHub fetch, ticket creation, and Slack notification as MCP tools |
| RAG over a vector store | `rag/embedder.py` + `rag/retriever.py` — pgvector cosine similarity over a seeded vulnerability knowledge base, injected into the analyzer prompt |
| Real-time streaming UI | SSE endpoint (`api/routes/stream.py`) consumed by `hooks/use-scan-stream.ts`, rendered live in `AgentTimeline`/`StreamViewer` |
| Production patterns | Async FastAPI throughout, Docker, CI on every PR, structured error handling, Render cold-start UX, full audit trail in Postgres |

---

## Talking points (for interviews)

1. **LangGraph's interrupt mechanism powers human-in-the-loop** — the pause state is persisted in Supabase, so it survives a server restart and resumes from the exact node.
2. **Dual-model routing** — `gpt-4.1-mini` for $0.001 classification, `gpt-4o` reserved for findings that actually need deep analysis.
3. **MCP server exposes tools** — GitHub fetch, ticket creation, and Slack notification as standardized MCP tools, not ad-hoc function calls.
4. **RAG over a vulnerability knowledge base** — pgvector cosine similarity pulls historical CVE context into the analyzer prompt instead of relying on the model's training data alone.
5. **LangSmith traces every graph execution** — can pull up a live trace during a demo.
6. **SSE streams findings as they're discovered** — the dashboard updates live while the scan is still running, not just on completion.

---

*Spec: `SENTINEL.md`*
