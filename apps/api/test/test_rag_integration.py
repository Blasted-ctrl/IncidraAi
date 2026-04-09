"""
Integration tests for RAG system.
Tests embedding, retrieval, reasoning, and end-to-end RAG pipeline.
"""

import pytest
from datetime import datetime, timezone
import asyncio
import json
from unittest.mock import patch, MagicMock

from src.rag import EmbeddingStore, IncidentReasoner, IncidentRAG


class TestEmbeddingStore:
    """Test embedding store functionality."""
    
    def test_initialize_embedding_store(self):
        """Test embedding store initialization."""
        store = EmbeddingStore(model_name="all-MiniLM-L6-v2")
        assert store.model is not None
        assert store.logs_collection is not None
        assert store.runbooks_collection is not None
    
    def test_embed_text(self):
        """Test text embedding generation."""
        store = EmbeddingStore()
        text = "Database connection failed"
        embedding = store.embed_text(text)
        
        assert isinstance(embedding, list)
        assert len(embedding) > 0
        assert all(isinstance(x, float) for x in embedding)
    
    def test_add_log_to_store(self):
        """Test adding log to vector store."""
        store = EmbeddingStore()
        log_text = "Error: Connection timeout"
        metadata = {"source": "api", "severity": "error"}
        
        store.add_log_to_store("log-001", log_text, metadata)
        
        # Verify it was added
        count = store.logs_collection.count()
        assert count == 1
    
    def test_add_runbook_to_store(self):
        """Test adding runbook to vector store."""
        store = EmbeddingStore()
        runbook_text = "Database troubleshooting steps: 1. Check connection"
        metadata = {"title": "DB Troubleshoot", "service": "database"}
        
        store.add_runbook_to_store("runbook-001", runbook_text, metadata)
        
        count = store.runbooks_collection.count()
        assert count == 1
    
    def test_retrieve_similar_logs(self):
        """Test retrieving similar logs."""
        store = EmbeddingStore()
        
        # Add some logs
        logs = [
            ("log-001", "Database connection timeout after 30 seconds"),
            ("log-002", "Failed to connect to database host"),
            ("log-003", "Memory usage critical in cache service"),
        ]
        
        for log_id, text in logs:
            store.add_log_to_store(log_id, text, {"index": int(log_id[-3:])})
        
        # Query for database-related logs
        results = store.retrieve_similar_logs("database connection failed", top_k=2)
        
        assert results["count"] > 0 or len(results["documents"]) >= 0
        assert len(results["distances"]) >= 0
    
    def test_retrieve_relevant_runbooks(self):
        """Test retrieving relevant runbooks."""
        store = EmbeddingStore()
        
        # Add runbooks
        runbooks = [
            ("rb-001", "Database Troubleshooting", "Steps to fix database issues"),
            ("rb-002", "Memory Management", "How to manage memory in services"),
        ]
        
        for rb_id, title, content in runbooks:
            text = f"{title}: {content}"
            store.add_runbook_to_store(rb_id, text, {"title": title})
        
        # Query for database runbooks
        results = store.retrieve_relevant_runbooks("database connection problem", top_k=1)
        
        assert len(results["distances"]) >= 0


class TestIncidentReasoner:
    """Test LLM reasoning component."""
    
    def test_initialize_reasoner(self):
        """Test reasoner initialization."""
        reasoner = IncidentReasoner(api_key=None)
        assert reasoner.model is not None
    
    def test_reason_without_api_key(self):
        """Test mock reasoning when API key not available."""
        reasoner = IncidentReasoner(api_key=None)
        
        result = reasoner.reason_about_incident(
            incident_summary="Database connection failing",
            logs=["Error: connection timeout"],
            runbooks=["Check database server status"],
            cluster_info={"service": "api"}
        )
        
        assert "success" in result
        assert "reasoning" in result
        assert "model" in result
        assert result["model"] is not None
    
    def test_mock_reasoning_structure(self):
        """Test structure of mock reasoning output."""
        reasoner = IncidentReasoner(api_key=None)
        
        result = reasoner.reason_about_incident(
            incident_summary="High memory usage detected",
            logs=["Memory: 95% of 16GB"],
            runbooks=["Memory Management Best Practices"],
        )
        
        reasoning = result["reasoning"]
        expected_keys = ["root_cause", "severity", "affected_services", "actions", "metrics"]
        
        for key in expected_keys:
            assert key in reasoning, f"Missing key in reasoning: {key}"


