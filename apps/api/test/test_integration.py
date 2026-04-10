"""
Integration tests for the currently implemented API surface.
These tests exercise the clustering and RAG routes exposed by FastAPI.
"""

from datetime import datetime, timezone
from pathlib import Path
import sys
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.main import app


@pytest.mark.asyncio
async def test_root_health_and_about_endpoints():
    """The top-level service endpoints should respond successfully."""
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        root = await client.get("/")
        health = await client.get("/health")
        about = await client.get("/about")

    assert root.status_code == 200
    assert root.json()["service"] == "Incident Triage API"

    assert health.status_code == 200
    assert health.json()["status"] == "ok"

    assert about.status_code == 200
    assert "features" in about.json()


@pytest.mark.asyncio
async def test_cluster_logs_submission_returns_task_id():
    """Submitting a clustering request should return a queued task identifier."""
    mock_task = SimpleNamespace(id="task-123")
    transport = ASGITransport(app=app)

    with patch("src.routes_clustering.cluster_logs.apply_async", return_value=mock_task):
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/clustering/cluster-logs",
                json={
                    "log_ids": [
                        "550e8400-e29b-41d4-a716-446655440000",
                        "550e8400-e29b-41d4-a716-446655440001",
                    ],
                    "skip_duplicates": True,
                },
            )

    assert response.status_code == 200
    payload = response.json()
    assert payload["task_id"] == "task-123"
    assert payload["status"] == "submitted"


@pytest.mark.asyncio
async def test_cluster_task_status_endpoint_reports_success():
    """Task status endpoint should surface Celery task results."""
    mock_result = MagicMock()
    mock_result.state = "SUCCESS"
    mock_result.result = {
        "cluster_id": "cluster-abc",
        "logs_clustered": 3,
        "logs_deduplicated": 1,
        "status": "success",
    }

    transport = ASGITransport(app=app)

    with patch("src.routes_clustering.celery_app.AsyncResult", return_value=mock_result):
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/clustering/tasks/task-123")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "SUCCESS"
    assert payload["result"]["cluster_id"] == "cluster-abc"


@pytest.mark.asyncio
async def test_cluster_task_status_endpoint_reports_failure():
    """Task status endpoint should expose failures returned by Celery."""
    mock_result = MagicMock()
    mock_result.state = "FAILURE"
    mock_result.info = RuntimeError("task exploded")
    transport = ASGITransport(app=app)

    with patch("src.routes_clustering.celery_app.AsyncResult", return_value=mock_result):
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/clustering/tasks/task-999")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "FAILURE"
    assert "task exploded" in payload["error"]


@pytest.mark.asyncio
async def test_cluster_task_result_endpoint_requires_success():
    """Task result endpoint should reject unfinished tasks."""
    mock_result = MagicMock()
    mock_result.state = "PENDING"
    transport = ASGITransport(app=app)

    with patch("src.routes_clustering.celery_app.AsyncResult", return_value=mock_result):
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/clustering/tasks/task-123/result")

    assert response.status_code == 400
    assert "not completed" in response.json()["detail"]


