"""Tests for Celery tasks and deduplication"""

import pytest
from unittest.mock import patch, MagicMock
from uuid import uuid4
from datetime import datetime, timezone
import json

from src.tasks import cluster_logs, handle_dead_letter, check_clustering_health
from src.dedup import compute_log_hash, is_log_duplicate, mark_log_hash_seen, get_dedup_stats


# ============================================================================
# Deduplication Tests
# ============================================================================

class TestDeduplication:
    """Tests for log deduplication"""
    
    def test_compute_log_hash(self):
        """Test hash computation"""
        msg = "Connection timeout"
        source = "database"
        severity = "ERROR"
        
        hash1 = compute_log_hash(msg, source, severity)
        hash2 = compute_log_hash(msg, source, severity)
        
        # Same input produces same hash
        assert hash1 == hash2
        
        # Different input produces different hash
        hash3 = compute_log_hash("Different message", source, severity)
        assert hash1 != hash3
    
    def test_hash_consistency(self):
        """Test that hash is consistent across calls"""
        log_data = ("message", "source", "ERROR")
        
        hashes = [compute_log_hash(*log_data) for _ in range(5)]
        
        # All hashes should be identical
        assert len(set(hashes)) == 1
    
    def test_hash_sensitivity_to_changes(self):
        """Test that hash changes with any input change"""
        base = compute_log_hash("msg", "source", "ERROR")
        
        # Message change
        assert base != compute_log_hash("different", "source", "ERROR")
        
        # Source change
        assert base != compute_log_hash("msg", "different", "ERROR")
        
        # Severity change
        assert base != compute_log_hash("msg", "source", "WARNING")


# ============================================================================
# Task Tests
# ============================================================================

class TestClusterLogsTask:
    """Tests for cluster_logs task"""
    
    @patch('src.tasks.psycopg2.connect')
    def test_cluster_logs_success(self, mock_connect):
        """Test successful log clustering"""
        
        # Mock database connection
        mock_cursor = MagicMock()
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        # Mock database query results
        mock_cursor.fetchall.return_value = [
            (str(uuid4()), "Error message", "api-server", "ERROR", datetime.now(timezone.utc)),
            (str(uuid4()), "Warning message", "database", "WARNING", datetime.now(timezone.utc)),
        ]
        mock_cursor.fetchone.side_effect = [
            (str(uuid4()),),  # New cluster ID
        ]
        
        log_ids = [str(uuid4()), str(uuid4())]
        
        # Task should not raise
        result = cluster_logs(log_ids)
        
        assert result["status"] == "success"
        assert result["logs_clustered"] > 0
    
    @patch('src.tasks.psycopg2.connect')
    def test_cluster_logs_no_logs_found(self, mock_connect):
        """Test clustering when no logs found"""
        
        mock_cursor = MagicMock()
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchall.return_value = []  # No logs
        
        log_ids = [str(uuid4())]
        result = cluster_logs(log_ids)
        
        assert result["status"] == "no_logs_found"
        assert result["logs_clustered"] == 0
    
    @patch('src.tasks.psycopg2.connect')
    def test_cluster_logs_with_cluster_id(self, mock_connect):
        """Test adding logs to existing cluster"""
        
        mock_cursor = MagicMock()
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        mock_cursor.fetchall.return_value = [
            (str(uuid4()), "Error", "api", "ERROR", datetime.now(timezone.utc)),
        ]
        
        log_ids = [str(uuid4())]
        cluster_id = str(uuid4())
        
        result = cluster_logs(log_ids, cluster_id=cluster_id)
        
        # Should update existing cluster, not create new one
        assert result["cluster_id"] == cluster_id


class TestDeadLetterQueueTask:
    """Tests for handle_dead_letter task"""
    
    @patch('src.tasks.psycopg2.connect')
    def test_dead_letter_recording(self, mock_connect):
        """Test recording task in dead-letter queue"""
        
        mock_cursor = MagicMock()
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        result = handle_dead_letter(
            task_name="tasks.cluster_logs",
            task_id="task-id-123",
            args={"log_ids": ["uuid1", "uuid2"]},
            kwargs={},
            error_message="Connection timeout",
            error_traceback="Traceback...",
        )
        
        assert result["status"] == "recorded_in_dlq"
        assert result["task_id"] == "task-id-123"
        assert "recorded_at" in result


# ============================================================================
# Health Check Tests
# ============================================================================

class TestHealthCheck:
    """Tests for health check task"""
    
    def test_clustering_health(self):
        """Test health check"""
        result = check_clustering_health()
        
        assert result["status"] == "healthy"
        assert "timestamp" in result
        assert "db_config" in result


# ============================================================================
# Integration Tests
# ============================================================================

class TestDeduplicationIntegration:
    """Integration tests for deduplication with Celery"""
    
    @patch('src.dedup.redis_client')
    def test_dedup_flow_with_duplicates(self, mock_redis):
        """Test deduplication flow"""
        
        msg = "Database query timeout"
        source = "db-service"
        severity = "ERROR"
        
        # First call: not duplicate
        mock_redis.exists.return_value = False
        result1 = is_log_duplicate(msg, source, severity)
        assert result1 is False
        
        # Second call: duplicate
        mock_redis.exists.return_value = True
        result2 = is_log_duplicate(msg, source, severity)
        assert result2 is True


# ============================================================================
# Configuration Tests
# ============================================================================

class TestCeleryConfiguration:
    """Tests for Celery configuration"""
    
    def test_celery_app_exists(self):
        """Test that Celery app is properly initialized"""
        from src.celery_app import app
        
        assert app is not None
        assert app.conf.broker_url is not None
        assert app.conf.result_backend is not None
    
    def test_task_queues_configured(self):
        """Test that queues are properly configured"""
        from src.celery_app import app
        
        queues = app.conf.task_queues
        queue_names = [q.name for q in queues]
        
        assert "default" in queue_names
        assert "clustering" in queue_names
        assert "dead_letter" in queue_names


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
