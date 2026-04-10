# Incidra

**AI-powered incident intelligence.** Incidra clusters noisy signals, retrieves the right runbooks, and delivers a root cause brief in under 3 seconds — so on-call engineers spend less time triaging and more time resolving.

![Next.js](https://img.shields.io/badge/Next.js_14-black?style=flat&logo=next.js)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat&logo=fastapi&logoColor=white)
![Python](https://img.shields.io/badge/Python_3.12-3776AB?style=flat&logo=python&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL_16-4169E1?style=flat&logo=postgresql&logoColor=white)
![Redis](https://img.shields.io/badge/Redis_7-DC382D?style=flat&logo=redis&logoColor=white)
![Celery](https://img.shields.io/badge/Celery-37814A?style=flat&logo=celery&logoColor=white)
![ChromaDB](https://img.shields.io/badge/ChromaDB-vector_store-orange?style=flat)
![Claude](https://img.shields.io/badge/Claude_API-Anthropic-blueviolet?style=flat)

---

## The Problem

On-call engineers waste hours triaging noisy alerts. By the time root cause is identified, the incident has compounded. Runbooks exist but aren't surfaced at the right moment. Past incidents repeat because no institutional memory is built.

## What Incidra Does

1. **Embeds** incoming log lines into 384-dim vectors (`all-MiniLM-L6-v2`)
2. **Retrieves** semantically similar past logs and relevant runbooks from ChromaDB
3. **Reasons** over the retrieved context with Claude to produce a structured brief
4. **Learns** — feedback on triage results is stored and used in future evaluations

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Incidra Dashboard                        │
│               Next.js 14 · Tailwind · Dark UI                   │
└─────────────────────┬───────────────────────────────────────────┘
                      │ HTTP + CORS
┌─────────────────────▼───────────────────────────────────────────┐
│                     Incidra API  (FastAPI)                       │
│                                                                  │
│  POST /api/rag/analyze          POST /logs   POST /triage        │
│  GET  /api/rag/health           GET  /incidents                  │
│  POST /api/clustering/cluster-logs                               │
│  GET  /metrics  (Prometheus)                                     │
└──────┬──────────────────┬───────────────────────────────────────┘
       │                  │
┌──────▼──────┐    ┌──────▼──────────────────────────────────────┐
│  PostgreSQL  │    │              RAG Pipeline                    │
│             │    │                                              │
│  logs        │    │  EmbeddingStore  (ChromaDB)                  │
│  incidents   │    │  ├─ incident_logs  collection               │
│  clusters    │    │  └─ runbooks       collection               │
│  triage      │    │                                              │
│  feedback    │    │  IncidentReasoner  (Claude API)              │
│  dead_letter │    │  └─ model fallback chain                     │
└─────────────┘    └──────────────────────────────────────────────┘
       │
┌──────▼──────────────────────────────────────────────────────────┐
│                       Celery + Redis                             │
│                                                                  │
│  clustering queue → SHA-256 dedup → cluster upsert              │
│  dead_letter queue → failed tasks persisted for recovery        │
│  exponential backoff  (2^n seconds · max 5 retries · jitter)    │
└──────────────────────────────────────────────────────────────────┘
```

---

## How the RAG Pipeline Works

```
User submits: incident summary + raw log lines
        │
        ▼
1. Each log line is embedded  →  384-dim vector (MiniLM)
2. ChromaDB cosine search     →  top-K similar past logs
3. ChromaDB cosine search     →  top-K relevant runbooks
4. Claude receives: summary + retrieved logs + retrieved runbooks
5. Claude returns JSON:
     root_cause · severity · affected_services
     actions · metrics · escalation
        │
        ▼
Structured triage brief  ·  rendered in Incidra dashboard  ·  <3s
```

Five runbooks are indexed at startup (database connections, API rate limiting, memory leaks, Celery queues, Kubernetes deployments). Custom runbooks can be ingested via `POST /api/rag/ingest-runbooks`.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 14, React 18, Tailwind CSS, Geist font |
| Backend | FastAPI, Python 3.12, Uvicorn |
| AI / LLM | Anthropic Claude API (`claude-sonnet-4-0`) |
| Embeddings | `sentence-transformers` (`all-MiniLM-L6-v2`) |
| Vector Store | ChromaDB (cosine similarity, persistent) |
| Database | PostgreSQL 16 |
| Queue | Celery 5 + Redis 7 |
| Observability | Prometheus metrics, OpenTelemetry tracing, Grafana dashboard |
| Monorepo | Turborepo + pnpm, shared TypeScript types + typed API client |

---

## Running Locally

**Prerequisites:** Python 3.12+, Node 20+, an [Anthropic API key](https://console.anthropic.com)

**Terminal 1 — API:**
```bash
cd apps/api
pip install ".[rag]"
export ANTHROPIC_API_KEY=sk-ant-...
uvicorn src.main:app --reload --port 8000
```

**Terminal 2 — Frontend:**
```bash
cd apps/web
npm install
npm run dev
```

Open `http://localhost:3000` · API docs at `http://localhost:8000/docs`

---

## Running with Docker (full stack)

```bash
# 1. Set environment variables
cp .env.example .env
# Edit .env — add ANTHROPIC_API_KEY and DB_PASSWORD

# 2. Start all services
docker compose up --build

# 3. Apply the database migration (first run only)
docker compose exec postgres psql -U postgres -d incident_triage \
  -f /dev/stdin < apps/api/migrations/001_initial_schema.sql
```

Services: PostgreSQL · Redis · Incidra API · Celery worker · Celery beat · Next.js

---

## API Reference

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/rag/analyze` | Run RAG triage — retrieve context + reason with Claude |
| `GET` | `/api/rag/health` | RAG system health and model status |
| `POST` | `/api/rag/ingest-runbooks` | Add custom runbooks to the vector store |
| `POST` | `/logs` | Ingest a single log entry |
| `POST` | `/logs/batch` | Ingest up to 1,000 logs at once |
| `GET` | `/logs` | List logs with filtering and pagination |
| `POST` | `/incidents` | Create an incident |
| `PATCH` | `/incidents/{id}` | Update incident status or assignee |
| `POST` | `/triage` | Full triage — fetch logs → run RAG → persist result |
| `POST` | `/triage/{id}/feedback` | Submit correctness feedback for evaluation |
| `POST` | `/api/clustering/cluster-logs` | Async log clustering job via Celery |
| `GET` | `/api/clustering/dead-letter-queue` | Inspect failed tasks |
| `GET` | `/metrics` | Prometheus metrics endpoint |

---

## Reliability

- **Idempotent ingestion** — SHA-256 content hash deduplication via Redis (24h TTL)
- **Retry with backoff** — Celery tasks retry up to 5× (`2^n` seconds, max 600s, with jitter)
- **Dead-letter queue** — tasks exceeding max retries are persisted to PostgreSQL for replay
- **Model fallback chain** — if the primary Claude model is unavailable, Incidra walks a prioritized list of fallback models automatically

---

## Observability

- **Prometheus** at `/metrics` — ingestion latency histogram, triage latency histogram, retry counter
- **OpenTelemetry** tracing on all routes and Celery tasks (set `OTEL_EXPORTER_OTLP_ENDPOINT`)
- **Grafana** dashboard at `observability/grafana/dashboards/` — p50/p95 latency + retry rate

---

## Project Structure

```
incidra/
├── apps/
│   ├── api/                      # FastAPI backend
│   │   ├── src/
│   │   │   ├── main.py           # App entry point + router wiring
│   │   │   ├── rag.py            # EmbeddingStore + IncidentReasoner + RAG pipeline
│   │   │   ├── tasks.py          # Celery tasks (clustering, dead-letter handler)
│   │   │   ├── dedup.py          # SHA-256 log deduplication via Redis
│   │   │   ├── observability.py  # Prometheus metrics + OpenTelemetry
│   │   │   ├── routes_logs.py
│   │   │   ├── routes_incidents.py
│   │   │   ├── routes_triage.py
│   │   │   ├── routes_clustering.py
│   │   │   └── routes_rag.py
│   │   ├── migrations/           # PostgreSQL schema
│   │   └── test/                 # pytest suite + Locust load tests
│   └── web/                      # Next.js dashboard
│       └── src/app/page.tsx      # Incidra triage UI
├── packages/
│   ├── shared/                   # Shared TypeScript types + typed API client
│   └── ui/                       # Shared React component library
├── observability/
│   └── grafana/dashboards/
└── docker-compose.yml
```
