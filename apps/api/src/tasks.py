"""Celery tasks for incident triage system"""

import logging
from datetime import datetime, timezone
from uuid import UUID
import json
from celery import shared_task, Task
from celery.exceptions import MaxRetriesExceededError, Reject
import psycopg2
from psycopg2.extras import Json
import os

from .config import get_database_config
from .dedup import is_log_duplicate, compute_log_hash, mark_log_hash_seen
from .observability import get_tracer, job_retries_total

logger = logging.getLogger(__name__)
tracer = get_tracer(__name__)

# Database configuration
DB_CONFIG = get_database_config()

# ============================================================================
# Custom Task Class with Dead-Letter Queue Support
# ============================================================================

class CallbackTask(Task):
    """Task with callbacks for error handling"""
    
    autoretry_for = (Exception,)
    retry_kwargs = {'max_retries': 5}
    retry_backoff = True  # Enable exponential backoff
    retry_backoff_max = 600  # Max backoff: 10 minutes
    retry_jitter = True  # Add randomness to prevent thundering herd
    
    def on_retry(self, exc, task_id, args, kwargs, einfo):
        """Called when task is retried"""
        job_retries_total.labels(task_name=self.name).inc()
        logger.warning(
            f"Task {self.name} (id={task_id}) retrying after error: {exc}"
        )
    
    def on_failure(self, exc, task_id, args, kwargs, einfo, **extra_kwargs):
        """Called when task permanently fails (max retries exceeded)"""
        logger.error(
            f"Task {self.name} (id={task_id}) failed permanently: {exc}",
            extra={"task_id": task_id, "task_args": args},
            exc_info=einfo
        )
        
        # Route to dead-letter queue
        handle_dead_letter.delay(
            task_name=self.name,
            task_id=task_id,
            args=args,
            kwargs=kwargs,
            error_message=str(exc),
            error_traceback=str(einfo),
        )


# ============================================================================
# Clustering Task
# ============================================================================

@shared_task(base=CallbackTask, bind=True)
def cluster_logs(
    self,
    log_ids: list[str],
    cluster_id: str | None = None,
    skip_duplicates: bool = True,
) -> dict:
    """
    Cluster a batch of logs together.
    
    Idempotent task that:
    - Deduplicates logs by content hash
    - Groups related logs into clusters
    - Retries with exponential backoff on failure
    - Routes to DLQ on max retries exceeded
    
    Args:
        log_ids: List of log UUIDs to cluster
        cluster_id: Optional existing cluster ID to add logs to
        skip_duplicates: Whether to skip duplicate logs
    
    Returns:
        Dict with clustering results:
        {
            "cluster_id": str,
            "logs_clustered": int,
            "logs_deduplicated": int,
            "timestamp": str
        }
    """
    
    try:
        with tracer.start_as_current_span("celery.cluster_logs"):
            conn = psycopg2.connect(**DB_CONFIG)
            cursor = conn.cursor()
            
            # Fetch logs from database — use ANY(%s) with a typed array to avoid
            # f-string SQL injection and to correctly handle UUID casting.
            from psycopg2.extras import execute_values
            cursor.execute(
                "SELECT id, message, source, severity, timestamp FROM logs"
                " WHERE id = ANY(%s) ORDER BY timestamp DESC",
                (log_ids,),
            )
            
            logs = cursor.fetchall()
            
            if not logs:
                logger.warning(f"No logs found for IDs: {log_ids}")
                return {
                    "cluster_id": cluster_id,
                    "logs_clustered": 0,
                    "logs_deduplicated": 0,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "status": "no_logs_found",
                }
            
            # Deduplication pass
            deduplicated_logs = []
            duplicate_count = 0
            
            for log_id, message, source, severity, timestamp in logs:
                if skip_duplicates and is_log_duplicate(message, source, severity):
                    duplicate_count += 1
                    logger.info(f"Skipping duplicate log: {log_id}")
                    continue
                
                deduplicated_logs.append({
                    "id": log_id,
                    "message": message,
                    "source": source,
                    "severity": severity,
                    "hash": compute_log_hash(message, source, severity),
                })
                
                # Mark as seen
                mark_log_hash_seen(message, source, severity)
            
            if not deduplicated_logs:
                logger.info("All logs were duplicates, no clustering needed")
                return {
                    "cluster_id": cluster_id,
                    "logs_clustered": 0,
                    "logs_deduplicated": duplicate_count,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "status": "all_deduplicated",
                }
            
            # Create or update cluster
            if not cluster_id:
                # Create new cluster
                cursor.execute("""
                    INSERT INTO clusters (name, description, log_count, incident_count)
                    VALUES (%s, %s, %s, %s)
                    RETURNING id
                """, (
                    f"Cluster-{datetime.now(timezone.utc).isoformat()}",
                    f"Auto-clustered {len(deduplicated_logs)} logs",
                    len(deduplicated_logs),
                    0,
                ))
                cluster_id = cursor.fetchone()[0]
                logger.info(f"Created new cluster: {cluster_id}")
            else:
                # Update existing cluster
                cursor.execute("""
                    UPDATE clusters
                    SET log_count = log_count + %s,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                """, (len(deduplicated_logs), cluster_id))
            
            conn.commit()
            
            result = {
                "cluster_id": str(cluster_id),
                "logs_clustered": len(deduplicated_logs),
                "logs_deduplicated": duplicate_count,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "status": "success",
            }
            
            logger.info(f"Clustering completed: {result}")
            return result
        
    except Exception as exc:
        logger.error(f"Clustering task failed: {exc}")
        
        # Retry with exponential backoff
        try:
            raise self.retry(
                exc=exc,
                countdown=2 ** self.request.retries,  # Exponential backoff
                max_retries=5,
            )
        except MaxRetriesExceededError:
            logger.error(f"Max retries exceeded for clustering task")
            raise
    
    finally:
        try:
            cursor.close()
            conn.close()
        except:
            pass


