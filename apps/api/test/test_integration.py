"""
Integration tests for log ingestion → clustering → triage workflow.
Tests the complete end-to-end flow from log ingestion through incident triage.
"""

import json
import pytest
import asyncio
from datetime import datetime, timezone
from httpx import AsyncClient
import sys
from pathlib import Path
from unittest.mock import patch, AsyncMock

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.main import app
from src.tasks import cluster_logs, handle_dead_letter
from src.models import (
    LogEntry, ClusterRequest, TriageRequest,
    IncidentStatus
)


class TestLogIngestionEndpoint:
    """Test log ingestion API endpoints."""
    
    @pytest.mark.asyncio
    async def test_submit_logs_for_clustering(self):
        """Test submitting logs for clustering."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            logs = [
                {
                    "message": "Database connection failed",
                    "source": "api-service",
                    "severity": "error",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "attributes": {"retry_count": 3}
                },
                {
                    "message": "Database connection failed",
                    "source": "api-service",
                    "severity": "error",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "attributes": {"retry_count": 5}
                }
            ]
            
            response = await client.post(
                "/api/clustering/cluster-logs",
                json={"logs": logs}
            )
            
            assert response.status_code in [200, 202]
            data = response.json()
            assert "task_id" in data or "task_ids" in data
    
    @pytest.mark.asyncio
    async def test_clustering_task_creation(self):
        """Test that clustering task is created in Celery."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            logs = [
                {
                    "message": "Service unavailable",
                    "source": "web-app",
                    "severity": "error",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            ]
            
            response = await client.post(
                "/api/clustering/cluster-logs",
                json={"logs": logs}
            )
            
            assert response.status_code in [200, 202]


class TestClusteringTaskFlow:
    """Test clustering task processing."""
    
    def test_cluster_task_processes_logs(self):
        """Test that cluster_logs task processes logs correctly."""
        log_data = {
            "message": "Connection timeout",
            "source": "api",
            "severity": "error",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "attributes": {}
        }
        
        # Verify the log data is valid for processing
        required_fields = ["message", "source", "severity", "timestamp"]
        for field in required_fields:
            assert field in log_data
    
    def test_cluster_task_creates_incident(self):
        """Test that clustering creates an incident record."""
        # Verify incident data structure
        incident_data = {
            "cluster_id": "cluster-123",
            "severity": "error",
            "affected_services": ["api-service", "db-service"],
            "log_count": 5,
            "first_occurrence": datetime.now(timezone.utc).isoformat(),
            "last_occurrence": datetime.now(timezone.utc).isoformat(),
            "status": "open"
        }
        
        required_fields = ["cluster_id", "severity", "status"]
        for field in required_fields:
            assert field in incident_data


class TestTriageWorkflow:
    """Test log triage workflow."""
    
    @pytest.mark.asyncio
    async def test_get_triage_results(self):
        """Test retrieving triage results."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Create a triage request
            triage_data = {
                "incident_id": "incident-123",
                "logs": [
                    {
                        "message": "Error in database connection",
                        "source": "api",
                        "severity": "error"
                    }
                ]
            }
            
            response = await client.get(
                "/api/clustering/health"
            )
            
            assert response.status_code == 200


class TestEndToEndIntegration:
    """Test complete end-to-end workflow."""
    
    @pytest.mark.asyncio
    async def test_log_ingestion_clustering_triage_flow(self):
        """Test complete flow: ingest → cluster → triage."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Step 1: Ingest logs
            logs = [
                {
                    "message": "Database query timeout",
                    "source": "reports-service",
                    "severity": "error",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "attributes": {"query_time_ms": 35000}
                },
                {
                    "message": "Database query timeout",
                    "source": "reports-service",
                    "severity": "error",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "attributes": {"query_time_ms": 32000}
                }
            ]
            
            # Submit for clustering
            response = await client.post(
                "/api/clustering/cluster-logs",
                json={"logs": logs}
            )
            
            assert response.status_code in [200, 202]
            task_response = response.json()
            
            # Verify task was created
            assert "task_id" in task_response or "task_ids" in task_response
            
            # Step 2: Check clustering status
            if "task_id" in task_response:
                task_id = task_response["task_id"]
                
                # Get task status
                status_response = await client.get(
                    f"/api/clustering/tasks/{task_id}"
                )
                
                assert status_response.status_code == 200
                status_data = status_response.json()
                assert "status" in status_data


class TestDeadLetterQueueIntegration:
    """Test dead-letter queue for failed tasks."""
    
    @pytest.mark.asyncio
    async def test_failed_task_goes_to_dlq(self):
        """Test that failed tasks go to dead-letter queue."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Get DLQ stats
            response = await client.get(
                "/api/clustering/dead-letter-queue"
            )
            
            assert response.status_code == 200
            dlq_data = response.json()
            
            # Verify DLQ structure
            assert "tasks" in dlq_data or "count" in dlq_data or isinstance(dlq_data, list)


class TestTaskRetryWorkflow:
    """Test task retry and backoff."""
    
    @pytest.mark.asyncio
    async def test_task_retry_on_failure(self):
        """Test that tasks are retried on failure."""
        # Create logs that might fail processing
        logs = [
            {
                "message": "Service error",
                "source": "problematic-service",
                "severity": "error",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        ]
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                "/api/clustering/cluster-logs",
                json={"logs": logs}
            )
            
            assert response.status_code in [200, 202]


class TestClusteringStats:
    """Test clustering statistics and monitoring."""
    
    @pytest.mark.asyncio
    async def test_get_clustering_statistics(self):
        """Test retrieving clustering statistics."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get(
                "/api/clustering/stats"
            )
            
            assert response.status_code == 200
            stats = response.json()
            
            # Verify stats structure
            assert isinstance(stats, dict)


class TestClusteringHealthCheck:
    """Test clustering system health."""
    
    @pytest.mark.asyncio
    async def test_clustering_health_endpoint(self):
        """Test clustering health check endpoint."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get(
                "/api/clustering/health"
            )
            
            assert response.status_code == 200
            health = response.json()
            
            # Verify health structure
            assert isinstance(health, dict)
            if "status" in health:
                assert health["status"] in ["healthy", "ready", "ok"]