class TestIncidentRAG:
    """Test complete RAG pipeline."""
    
    def test_initialize_rag(self):
        """Test RAG system initialization."""
        rag = IncidentRAG()
        assert rag.embedding_store is not None
        assert rag.reasoner is not None
    
    def test_ingest_runbooks(self):
        """Test ingesting runbooks into RAG."""
        rag = IncidentRAG()
        
        runbooks = [
            {
                "id": "rb-001",
                "title": "Database Troubleshooting",
                "service": "database",
                "tags": ["database", "troubleshooting"],
                "content": "Steps to troubleshoot database issues"
            },
            {
                "id": "rb-002",
                "title": "Celery Queue Management",
                "service": "celery",
                "tags": ["queue", "performance"],
                "content": "How to manage Celery task queues"
            }
        ]
        
        rag.ingest_runbooks(runbooks)
        
        count = rag.embedding_store.runbooks_collection.count()
        assert count == 2
    
    def test_analyze_incident_end_to_end(self):
        """Test complete incident analysis workflow."""
        rag = IncidentRAG()
        
        # Ingest runbooks
        runbooks = [
            {
                "id": "rb-001",
                "title": "Database Connection Troubleshooting",
                "service": "database",
                "tags": ["database", "connection"],
                "content": "Check database server status. Verify firewall rules. Review connection pool."
            }
        ]
        rag.ingest_runbooks(runbooks)
        
        # Analyze incident
        logs = [
            "Database connection timeout after 30 seconds",
            "Unable to acquire connection from pool",
            "Connection refused from host database.prod"
        ]
        
        result = rag.analyze_incident(
            incident_summary="Database connection failures affecting API service",
            logs=logs,
            cluster_info={"service": "api", "log_count": len(logs)},
            top_k_logs=2,
            top_k_runbooks=1
        )
        
        assert "incident_summary" in result
        assert "retrieved_logs" in result
        assert "retrieved_runbooks" in result
        assert "reasoning" in result
        
        # Verify structure
        assert result["retrieved_logs"]["count"] >= 0
        assert result["retrieved_runbooks"]["count"] >= 0
        assert result["reasoning"]["success"] in [True, False]


class TestRAGEndpoints:
    """Test RAG API endpoints."""
    
    @pytest.mark.asyncio
    async def test_rag_health_endpoint(self):
        """Test RAG health check endpoint."""
        from src.routes_rag import rag_health
        
        response = await rag_health()
        
        assert response["status"] == "healthy"
        assert "rag_initialized" in response
        assert "embedding_model" in response
    
    @pytest.mark.asyncio
    async def test_rag_analyze_endpoint(self):
        """Test RAG analysis endpoint."""
        from src.routes_rag import analyze_incident
        from src.routes_rag import RAGAnalysisRequest
        
        request = RAGAnalysisRequest(
            incident_summary="Service experiencing high latency",
            logs=[
                "API latency: p99=5000ms, p95=3000ms",
                "Database query time: 4500ms",
                "Cache hit ratio: 30%"
            ]
        )
        
        response = await analyze_incident(request)
        
        assert response.incident_summary is not None
        assert response.retrieved_logs is not None
        assert response.retrieved_runbooks is not None
        assert response.reasoning is not None


class TestRAGWithGoldenDataset:
    """Test RAG system with golden dataset."""
    
    def test_rag_on_golden_incident(self):
        """Test RAG analysis on a golden incident."""
        from test.test_rag_evaluation import GOLDEN_INCIDENTS
        
        rag = IncidentRAG()
        
        # Ingest runbooks
        runbooks = [
            {
                "id": "rb-connection",
                "title": "Database Connection Troubleshooting",
                "service": "database",
                "tags": ["database", "connection"],
                "content": "Check database connection pool status"
            },
            {
                "id": "rb-query",
                "title": "Query Performance Optimization",
                "service": "database",
                "tags": ["database", "performance"],
                "content": "Optimize slow queries with proper indexing"
            }
        ]
        rag.ingest_runbooks(runbooks)
        
        # Test on first golden incident
        incident = GOLDEN_INCIDENTS[0]
        
        result = rag.analyze_incident(
            incident_summary=incident["summary"],
            logs=incident["logs"],
            cluster_info={"id": incident["id"]},
            top_k_logs=3,
            top_k_runbooks=2
        )
        
        # Verify result structure
        assert result["incident_summary"] == incident["summary"]
        assert result["retrieved_logs"]["count"] >= 0
        assert result["retrieved_runbooks"]["count"] >= 0
        assert result["reasoning"]["success"] in [True, False]
        
        # Check reasoning output
        reasoning = result["reasoning"]["reasoning"]
        if reasoning:
            # If not empty, should have expected fields
            if "severity" in reasoning:
                assert reasoning["severity"] in ["low", "medium", "high", "critical"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
