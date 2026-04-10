"""
API endpoints for AI triage: run triage on an incident, retrieve results,
and submit feedback to reinforce future analyses.
"""

from fastapi import APIRouter, HTTPException, Body, Request
from typing import Optional
from datetime import datetime, timezone
from uuid import uuid4
import logging
import psycopg2
from psycopg2.extras import RealDictCursor, Json
import os
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

from .config import get_database_config
from .types_api import (
    TriageRequest,
    TriageResult,
    TriageFeedback,
    RootCauseHypothesis,
    MitigationStep,
    RiskLevel,
)
from .observability import get_tracer, triage_latency_seconds, track_latency

logger = logging.getLogger(__name__)
tracer = get_tracer(__name__)

router = APIRouter(prefix="/triage", tags=["triage"])


def _get_conn():
    return psycopg2.connect(**get_database_config())


def _get_rag():
    """Lazy-import to avoid circular deps and defer heavy model loading."""
    from .routes_rag import get_rag_system
    return get_rag_system()


# ============================================================================
# Helpers
# ============================================================================

def _build_triage_result(triage_row, hypothesis_rows, step_rows) -> TriageResult:
    hypotheses = [
        RootCauseHypothesis(
            id=h["id"],
            hypothesis=h["hypothesis"],
            confidence=float(h["confidence"]),
            supporting_logs=h["supporting_logs"] or [],
            relevant_runbooks=[],
        )
        for h in hypothesis_rows
    ]

    steps = [
        MitigationStep(
            id=s["id"],
            step=s["step"],
            order=s["order"],
            estimated_time_minutes=s["estimated_time_minutes"],
            risk_level=s["risk_level"],
            automation_possible=s["automation_possible"],
        )
        for s in step_rows
    ]

    return TriageResult(
        id=triage_row["id"],
        incident_id=triage_row["incident_id"],
        created_at=triage_row["created_at"],
        completed_at=triage_row["completed_at"],
        summary=triage_row["summary"],
        confidence_score=float(triage_row["confidence_score"]),
        model_version=triage_row["model_version"],
        root_cause_hypotheses=hypotheses,
        mitigation_steps=steps,
    )


# ============================================================================
# Endpoints
# ============================================================================

@router.post("", response_model=TriageResult, status_code=201)
@limiter.limit("10/minute")
async def run_triage(http_request: Request, request: TriageRequest = Body(...)):
    """
    Run AI triage on an incident.

    Fetches the specified logs from the database, runs the RAG pipeline,
    then persists and returns the structured triage result. Feedback submitted
    via POST /triage/{id}/feedback is stored for future evaluation.
    """
    try:
        with tracer.start_as_current_span("run_triage"):
            with track_latency(triage_latency_seconds, "/triage"):
                conn = _get_conn()
                cursor = conn.cursor(cursor_factory=RealDictCursor)

                incident_id = str(request.incident_id)

                # Verify incident exists
                cursor.execute("SELECT id, title FROM incidents WHERE id = %s", (incident_id,))
                incident_row = cursor.fetchone()
                if not incident_row:
                    raise HTTPException(status_code=404, detail=f"Incident {incident_id} not found")

                # Fetch log text for the requested log IDs
                log_ids = [str(lid) for lid in request.log_ids]
                cursor.execute(
                    "SELECT id, message, severity, source FROM logs WHERE id = ANY(%s)",
                    (log_ids,),
                )
                log_rows = cursor.fetchall()

                log_texts = [
                    f"[{r['severity']}] {r['source']}: {r['message']}" for r in log_rows
                ]

                # Run RAG analysis
                rag = _get_rag()
                rag_result = rag.analyze_incident(
                    incident_summary=incident_row["title"],
                    logs=log_texts,
                    cluster_info=request.context,
                )

                reasoning = rag_result["reasoning"].get("reasoning", {})
                model_version = rag_result["reasoning"].get("model", "unknown")
                now = datetime.now(timezone.utc)

                # Derive a confidence score from the reasoning severity
                severity_confidence = {
                    "critical": 0.9,
                    "high": 0.75,
                    "medium": 0.6,
                    "low": 0.45,
                }
                confidence = severity_confidence.get(
                    str(reasoning.get("severity", "")).lower(), 0.5
                )

                # Compose the executive summary
                root_cause_text = reasoning.get("root_cause", "Unknown root cause")
                summary = (
                    f"Root cause: {root_cause_text}. "
                    f"Severity: {reasoning.get('severity', 'unknown')}. "
                    f"Escalation: {reasoning.get('escalation', 'not required')}."
                )

                # Persist triage result
                triage_id = str(uuid4())
                cursor.execute(
                    """
                    INSERT INTO triage_results
                        (id, incident_id, completed_at, summary, confidence_score, model_version)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING id, incident_id, created_at, completed_at,
                              summary, confidence_score, model_version
                    """,
                    (triage_id, incident_id, now, summary, confidence, model_version),
                )
                triage_row = cursor.fetchone()

                # Persist root cause hypothesis
                hypothesis_rows = []
                if root_cause_text and root_cause_text != "Unknown root cause":
                    cursor.execute(
                        """
                        INSERT INTO root_cause_hypotheses
                            (triage_result_id, hypothesis, confidence, supporting_logs)
                        VALUES (%s, %s, %s, %s)
                        RETURNING id, hypothesis, confidence, supporting_logs
                        """,
                        (triage_id, root_cause_text, confidence, log_ids[:5]),
                    )
                    hypothesis_rows = [cursor.fetchone()]

                # Persist mitigation steps
                step_rows = []
                for i, action in enumerate(reasoning.get("actions", []), start=1):
                    cursor.execute(
                        """
                        INSERT INTO mitigation_steps
                            (triage_result_id, step, "order", risk_level, automation_possible)
                        VALUES (%s, %s, %s, %s::risk_level, %s)
                        RETURNING id, step, "order", estimated_time_minutes,
                                  risk_level, automation_possible
                        """,
                        (triage_id, action, i, "MEDIUM", False),
                    )
                    step_rows.append(cursor.fetchone())

                conn.commit()
                cursor.close()
                conn.close()

                return _build_triage_result(triage_row, hypothesis_rows, step_rows)

    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Triage failed: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/{triage_id}", response_model=TriageResult)
