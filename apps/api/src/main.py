from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from .routes_clustering import router as clustering_router
from .routes_rag import router as rag_router

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Incident Triage API",
    version="0.1.0",
    description="API for incident triage with clustering and AI analysis",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "localhost"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(clustering_router)
app.include_router(rag_router)


@app.get("/")
async def root():
    """API root endpoint"""
    return {
        "service": "Incident Triage API",
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "ok",
        "service": "incident-triage-api",
    }


@app.get("/about")
async def about():
    """About the API"""
    return {
        "name": "Incident Triage API",
        "version": "0.1.0",
        "features": [
            "Log clustering with deduplication",
            "Incident triage with AI analysis",
            "RAG-powered incident reasoning with LLM",
            "Vector embeddings for log similarity",
            "Runbook retrieval and context augmentation",
            "Background job processing with Celery",
            "Redis caching and deduplication",
            "Dead-letter queue for failed tasks",
        ],
        "endpoints": {
            "clustering": "/api/clustering",
            "rag": "/api/rag",
            "docs": "/docs",
            "health": "/health",
        },
    }