"""
Python Client Testing Suite
Run: pytest test_python_client.py -v
"""

import sys
from pathlib import Path
from datetime import datetime
from uuid import UUID, uuid4
from unittest.mock import Mock, patch, AsyncMock, MagicMock
import json

# Add src directory to path to allow imports
src_path = str(Path(__file__).parent.parent / "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)

import pytest

# Import from src modules
from client import SyncTriageClient, TriageClient, TriageClientConfig, create_client

# Import types - try both import paths
try:
    from types_api import (
        CreateLogRequest,
        CreateIncidentRequest,
        TriageRequest,
        UpdateIncidentRequest,
        TriageFeedback,
        LogSeverity,
        IncidentSeverity,
        IncidentStatus,
        Log,
        Incident,
        TriageResult,
        LogList,
        IncidentList,
    )
except ImportError:
    # Fallback if direct import fails
    import importlib.util
    _spec = importlib.util.spec_from_file_location("types_api", Path(__file__).parent.parent / "src" / "types_api.py")
    _api_types = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_api_types)
    
    CreateLogRequest = _api_types.CreateLogRequest
    CreateIncidentRequest = _api_types.CreateIncidentRequest
    TriageRequest = _api_types.TriageRequest
    UpdateIncidentRequest = _api_types.UpdateIncidentRequest
    TriageFeedback = _api_types.TriageFeedback
    LogSeverity = _api_types.LogSeverity
    IncidentSeverity = _api_types.IncidentSeverity
    IncidentStatus = _api_types.IncidentStatus
    Log = _api_types.Log
    Incident = _api_types.Incident
    TriageResult = _api_types.TriageResult
    LogList = _api_types.LogList
    IncidentList = _api_types.IncidentList


@pytest.fixture
def config():
    """Create test client configuration"""
    return TriageClientConfig(
        base_url="http://localhost:8000",
        api_key="test-key",
        timeout=30.0,
    )


@pytest.fixture
def sync_client(config):
    """Create sync client for testing"""
    with patch("httpx.Client"):
        client = SyncTriageClient(config)
        return client


@pytest.fixture
async def async_client(config):
    """Create async client for testing"""
    with patch("httpx.AsyncClient"):
        client = TriageClient(config)
        yield client
        await client.close()


class TestClientInitialization:
    """Test client creation and configuration"""

    def test_client_config_creation(self, config):
        """Test TriageClientConfig initialization"""
        assert config.base_url == "http://localhost:8000"
        assert config.api_key == "test-key"
        assert config.timeout == 30.0

    def test_client_config_headers(self, config):
        """Test header generation with auth"""
        headers = config.get_headers()
        assert headers["Content-Type"] == "application/json"
        assert headers["Authorization"] == "Bearer test-key"

    def test_client_config_headers_no_auth(self):
        """Test headers without API key"""
        config = TriageClientConfig(base_url="http://localhost:8000")
        headers = config.get_headers()
        assert "Authorization" not in headers

    def test_sync_client_creation(self, config):
        """Test sync client initialization"""
        with patch("httpx.Client"):
            client = SyncTriageClient(config)
            assert client.client is not None

    def test_async_client_creation(self, config):
        """Test async client initialization"""
        with patch("httpx.AsyncClient"):
            client = TriageClient(config)
            assert client.client is not None

    def test_create_client_factory_sync(self, config):
        """Test sync client factory"""
        with patch("httpx.Client"):
            client = create_client("http://localhost:8000", sync=True)
            assert isinstance(client, SyncTriageClient)

    def test_create_client_factory_async(self, config):
        """Test async client factory"""
        with patch("httpx.AsyncClient"):
            client = create_client("http://localhost:8000", sync=False)
            assert isinstance(client, TriageClient)


class TestSyncLogsAPI:
    """Test synchronous logs API methods"""

    def test_list_logs(self, sync_client):
        """Test listing logs"""
        mock_response = Mock()
        mock_response.json.return_value = {
            "items": [],
            "total": 0,
            "limit": 50,
            "offset": 0,
        }
        mock_response.status_code = 200
        sync_client.client.get = Mock(return_value=mock_response)

        result = sync_client.list_logs(limit=50, offset=0)

        assert isinstance(result, LogList)
        assert result.total == 0
        assert result.limit == 50

    def test_list_logs_with_filters(self, sync_client):
        """Test listing logs with filters"""
        mock_response = Mock()
        mock_response.json.return_value = {
            "items": [],
            "total": 0,
            "limit": 25,
            "offset": 0,
        }
        mock_response.status_code = 200
        sync_client.client.get = Mock(return_value=mock_response)

        result = sync_client.list_logs(
            limit=25,
            severity=LogSeverity.ERROR,
        )

        assert result.limit == 25
        sync_client.client.get.assert_called_once()

    def test_create_log(self, sync_client):
        """Test creating a log"""
        log_id = uuid4()
        mock_response = Mock()
        mock_response.json.return_value = {
            "id": str(log_id),
            "message": "Test error",
            "severity": "ERROR",
            "source": "test-service",
            "timestamp": datetime.now().isoformat(),
        }
        mock_response.status_code = 201
        sync_client.client.post = Mock(return_value=mock_response)

        log_request = CreateLogRequest(
            message="Test error",
            severity=LogSeverity.ERROR,
            source="test-service",
        )

        result = sync_client.create_log(log_request)

        assert isinstance(result, Log)
        assert result.message == "Test error"
        assert result.severity == LogSeverity.ERROR
        sync_client.client.post.assert_called_once()

    def test_get_log(self, sync_client):
        """Test getting a specific log"""
        log_id = uuid4()
        mock_response = Mock()
        mock_response.json.return_value = {
            "id": str(log_id),
            "message": "Test",
            "severity": "INFO",
            "source": "test",
            "timestamp": datetime.now().isoformat(),
            "incident_ids": [],
            "related_logs": [],
        }
        mock_response.status_code = 200
        sync_client.client.get = Mock(return_value=mock_response)

        result = sync_client.get_log(log_id)

        assert result.id == log_id
        sync_client.client.get.assert_called_once()


