"""API endpoints for incident management."""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from datetime import datetime, timezone
import logging
import psycopg2
from psycopg2.extras import RealDictCursor

from .config import get_database_config
from .types_api import (
    Incident,
    IncidentDetail,
    IncidentList,
    CreateIncidentRequest,
    UpdateIncidentRequest,
    IncidentStatus,
    IncidentSeverity,
)
from .observability import get_tracer

logger = logging.getLogger(__name__)
tracer = get_tracer(__name__)

router = APIRouter(prefix="/incidents", tags=["incidents"])


def _get_conn():
    return psycopg2.connect(**get_database_config())


def _row_to_incident(r) -> Incident:
    return Incident(
        id=r["id"],
        title=r["title"],
        description=r["description"],
        status=r["status"],
        severity=r["severity"],
        created_at=r["created_at"],
        updated_at=r["updated_at"],
        resolved_at=r["resolved_at"],
        assigned_to=r["assigned_to"],
        cluster_ids=r["cluster_ids"] or [],
    )


# ============================================================================
# Endpoints
# ============================================================================

@router.get("", response_model=IncidentList)
async def list_incidents(
    status: Optional[str] = Query(None, description="Filter by status"),
    severity: Optional[str] = Query(None, description="Filter by severity"),
    assigned_to: Optional[str] = Query(None, description="Filter by assignee"),
    sort_by: str = Query("created_at", description="Sort field"),
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0),
):
    """List incidents with optional filtering, sorting, and pagination."""
    try:
        conn = _get_conn()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        conditions = []
        params: list = []

        if status:
            conditions.append("status = %s::incident_status")
            params.append(status.upper())
        if severity:
            conditions.append("severity = %s::incident_severity")
            params.append(severity.upper())
        if assigned_to:
            conditions.append("assigned_to = %s")
            params.append(assigned_to)

        where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
        allowed_sort = {"created_at", "updated_at", "severity"}
        order_col = sort_by if sort_by in allowed_sort else "created_at"

        cursor.execute(f"SELECT COUNT(*) FROM incidents {where}", params)
        total = cursor.fetchone()["count"]

        cursor.execute(
            f"SELECT id, title, description, status, severity, created_at, updated_at,"
            f" resolved_at, assigned_to, cluster_ids"
            f" FROM incidents {where} ORDER BY {order_col} DESC LIMIT %s OFFSET %s",
            params + [limit, offset],
        )
        rows = cursor.fetchall()
        cursor.close()
        conn.close()

        return IncidentList(
            items=[_row_to_incident(r) for r in rows],
            total=total,
            limit=limit,
            offset=offset,
        )

    except Exception as exc:
        logger.error(f"Failed to list incidents: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("", response_model=Incident, status_code=201)
async def create_incident(request: CreateIncidentRequest):
    """Create a new incident."""
    try:
        with tracer.start_as_current_span("create_incident"):
            conn = _get_conn()
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            severity_val = (
                request.severity.value
                if hasattr(request.severity, "value")
                else request.severity
            )
            cluster_ids = [str(c) for c in (request.cluster_ids or [])]

            cursor.execute(
                """
                INSERT INTO incidents (title, description, severity, cluster_ids)
                VALUES (%s, %s, %s::incident_severity, %s)
                RETURNING id, title, description, status, severity, created_at,
                          updated_at, resolved_at, assigned_to, cluster_ids
                """,
                (request.title, request.description, severity_val, cluster_ids),
            )
            row = cursor.fetchone()
            conn.commit()
            cursor.close()
            conn.close()
            return _row_to_incident(row)

    except Exception as exc:
        logger.error(f"Failed to create incident: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/{incident_id}", response_model=IncidentDetail)
async def get_incident(incident_id: str):
    """Get a specific incident with related logs and triage results."""
    try:
        conn = _get_conn()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        cursor.execute(
            "SELECT id, title, description, status, severity, created_at, updated_at,"
            " resolved_at, assigned_to, cluster_ids"
            " FROM incidents WHERE id = %s",
            (incident_id,),
        )
        row = cursor.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail=f"Incident {incident_id} not found")

        cursor.close()
        conn.close()

        incident = _row_to_incident(row)
        return IncidentDetail(**incident.model_dump())

    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Failed to get incident {incident_id}: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))


@router.patch("/{incident_id}", response_model=Incident)
async def update_incident(incident_id: str, request: UpdateIncidentRequest):
    """Update an existing incident (partial update)."""
    try:
        with tracer.start_as_current_span("update_incident"):
            conn = _get_conn()
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            # Verify incident exists
            cursor.execute("SELECT id FROM incidents WHERE id = %s", (incident_id,))
            if not cursor.fetchone():
                raise HTTPException(status_code=404, detail=f"Incident {incident_id} not found")

            # Build partial update
            fields = []
            params: list = []

            if request.title is not None:
                fields.append("title = %s")
                params.append(request.title)
            if request.description is not None:
                fields.append("description = %s")
                params.append(request.description)
            if request.status is not None:
                fields.append("status = %s::incident_status")
                status_val = request.status.value if hasattr(request.status, "value") else request.status
                params.append(status_val)
                if status_val == "RESOLVED":
                    fields.append("resolved_at = CURRENT_TIMESTAMP")
            if request.severity is not None:
                fields.append("severity = %s::incident_severity")
                params.append(
                    request.severity.value if hasattr(request.severity, "value") else request.severity
                )
            if request.assigned_to is not None:
                fields.append("assigned_to = %s")
                params.append(request.assigned_to)

            if not fields:
                # Nothing to update — return current state
                cursor.execute(
                    "SELECT id, title, description, status, severity, created_at, updated_at,"
                    " resolved_at, assigned_to, cluster_ids FROM incidents WHERE id = %s",
                    (incident_id,),
                )
                return _row_to_incident(cursor.fetchone())

            fields.append("updated_at = CURRENT_TIMESTAMP")
            params.append(incident_id)

            cursor.execute(
                f"UPDATE incidents SET {', '.join(fields)} WHERE id = %s"
                f" RETURNING id, title, description, status, severity, created_at,"
                f" updated_at, resolved_at, assigned_to, cluster_ids",
                params,
            )
            row = cursor.fetchone()
            conn.commit()
            cursor.close()
            conn.close()
            return _row_to_incident(row)

    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Failed to update incident {incident_id}: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))