@pytest.mark.asyncio
async def test_clustering_health_endpoint_returns_healthy_payload():
    """Clustering health should succeed when the health task returns data."""
    mock_async_result = MagicMock()
    mock_async_result.get.return_value = {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    transport = ASGITransport(app=app)

    with patch(
        "src.routes_clustering.check_clustering_health.apply_async",
        return_value=mock_async_result,
    ):
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/clustering/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "healthy"
    assert "clustering" in payload


@pytest.mark.asyncio
async def test_clustering_health_endpoint_returns_unhealthy_payload_on_error():
    """Clustering health should degrade gracefully when task execution fails."""
    transport = ASGITransport(app=app)

    with patch(
        "src.routes_clustering.check_clustering_health.apply_async",
        side_effect=RuntimeError("broker unavailable"),
    ):
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/clustering/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "unhealthy"
    assert "broker unavailable" in payload["error"]


@pytest.mark.asyncio
async def test_clustering_stats_endpoint_returns_dedup_stats():
    """Stats endpoint should return deduplication metadata and active-task counts."""
    mock_inspect = MagicMock()
    mock_inspect.active.return_value = {"worker-a": [{"id": "task-1"}]}
    transport = ASGITransport(app=app)

    with patch("src.routes_clustering.celery_app.control.inspect", return_value=mock_inspect):
        with patch(
            "src.routes_clustering.get_dedup_stats",
            return_value={"ttl_seconds": 86400, "redis_db": 2},
        ):
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get("/api/clustering/stats")

    assert response.status_code == 200
    payload = response.json()
    assert payload["deduplication"]["redis_db"] == 2
    assert payload["active_tasks"]["worker-a"] == 1


@pytest.mark.asyncio
async def test_dead_letter_queue_endpoint_returns_records():
    """Dead-letter queue route should marshal DB records into JSON."""
    mock_cursor = MagicMock()
    mock_cursor.description = [("task_id",), ("status",)]
    mock_cursor.fetchall.return_value = [("task-1", "pending")]

    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cursor

    transport = ASGITransport(app=app)

    with patch("psycopg2.connect", return_value=mock_conn):
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/clustering/dead-letter-queue")

    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 1
    assert payload["records"][0]["task_id"] == "task-1"


@pytest.mark.asyncio
async def test_retry_task_endpoint_revokes_task():
    """Retry endpoint should revoke the original task before requeueing."""
    transport = ASGITransport(app=app)

    with patch("src.routes_clustering.celery_app.control.revoke") as mock_revoke:
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/api/clustering/tasks/task-123/retry")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "retry_initiated"
    mock_revoke.assert_called_once_with("task-123", terminate=True)


@pytest.mark.asyncio
async def test_rag_health_endpoint_reports_configuration():
    """RAG health should indicate configuration and vector store details."""
    transport = ASGITransport(app=app)

    with patch("src.routes_rag.get_rag_system") as mock_get_rag_system:
        mock_get_rag_system.return_value = SimpleNamespace(
            reasoner=SimpleNamespace(client=object())
        )
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/rag/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "healthy"
    assert payload["anthropic_configured"] is True


@pytest.mark.asyncio
async def test_rag_health_endpoint_handles_initialization_errors():
    """RAG health should return 503 when initialization fails."""
    transport = ASGITransport(app=app)

    with patch("src.routes_rag.get_rag_system", side_effect=RuntimeError("vector store offline")):
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/rag/health")

    assert response.status_code == 503
    assert "vector store offline" in response.json()["detail"]


@pytest.mark.asyncio
async def test_rag_analyze_endpoint_returns_analysis_payload():
    """RAG analysis route should return a structured incident triage response."""
    transport = ASGITransport(app=app)
    mock_rag = MagicMock()
    mock_rag.analyze_incident.return_value = {
        "incident_summary": "Database connection failures affecting API",
        "retrieved_logs": {
            "count": 2,
            "logs": ["Database timeout", "Connection pool exhausted"],
            "relevance_scores": [0.12, 0.25],
        },
        "retrieved_runbooks": {
            "count": 1,
            "runbooks": ["Database Connection Troubleshooting"],
            "relevance_scores": [0.08],
        },
        "reasoning": {
            "success": True,
            "reasoning": {
                "root_cause": "Connection pool exhaustion caused API request failures",
                "severity": "high",
                "affected_services": ["api-service", "database"],
                "actions": ["Check pool usage", "Restart exhausted workers"],
                "metrics": ["pool_utilization"],
                "escalation": "yes - database team",
            },
            "model": "claude-sonnet-4-0",
            "tokens_used": 321,
        },
    }

    with patch("src.routes_rag.get_rag_system", return_value=mock_rag):
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/rag/analyze",
                json={
                    "incident_summary": "Database connection failures affecting API",
                    "logs": [
                        "Database timeout",
                        "Connection pool exhausted",
                    ],
                },
            )

    assert response.status_code == 200
    payload = response.json()
    assert payload["reasoning"]["success"] is True
    assert payload["reasoning"]["model"] == "claude-sonnet-4-0"
    assert payload["retrieved_runbooks"]["count"] == 1


@pytest.mark.asyncio
async def test_ingest_runbooks_and_count_endpoints():
    """Runbook management endpoints should return success payloads."""
    transport = ASGITransport(app=app)
    mock_rag = MagicMock()
    mock_rag.embedding_store.runbooks_collection.count.return_value = 5

    with patch("src.routes_rag.get_rag_system", return_value=mock_rag):
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            ingest = await client.post(
                "/api/rag/ingest-runbooks",
                json=[
                    {
                        "id": "rb-1",
                        "title": "Database Troubleshooting",
                        "service": "database",
                        "tags": ["database"],
                        "content": "Check connection pool usage",
                    }
                ],
            )
            count = await client.get("/api/rag/runbooks-count")

    assert ingest.status_code == 200
    assert ingest.json()["runbooks_ingested"] == 1
    assert count.status_code == 200
    assert count.json()["runbooks_in_store"] == 5