class TestSyncIncidentsAPI:
    """Test synchronous incidents API methods"""

    def test_list_incidents(self, sync_client):
        """Test listing incidents"""
        mock_response = Mock()
        mock_response.json.return_value = {
            "items": [],
            "total": 0,
            "limit": 50,
            "offset": 0,
        }
        mock_response.status_code = 200
        sync_client.client.get = Mock(return_value=mock_response)

        result = sync_client.list_incidents()

        assert isinstance(result, IncidentList)
        assert result.total == 0

    def test_list_incidents_with_filter(self, sync_client):
        """Test listing incidents with status filter"""
        mock_response = Mock()
        mock_response.json.return_value = {
            "items": [],
            "total": 0,
            "limit": 50,
            "offset": 0,
        }
        mock_response.status_code = 200
        sync_client.client.get = Mock(return_value=mock_response)

        result = sync_client.list_incidents(status=IncidentStatus.OPEN)

        assert isinstance(result, IncidentList)
        sync_client.client.get.assert_called_once()

    def test_create_incident(self, sync_client):
        """Test creating an incident"""
        incident_id = uuid4()
        mock_response = Mock()
        mock_response.json.return_value = {
            "id": str(incident_id),
            "title": "Test Incident",
            "severity": "HIGH",
            "status": "OPEN",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "cluster_ids": [],
        }
        mock_response.status_code = 201
        sync_client.client.post = Mock(return_value=mock_response)

        incident_request = CreateIncidentRequest(
            title="Test Incident",
            severity=IncidentSeverity.HIGH,
        )

        result = sync_client.create_incident(incident_request)

        assert isinstance(result, Incident)
        assert result.title == "Test Incident"
        assert result.severity == IncidentSeverity.HIGH
        sync_client.client.post.assert_called_once()

    def test_get_incident(self, sync_client):
        """Test getting a specific incident"""
        incident_id = uuid4()
        mock_response = Mock()
        mock_response.json.return_value = {
            "id": str(incident_id),
            "title": "Test",
            "severity": "MEDIUM",
            "status": "INVESTIGATING",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "cluster_ids": [],
            "logs": [],
            "triage_results": [],
            "timeline": [],
        }
        mock_response.status_code = 200
        sync_client.client.get = Mock(return_value=mock_response)

        result = sync_client.get_incident(incident_id)

        assert result.id == incident_id
        sync_client.client.get.assert_called_once()

    def test_update_incident(self, sync_client):
        """Test updating an incident"""
        incident_id = uuid4()
        mock_response = Mock()
        mock_response.json.return_value = {
            "id": str(incident_id),
            "title": "Updated Title",
            "severity": "CRITICAL",
            "status": "RESOLVED",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "cluster_ids": [],
        }
        mock_response.status_code = 200
        sync_client.client.patch = Mock(return_value=mock_response)

        update_request = UpdateIncidentRequest(
            status=IncidentStatus.RESOLVED,
            severity=IncidentSeverity.CRITICAL,
        )

        result = sync_client.update_incident(incident_id, update_request)

        assert result.status == IncidentStatus.RESOLVED
        sync_client.client.patch.assert_called_once()


