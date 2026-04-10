import os
import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from .observability import create_metrics_app, setup_tracing
from .routes_clustering import router as clustering_router
from .routes_rag import router as rag_router
from .routes_logs import router as logs_router
from .routes_incidents import router as incidents_router
from .routes_triage import router as triage_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── Rate limiter (keyed by client IP) ────────────────────────────────────────
limiter = Limiter(key_func=get_remote_address, default_limits=["120/minute"])

# ── CORS origins (configure via env var in production) ───────────────────────
_raw_origins = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:3000,http://127.0.0.1:3000",
)
ALLOWED_ORIGINS = [o.strip() for o in _raw_origins.split(",") if o.strip()]

# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Incidra API",
    version="0.1.0",
    description=(
        "Incidra — AI-powered incident intelligence. "
        "Clusters signals, retrieves runbooks, and delivers root cause "
        "hypotheses via RAG."
    ),
    # Keep docs available — useful for portfolio; exposes no secrets
    docs_url="/docs",
    redoc_url="/redoc",
)

# Attach limiter to app state so route decorators can find it
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["GET", "POST", "PATCH"],
    allow_headers=["Content-Type", "Authorization"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(logs_router)
app.include_router(incidents_router)
app.include_router(triage_router)
app.include_router(clustering_router)
app.include_router(rag_router)
app.mount("/metrics", create_metrics_app())
setup_tracing(app)


# ── Core endpoints ────────────────────────────────────────────────────────────

@app.get("/")
async def root():
    return {
        "service": "Incidra API",
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health")
async def health():
    return {"status": "ok", "service": "incidra-api"}


@app.get("/about")
async def about():
    return {
        "name": "Incidra API",
        "version": "0.1.0",
        "features": [
            "RAG-powered incident reasoning with LLM",
            "Vector embeddings for log similarity",
            "Runbook retrieval and context augmentation",
            "Log clustering with deduplication",
            "Background job processing with Celery",
            "Redis caching and deduplication",
            "Dead-letter queue for failed tasks",
        ],
        "endpoints": {
            "logs": "/logs",
            "incidents": "/incidents",
            "triage": "/triage",
            "clustering": "/api/clustering",
            "rag": "/api/rag",
            "docs": "/docs",
            "health": "/health",
        },
    }