async def get_triage_result(triage_id: str):
    """Retrieve a previously computed triage result."""
    try:
        conn = _get_conn()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        cursor.execute(
            "SELECT id, incident_id, created_at, completed_at, summary,"
            " confidence_score, model_version FROM triage_results WHERE id = %s",
            (triage_id,),
        )
        triage_row = cursor.fetchone()
        if not triage_row:
            raise HTTPException(status_code=404, detail=f"Triage result {triage_id} not found")

        cursor.execute(
            "SELECT id, hypothesis, confidence, supporting_logs"
            " FROM root_cause_hypotheses WHERE triage_result_id = %s ORDER BY confidence DESC",
            (triage_id,),
        )
        hypothesis_rows = cursor.fetchall()

        cursor.execute(
            'SELECT id, step, "order", estimated_time_minutes, risk_level, automation_possible'
            " FROM mitigation_steps WHERE triage_result_id = %s ORDER BY \"order\" ASC",
            (triage_id,),
        )
        step_rows = cursor.fetchall()

        cursor.close()
        conn.close()

        return _build_triage_result(triage_row, hypothesis_rows, step_rows)

    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Failed to get triage result {triage_id}: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/{triage_id}/feedback", status_code=204)
async def submit_triage_feedback(triage_id: str, feedback: TriageFeedback = Body(...)):
    """
    Submit feedback on a triage result.

    Feedback is persisted to the triage_feedback table and will be used in
    future evaluation runs to measure top-3 root cause accuracy.
    """
    try:
        conn = _get_conn()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Verify triage result exists
        cursor.execute("SELECT id FROM triage_results WHERE id = %s", (triage_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail=f"Triage result {triage_id} not found")

        # Determine feedback type from the submitted data
        if feedback.correct_hypothesis:
            feedback_type = "helpful"
        elif feedback.actual_root_cause:
            feedback_type = "partially_helpful"
        else:
            feedback_type = "unhelpful"

        notes_parts = []
        if feedback.actual_root_cause:
            notes_parts.append(f"Actual root cause: {feedback.actual_root_cause}")
        if feedback.resolution_time_minutes:
            notes_parts.append(f"Resolution time: {feedback.resolution_time_minutes} min")
        if feedback.comment:
            notes_parts.append(feedback.comment)

        cursor.execute(
            """
            INSERT INTO triage_feedback (triage_result_id, feedback_type, notes)
            VALUES (%s, %s, %s)
            """,
            (triage_id, feedback_type, "\n".join(notes_parts) or None),
        )
        conn.commit()
        cursor.close()
        conn.close()

    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Failed to submit feedback for triage {triage_id}: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))
