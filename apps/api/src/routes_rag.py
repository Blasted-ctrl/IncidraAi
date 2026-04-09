"""
FastAPI endpoints for RAG-powered incident analysis.
"""

from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
import os

from src.rag import IncidentRAG

# Initialize RAG system
rag_system = None


def get_rag_system() -> IncidentRAG:
    """Lazy initialize RAG system."""
    global rag_system
    if rag_system is None:
        rag_system = IncidentRAG(
            embedding_model="all-MiniLM-L6-v2",
            llm_model="claude-3-5-sonnet-20241022",
            persist_dir="./vector_db",
            anthropic_key=os.getenv("ANTHROPIC_API_KEY")
        )
        # Load default runbooks
        _load_default_runbooks()
    return rag_system


def _load_default_runbooks():
    """Load default runbooks into RAG system."""
    runbooks = [
        {
            "id": "runbook-001",
            "title": "Database Connection Troubleshooting",
            "service": "database",
            "tags": ["database", "connection", "troubleshooting"],
            "content": """
Steps to troubleshoot database connection issues:
1. Check database server status: ping database.prod
2. Verify firewall rules allow connections
3. Check connection pool settings
4. Review database logs for errors
5. Test connection with psql: psql -h host -U user -d database
6. If pool exhausted: review long-running queries
7. Consider increasing pool size temporarily
8. Restart database service if necessary
""",
        },
        {
            "id": "runbook-002",
            "title": "API Rate Limiting and Traffic Management",
            "service": "api-gateway",
            "tags": ["api", "rate-limiting", "traffic"],
            "content": """
Steps to handle rate limit issues:
1. Identify rate-limited client IP
2. Check request rate: requests_per_minute = total_requests / time_window
3. Determine if rate limit is appropriate for use case
4. If legitimate high-volume client:
   - Add to whitelist
   - Increase per-client rate limit
   - Consider separate API tier
5. If suspicious (potential DDoS):
   - Check for multiple source IPs
   - Enable geo-blocking if needed
   - Review request patterns
   - Alert security team
6. Monitor with metrics:
   - 429 response rate
   - Top client IPs
   - Request patterns
""",
        },
        {
            "id": "runbook-003",
            "title": "Service Memory Leak Diagnosis",
            "service": "worker-service",
            "tags": ["memory", "debugging", "performance"],
            "content": """
Steps to diagnose and fix memory leaks:
1. Monitor memory growth: memory_gb_now - memory_gb_baseline
2. If growth > 50MB/hour, memory leak likely
3. Collect memory profile:
   - Use py-spy: py-spy record -o profile.svg -- python service.py
   - Use memory_profiler: python -m memory_profiler service.py
4. Analyze profile:
   - Look for unbounded object growth
   - Check for circular references
   - Review cache implementations
5. Common causes:
   - Unbounded caches without TTL
   - Event listeners not unregistered
   - Circular references in data structures
6. Fix recommendations:
   - Implement cache TTL
   - Use weak references where appropriate
   - Add periodic cleanup
7. Deploy fix and monitor
""",
        },
        {
            "id": "runbook-004",
            "title": "Celery Task Queue Backlog Resolution",
            "service": "celery-worker",
            "tags": ["queue", "celery", "performance"],
            "content": """
Steps to resolve Celery task queue backlog:
1. Check queue depth: redis-cli LLEN celery
2. Monitor task processing rate: completed_per_second
3. Calculate estimated time: backlog_size / completion_rate
4. To increase throughput:
   - Increase worker instances: scale -u worker -n 10
   - Increase concurrency per worker: -l 10
   - Optimize task code for speed
   - Consider task prioritization
5. For immediate relief:
   - Add temporary workers
   - Prioritize critical tasks
   - Consider task batching
6. Long-term solutions:
   - Implement task sharding
   - Use task routing to specialized workers
   - Consider multiple queue systems
""",
        },
        {
            "id": "runbook-005",
            "title": "Kubernetes Pod Deployment Troubleshooting",
            "service": "kubernetes",
            "tags": ["kubernetes", "deployment", "containers"],
            "content": """
Steps to troubleshoot pod deployment failures:
1. Check pod status: kubectl get pods -o wide
2. Check events: kubectl describe pod pod-name
3. Check logs: kubectl logs pod-name
4. Common issues and fixes:
   - ImagePullBackOff: verify image exists in registry
   - CrashLoopBackOff: check application logs, config
   - Pending: check resource requests vs available
   - OOMKilled: increase memory limit
5. Resource issues:
   - Check node resource usage: kubectl top nodes
   - Check pod resource requests: kubectl describe pod
   - Add nodes if insufficient resources
6. Configuration issues:
   - Verify ConfigMaps mounted: kubectl get configmap
   - Verify Secrets mounted: kubectl get secret
   - Check environment variables
7. Networking issues:
   - Check service: kubectl get svc
   - Check DNS: nslookup service-name.namespace.svc.cluster.local
""",
        },
    ]
    
    try:
        rag_system = get_rag_system()
        rag_system.ingest_runbooks(runbooks)
    except Exception as e:
        print(f"Warning: Could not load runbooks: {e}")


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class RAGAnalysisRequest(BaseModel):
    """Request for RAG-powered incident analysis."""
    
    incident_summary: str = Field(..., description="Human-readable incident summary")
    logs: List[str] = Field(..., description="Log messages to analyze")
    cluster_info: Optional[Dict[str, Any]] = Field(None, description="Cluster metadata")
    top_k_logs: int = Field(5, ge=1, le=20, description="Number of similar logs to retrieve")
    top_k_runbooks: int = Field(3, ge=1, le=10, description="Number of runbooks to retrieve")


