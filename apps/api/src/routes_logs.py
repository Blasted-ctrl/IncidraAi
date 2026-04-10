"""API endpoints for log ingestion and retrieval."""

from fastapi import APIRouter, HTTPException, Query, Request
from typing import Optional
from datetime import datetime, timezone
import logging
import psycopg2
from psycopg2.extras import RealDictCursor, Json
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

from .config import get_database_config
from .types_api import Log, LogDetail, LogList, CreateLogRequest, LogSeverity
from .observability import get_tracer, ingestion_latency_seconds, track_latency

logger = logging.getLogger(__name__)
tracer = get_tracer(__name__)

router = APIRouter(prefix="/logs", tags=["logs"])


def _get_conn():
    return psycopg2.connect(**get_database_config())


# ============================================================================
# Endpoints
# ============================================================================

@router.get("", response_model=LogList)
async def list_logs(
    severity: Optional[str] = Query(None, description="Filter by severity"),
    source: Optional[str] = Query(None, description="Filter by source"),
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0),
):
    """List logs with optional filtering and pagination."""
    try:
        conn = _get_conn()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        conditions = []
        params: list = []

        if severity:
            conditions.append("severity = %s::log_severity")
            params.append(severity.upper())
        if source:
            conditions.append("source = %s")
            params.append(source)

        where = ("WHERE " + " AND ".join(conditions)) if conditions else ""

        cursor.execute(
            f"SELECT COUNT(*) FROM logs {where}", params
        )
        total = cursor.fetchone()["count"]

        cursor.execute(
            f"SELECT id, message, severity, timestamp, source, trace_id, span_id, metadata"
            f" FROM logs {where} ORDER BY timestamp DESC LIMIT %s OFFSET %s",
            params + [limit, offset],
        )
        rows = cursor.fetchall()
        cursor.close()
        conn.close()

        items = [
            Log(
                id=r["id"],
                message=r["message"],
                severity=r["severity"],
                timestamp=r["timestamp"],
                source=r["source"],
                trace_id=r["trace_id"],
                span_id=r["span_id"],
                metadata=r["metadata"],
            )
            for r in rows
        ]
        return LogList(items=items, total=total, limit=limit, offset=offset)

    except Exception as exc:
        logger.error(f"Failed to list logs: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("", response_model=Log, status_code=201)
async def create_log(request: CreateLogRequest):
    """Ingest a single log entry."""
    try:
        with tracer.start_as_current_span("create_log"):
            with track_latency(ingestion_latency_seconds, "/logs"):
                conn = _get_conn()
                cursor = conn.cursor(cursor_factory=RealDictCursor)

                cursor.execute(
                    """
                    INSERT INTO logs (message, severity, source, trace_id, span_id, metadata)
                    VALUES (%s, %s::log_severity, %s, %s, %s, %s)
                    RETURNING id, message, severity, timestamp, source, trace_id, span_id, metadata
                    """,
                    (
                        request.message,
                        request.severity.value if hasattr(request.severity, "value") else request.severity,
                        request.source,
                        str(request.trace_id) if request.trace_id else None,
                        str(request.span_id) if request.span_id else None,
                        Json(request.metadata) if request.metadata else None,
                    ),
                )
                row = cursor.fetchone()
                conn.commit()
                cursor.close()
                conn.close()

                return Log(
                    id=row["id"],
                    message=row["message"],
                    severity=row["severity"],
                    timestamp=row["timestamp"],
                    source=row["source"],
                    trace_id=row["trace_id"],
                    span_id=row["span_id"],
                    metadata=row["metadata"],
                )

    except Exception as exc:
        logger.error(f"Failed to create log: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/batch", response_model=list[Log], status_code=201)
@limiter.limit("20/minute")
async def create_logs_batch(http_request: Request, requests: list[CreateLogRequest]):
    """Ingest a batch of log entries (idempotent by message+source+severity hash)."""
    if not requests:
        raise HTTPException(status_code=400, detail="Batch cannot be empty")
    if len(requests) > 1000:
        raise HTTPException(status_code=400, detail="Batch size limit is 1000 per request")

    try:
        with tracer.start_as_current_span("create_logs_batch"):
            with track_latency(ingestion_latency_seconds, "/logs/batch"):
                conn = _get_conn()
                cursor = conn.cursor(cursor_factory=RealDictCursor)

                results = []
                for req in requests:
                    cursor.execute(
                        """
                        INSERT INTO logs (message, severity, source, trace_id, span_id, metadata)
                        VALUES (%s, %s::log_severity, %s, %s, %s, %s)
                        RETURNING id, message, severity, timestamp, source, trace_id, span_id, metadata
                        """,
                        (
                            req.message,
                            req.severity.value if hasattr(req.severity, "value") else req.severity,
                            req.source,
                            str(req.trace_id) if req.trace_id else None,
                            str(req.span_id) if req.span_id else None,
                            Json(req.metadata) if req.metadata else None,
                        ),
                    )
                    row = cursor.fetchone()
                    results.append(
                        Log(
                            id=row["id"],
                            message=row["message"],
                            severity=row["severity"],
                            timestamp=row["timestamp"],
                            source=row["source"],
                            trace_id=row["trace_id"],
                            span_id=row["span_id"],
                            metadata=row["metadata"],
                        )
                    )

                conn.commit()
                cursor.close()
                conn.close()
                return results

    except Exception as exc:
        logger.error(f"Failed to create log batch: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/{log_id}", response_model=LogDetail)
async def get_log(log_id: str):
    """Get a specific log entry by ID."""
    try:
        conn = _get_conn()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        cursor.execute(
            "SELECT id, message, severity, timestamp, source, trace_id, span_id, metadata"
            " FROM logs WHERE id = %s",
            (log_id,),
        )
        row = cursor.fetchone()
        cursor.close()
        conn.close()

        if not row:
            raise HTTPException(status_code=404, detail=f"Log {log_id} not found")

        return LogDetail(
            id=row["id"],
            message=row["message"],
            severity=row["severity"],
            timestamp=row["timestamp"],
            source=row["source"],
            trace_id=row["trace_id"],
            span_id=row["span_id"],
            metadata=row["metadata"],
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Failed to get log {log_id}: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))