class TestSyncTriageAPI:
    """Test synchronous triage API methods"""

    def test_triage_incident(self, sync_client):
        """Test running triage analysis"""
        incident_id = uuid4()
        log_id = uuid4()
        triage_id = uuid4()

        mock_response = Mock()
        mock_response.json.return_value = {
            "id": str(triage_id),
            "incident_id": str(incident_id),
            "created_at": datetime.now().isoformat(),
            "completed_at": datetime.now().isoformat(),
            "root_cause_hypotheses": [
                {
                    "id": str(uuid4()),
                    "hypothesis": "Database timeout",
                    "confidence": 0.85,
                    "supporting_logs": [],
                    "relevant_runbooks": [],
                    "similar_incidents": [],
                }
            ],
            "mitigation_steps": [
                {
                    "id": str(uuid4()),
                    "step": "Restart database",
                    "order": 1,
                    "risk_level": "MEDIUM",
                    "automation_possible": False,
                }
            ],
            "summary": "Analysis shows database timeout",
            "confidence_score": 0.85,
            "model_version": "1.0.0",
        }
        mock_response.status_code = 200
        sync_client.client.post = Mock(return_value=mock_response)

        triage_request = TriageRequest(
            incident_id=incident_id,
            log_ids=[log_id],
        )

        result = sync_client.triage_incident(triage_request)

        assert isinstance(result, TriageResult)
        assert len(result.root_cause_hypotheses) == 1
        assert len(result.mitigation_steps) == 1
        assert result.confidence_score == 0.85
        sync_client.client.post.assert_called_once()

    def test_get_triage_result(self, sync_client):
        """Test getting a triage result"""
        triage_id = uuid4()
        mock_response = Mock()
        mock_response.json.return_value = {
            "id": str(triage_id),
            "incident_id": str(uuid4()),
            "created_at": datetime.now().isoformat(),
            "completed_at": datetime.now().isoformat(),
            "root_cause_hypotheses": [],
            "mitigation_steps": [],
            "summary": "Test",
            "confidence_score": 0.5,
            "model_version": "1.0.0",
        }
        mock_response.status_code = 200
        sync_client.client.get = Mock(return_value=mock_response)

        result = sync_client.get_triage_result(triage_id)

        assert result.id == triage_id
        sync_client.client.get.assert_called_once()

    def test_submit_triage_feedback(self, sync_client):
        """Test submitting triage feedback"""
        triage_id = uuid4()
        mock_response = Mock()
        mock_response.status_code = 204
        sync_client.client.post = Mock(return_value=mock_response)

        feedback = TriageFeedback(
            helpful_steps=[],
            resolution_time_minutes=30,
        )

        sync_client.submit_triage_feedback(triage_id, feedback)

        sync_client.client.post.assert_called_once()


class TestDataValidation:
    """Test Pydantic model validation"""

    def test_create_log_request_validation(self):
        """Test log request validation"""
        # Valid request
        log = CreateLogRequest(
            message="Test",
            severity=LogSeverity.ERROR,
            source="service",
        )
        assert log.message == "Test"

    def test_create_incident_request_validation(self):
        """Test incident request validation"""
        # Valid request
        incident = CreateIncidentRequest(
            title="Test Incident",
            severity=IncidentSeverity.HIGH,
        )
        assert incident.title == "Test Incident"

    def test_incident_min_title_length(self):
        """Test incident title minimum length"""
        with pytest.raises(ValueError):
            CreateIncidentRequest(
                title="",  # Empty
                severity=IncidentSeverity.LOW,
            )

    def test_triage_request_requires_log_ids(self):
        """Test that triage request requires log IDs"""
        with pytest.raises(ValueError):
            TriageRequest(
                incident_id=uuid4(),
                log_ids=[],  # Empty
            )

    def test_confidence_score_range(self):
        """Test confidence score validation"""
        # Valid: between 0 and 1
        result = TriageResult(
            id=uuid4(),
            incident_id=uuid4(),
            created_at=datetime.now(),
            completed_at=datetime.now(),
            root_cause_hypotheses=[],
            mitigation_steps=[],
            summary="Test",
            confidence_score=0.95,
            model_version="1.0.0",
        )
        assert result.confidence_score == 0.95

        # Invalid: out of range
        with pytest.raises(ValueError):
            TriageResult(
                id=uuid4(),
                incident_id=uuid4(),
                created_at=datetime.now(),
                root_cause_hypotheses=[],
                mitigation_steps=[],
                summary="Test",
                confidence_score=1.5,  # Out of range
                model_version="1.0.0",
            )


class TestErrorHandling:
    """Test error handling"""

    def test_health_check_success(self, sync_client):
        """Test successful health check"""
        mock_response = Mock()
        mock_response.status_code = 200
        sync_client.client.get = Mock(return_value=mock_response)

        result = sync_client.health()
        assert result is True

    def test_health_check_failure(self, sync_client):
        """Test failed health check"""
        sync_client.client.get = Mock(side_effect=Exception("Connection error"))

        result = sync_client.health()
        assert result is False

    def test_http_error_raises(self, sync_client):
        """Test HTTP error response"""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.raise_for_status = Mock(side_effect=Exception("404 Not Found"))
        sync_client.client.get = Mock(return_value=mock_response)

        with pytest.raises(Exception):
            sync_client.get_log(uuid4())


class TestContextManagers:
    """Test context manager functionality"""

    def test_sync_client_context_manager(self, config):
        """Test sync client context manager"""
        with patch("httpx.Client") as mock_client_class:
            mock_instance = MagicMock()
            mock_client_class.return_value = mock_instance

            with SyncTriageClient(config) as client:
                assert client is not None

            mock_instance.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_async_client_context_manager(self, config):
        """Test async client context manager"""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_instance = AsyncMock()
            mock_client_class.return_value = mock_instance

            async with TriageClient(config) as client:
                assert client is not None

            mock_instance.aclose.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