class RetrievedContent(BaseModel):
    """Retrieved content from vector store."""
    
    count: int
    documents: List[str]
    relevance_scores: List[float]


class ReasoningResult(BaseModel):
    """LLM reasoning result."""
    
    success: bool
    warning: Optional[str] = None
    reasoning: Dict[str, Any]
    model: str
    tokens_used: int


class RAGAnalysisResponse(BaseModel):
    """Response from RAG analysis."""
    
    incident_summary: str
    retrieved_logs: RetrievedContent
    retrieved_runbooks: RetrievedContent
    reasoning: ReasoningResult
    analysis_timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


# ============================================================================
# ENDPOINTS
# ============================================================================

router = APIRouter(prefix="/api/rag", tags=["rag"])


@router.post("/analyze", response_model=RAGAnalysisResponse)
async def analyze_incident(request: RAGAnalysisRequest = Body(...)):
    """
    Analyze incident using RAG system.
    
    Retrieves similar logs and relevant runbooks, then uses LLM to reason about the incident.
    """
    try:
        rag = get_rag_system()
        
        result = rag.analyze_incident(
            incident_summary=request.incident_summary,
            logs=request.logs,
            cluster_info=request.cluster_info,
            top_k_logs=request.top_k_logs,
            top_k_runbooks=request.top_k_runbooks
        )
        
        return RAGAnalysisResponse(
            incident_summary=result["incident_summary"],
            retrieved_logs=RetrievedContent(
                count=result["retrieved_logs"]["count"],
                documents=result["retrieved_logs"]["logs"],
                relevance_scores=result["retrieved_logs"]["relevance_scores"]
            ),
            retrieved_runbooks=RetrievedContent(
                count=result["retrieved_runbooks"]["count"],
                documents=result["retrieved_runbooks"]["runbooks"],
                relevance_scores=result["retrieved_runbooks"]["relevance_scores"]
            ),
            reasoning=ReasoningResult(
                success=result["reasoning"]["success"],
                warning=result["reasoning"].get("warning"),
                reasoning=result["reasoning"].get("reasoning", {}),
                model=result["reasoning"]["model"],
                tokens_used=result["reasoning"]["tokens_used"]
            )
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"RAG analysis failed: {str(e)}")


@router.get("/health")
async def rag_health():
    """Health check for RAG system."""
    try:
        rag = get_rag_system()
        return {
            "status": "healthy",
            "rag_initialized": rag is not None,
            "embedding_model": "all-MiniLM-L6-v2",
            "vector_store": "chromadb",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"RAG system unhealthy: {str(e)}")


@router.post("/ingest-runbooks")
async def ingest_runbooks(runbooks: List[Dict[str, Any]] = Body(...)):
    """
    Ingest runbooks into vector store for RAG retrieval.
    
    Expected format:
    {
        "id": "runbook-id",
        "title": "Runbook Title",
        "service": "service-name",
        "tags": ["tag1", "tag2"],
        "content": "Full runbook content"
    }
    """
    try:
        rag = get_rag_system()
        rag.ingest_runbooks(runbooks)
        
        return {
            "status": "success",
            "runbooks_ingested": len(runbooks),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to ingest runbooks: {str(e)}")


@router.get("/runbooks-count")
async def runbooks_count():
    """Get count of ingested runbooks."""
    try:
        rag = get_rag_system()
        count = rag.embedding_store.runbooks_collection.count()
        
        return {
            "runbooks_in_store": count,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get runbook count: {str(e)}")
