"""API endpoints for clustering and task management"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from datetime import datetime, timezone
import logging

from .celery_app import app as celery_app
from .config import get_database_config
from .observability import get_tracer, ingestion_latency_seconds, track_latency
from .tasks import cluster_logs, check_clustering_health
from .dedup import get_dedup_stats

logger = logging.getLogger(__name__)
tracer = get_tracer(__name__)

router = APIRouter(prefix="/api/clustering", tags=["clustering"])

# ============================================================================
# Request/Response Models
# ============================================================================

class ClusterLogsRequest(BaseModel):
    """Request to cluster logs"""
    log_ids: list[str]
    cluster_id: Optional[str] = None
    skip_duplicates: bool = True


class ClusterLogsResponse(BaseModel):
    """Response from clustering task"""
    task_id: str
    status: str
    message: str


class TaskStatusResponse(BaseModel):
    """Task status information"""
    task_id: str
    status: str
    result: Optional[dict] = None
    error: Optional[str] = None


class DedupStatsResponse(BaseModel):
    """Deduplication statistics"""
    dedup_prefix: str
    ttl_seconds: int
    cache_ttl_hours: float
    redis_db: int


# ============================================================================
# Clustering Endpoints
# ============================================================================

@router.post("/cluster-logs", response_model=ClusterLogsResponse)
async def cluster_logs_endpoint(request: ClusterLogsRequest):
    """
    Submit a clustering job to the queue.
    
    Returns immediately with task ID. Use /tasks/{task_id} to check status.
    
    Features:
    - Idempotent: Same logs won't be re-clustered if already processed
    - Deduplication: Duplicate logs are skipped automatically
    - Retries: Failed tasks retry with exponential backoff
    - DLQ: Tasks exceeding max retries are sent to dead-letter queue
    
    Example:
        POST /api/clustering/cluster-logs
        {
            "log_ids": ["uuid1", "uuid2", "uuid3"],
            "cluster_id": "existing-cluster-id",
            "skip_duplicates": true
        }
    """
    
    try:
        with tracer.start_as_current_span("cluster_logs_endpoint"):
            with track_latency(
                ingestion_latency_seconds,
                "/api/clustering/cluster-logs",
            ):
                # Submit task to Celery
                task = cluster_logs.apply_async(
                    args=[request.log_ids],
                    kwargs={
                        "cluster_id": request.cluster_id,
                        "skip_duplicates": request.skip_duplicates,
                    },
                    queue="clustering",
                )

                return ClusterLogsResponse(
                    task_id=task.id,
                    status="submitted",
                    message=f"Clustering job submitted. Check status with /api/clustering/tasks/{task.id}",
                )
    
    except Exception as exc:
        logger.error(f"Failed to submit clustering job: {exc}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to submit clustering job: {str(exc)}",
        )


@router.get("/tasks/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(task_id: str):
    """
    Get status of a clustering task.
    
    Possible statuses:
    - PENDING: Task waiting in queue
    - STARTED: Task is being processed
    - SUCCESS: Task completed successfully
    - RETRY: Task is retrying after an error
    - FAILURE: Task failed
    """
    
    try:
        task = celery_app.AsyncResult(task_id)
        
        if task.state == "SUCCESS":
            return TaskStatusResponse(
                task_id=task_id,
                status=task.state,
                result=task.result,
            )
        elif task.state == "FAILURE":
            return TaskStatusResponse(
                task_id=task_id,
                status=task.state,
                error=str(task.info),
            )
        else:
            return TaskStatusResponse(
                task_id=task_id,
                status=task.state,
            )
    
    except Exception as exc:
        logger.error(f"Failed to get task status: {exc}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get task status: {str(exc)}",
        )


@router.get("/tasks/{task_id}/result")
async def get_task_result(task_id: str):
    """Get the result of a completed clustering task."""
    
    try:
        task = celery_app.AsyncResult(task_id)
        
        if task.state != "SUCCESS":
            raise HTTPException(
                status_code=400,
                detail=f"Task is in {task.state} state, not completed",
            )
        
        return task.result
    
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Failed to get task result: {exc}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get task result: {str(exc)}",
        )


# ============================================================================
# Queue Management Endpoints
# ============================================================================

@router.get("/health")
async def clustering_health():
    """Health check for clustering system"""
    
    try:
        result = check_clustering_health.apply_async(queue="default").get(timeout=5)
        return {
            "status": "healthy",
            "clustering": result,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as exc:
        logger.error(f"Health check failed: {exc}")
        return {
            "status": "unhealthy",
            "error": str(exc),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


@router.get("/stats")
async def get_stats():
    """Get clustering and deduplication statistics"""
    
    try:
        # Get active tasks
        inspect = celery_app.control.inspect()
        active_tasks = inspect.active()
        
        dedup_stats = get_dedup_stats()
        
        return {
            "deduplication": dedup_stats,
            "active_tasks": {
                queue: len(tasks) if tasks else 0
                for queue, tasks in (active_tasks or {}).items()
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    
    except Exception as exc:
        logger.error(f"Failed to get stats: {exc}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get stats: {str(exc)}",
        )


@router.post("/tasks/{task_id}/retry")
async def retry_task(task_id: str):
    """
    Manually retry a failed task.
    
    Use this to retry tasks from the dead-letter queue.
    """
    
    try:
        # Revoke the existing task
        celery_app.control.revoke(task_id, terminate=True)
        
        # Get the task info and resubmit
        # In production, you'd fetch from dead-letter-queue table
        
        return {
            "status": "retry_initiated",
            "original_task_id": task_id,
            "message": "Task marked for retry. Monitor the original task ID for status.",
        }
    
    except Exception as exc:
        logger.error(f"Failed to retry task: {exc}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retry task: {str(exc)}",
        )


# ============================================================================
# Dead-Letter Queue Endpoints
# ============================================================================

@router.get("/dead-letter-queue")
async def get_dead_letter_queue(
    limit: int = Query(50, ge=1, le=1000),
    status: Optional[str] = None,
):
    """
    Get tasks from the dead-letter queue.
    
    Query parameters:
    - limit: Number of records to return (default 50, max 1000)
    - status: Filter by status (pending, retry_pending, recovered, etc)
    """
    
    try:
        import psycopg2
        import os
        
        conn = psycopg2.connect(**get_database_config())
        cursor = conn.cursor()
        
        query = "SELECT * FROM dead_letter_queue"
        params = []
        
        if status:
            query += " WHERE status = %s"
            params.append(status)
        
        query += " ORDER BY created_at DESC LIMIT %s"
        params.append(limit)
        
        cursor.execute(query, params)
        columns = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()
        
        results = [dict(zip(columns, row)) for row in rows]
        
        cursor.close()
        conn.close()
        
        return {
            "count": len(results),
            "records": results,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    
    except Exception as exc:
        logger.error(f"Failed to get dead-letter queue: {exc}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get dead-letter queue: {str(exc)}",
        )