# ============================================================================
# Dead-Letter Queue Handler
# ============================================================================

@shared_task(bind=True)
def handle_dead_letter(
    self,
    task_name: str,
    task_id: str,
    args: dict | list,
    kwargs: dict,
    error_message: str,
    error_traceback: str,
) -> dict:
    """
    Handle tasks that have exceeded max retries.
    
    Records the failed task to a dead-letter queue table for investigation
    and potential manual recovery.
    
    Args:
        task_name: Original task name
        task_id: Original task ID
        args: Original task arguments
        kwargs: Original task keyword arguments
        error_message: Error message from failure
        error_traceback: Full error traceback
    
    Returns:
        Tracking information for the dead-letter record
    """
    
    try:
        with tracer.start_as_current_span("celery.handle_dead_letter"):
            conn = psycopg2.connect(**DB_CONFIG)
            cursor = conn.cursor()
            
            # Check if dead_letter_queue table exists, create if not
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS dead_letter_queue (
                    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                    task_name VARCHAR(255) NOT NULL,
                    task_id VARCHAR(255) NOT NULL UNIQUE,
                    task_args JSONB,
                    task_kwargs JSONB,
                    error_message TEXT,
                    error_traceback TEXT,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    status VARCHAR(50) DEFAULT 'pending'
                )
            """)
            
            # Insert into dead-letter queue
            cursor.execute("""
                INSERT INTO dead_letter_queue 
                (task_name, task_id, task_args, task_kwargs, error_message, error_traceback)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (task_id) DO UPDATE SET
                    status = 'retry_pending',
                    error_message = EXCLUDED.error_message,
                    error_traceback = EXCLUDED.error_traceback
            """, (
                task_name,
                task_id,
                Json(args if isinstance(args, dict) else {"args": args}),
                Json(kwargs),
                error_message,
                error_traceback,
            ))
            
            conn.commit()
            
            dlq_record = {
                "task_id": task_id,
                "task_name": task_name,
                "recorded_at": datetime.now(timezone.utc).isoformat(),
                "status": "recorded_in_dlq",
            }
            
            logger.warning(f"Task recorded in dead-letter queue: {dlq_record}")
            return dlq_record
        
    except Exception as exc:
        logger.error(f"Failed to record in dead-letter queue: {exc}")
        # Don't retry DLQ handler - just log
        return {
            "error": str(exc),
            "task_id": task_id,
            "status": "dlq_handler_failed",
        }
    
    finally:
        try:
            cursor.close()
            conn.close()
        except:
            pass


# ============================================================================
# Utility Tasks
# ============================================================================

@shared_task
def check_clustering_health() -> dict:
    """Health check for clustering tasks"""
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "db_config": {
            "host": DB_CONFIG["host"],
            "database": DB_CONFIG["database"],
            "port": DB_CONFIG["port"],
        },
    }
