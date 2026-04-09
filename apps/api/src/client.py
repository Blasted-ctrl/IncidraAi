"""
Incident Triage API - Python Client
Async HTTP client for consuming the REST API
Uses httpx for async/sync support
"""

from typing import Any, Optional
from uuid import UUID

try:
    import httpx
except ImportError:
    raise ImportError(
        "httpx is required for the API client. Install it with: pip install httpx"
    )

# Import from types module - using relative import
try:
    # When imported as module
    from .types import (
        APIError,
        CreateIncidentRequest,
        CreateLogRequest,
        Incident,
        IncidentDetail,
        IncidentList,
        IncidentSortBy,
        Log,
        LogDetail,
        LogList,
        LogSeverity,
        TriageFeedback,
        TriageRequest,
        TriageResult,
        UpdateIncidentRequest,
    )
except ImportError:
    # When imported directly from sys.path
    from types_api import (
        APIError,
        CreateIncidentRequest,
        CreateLogRequest,
        Incident,
        IncidentDetail,
        IncidentList,
        IncidentSortBy,
        Log,
        LogDetail,
        LogList,
        LogSeverity,
        TriageFeedback,
        TriageRequest,
        TriageResult,
        UpdateIncidentRequest,
    )


class TriageClientConfig:
    """Configuration for TriageClient"""

    def __init__(
        self,
        base_url: str,
        api_key: Optional[str] = None,
        headers: Optional[dict[str, str]] = None,
        timeout: float = 30.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.headers = headers or {}
        self.timeout = timeout

    def get_headers(self) -> dict[str, str]:
        """Get combined headers including auth"""
        headers = {"Content-Type": "application/json", **self.headers}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers


class TriageClient:
    """Async Incident Triage API client"""

    def __init__(self, config: TriageClientConfig):
        self.config = config
        self.client = httpx.AsyncClient(
            base_url=config.base_url,
            headers=config.get_headers(),
            timeout=config.timeout,
        )

    async def close(self) -> None:
        """Close the HTTP client"""
        await self.client.aclose()

    async def __aenter__(self):
        """Async context manager entry"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()

    # ========================================================================
    # Logs
    # ========================================================================

    async def list_logs(
        self,
        limit: int = 50,
        offset: int = 0,
        incident_id: Optional[UUID] = None,
        cluster_id: Optional[UUID] = None,
        severity: Optional[LogSeverity] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
    ) -> LogList:
        """List logs with filtering and pagination"""
        params = {
            "limit": limit,
            "offset": offset,
        }
        if incident_id:
            params["incident_id"] = str(incident_id)
        if cluster_id:
            params["cluster_id"] = str(cluster_id)
        if severity:
            params["severity"] = severity.value
        if start_time:
            params["start_time"] = start_time
        if end_time:
            params["end_time"] = end_time

        response = await self.client.get("/logs", params=params)
        response.raise_for_status()
        return LogList(**response.json())

    async def get_log(self, log_id: UUID) -> LogDetail:
        """Get a specific log by ID"""
        response = await self.client.get(f"/logs/{log_id}")
        response.raise_for_status()
        return LogDetail(**response.json())

    async def create_log(self, log: CreateLogRequest) -> Log:
        """Create a new log entry"""
        response = await self.client.post(
            "/logs",
            json=log.model_dump(mode="json", exclude_none=True),
        )
        response.raise_for_status()
        return Log(**response.json())

    # ========================================================================
    # Incidents
    # ========================================================================

    async def list_incidents(
        self,
        limit: int = 50,
        offset: int = 0,
        status: Optional[str] = None,
        severity: Optional[str] = None,
        sort_by: IncidentSortBy = IncidentSortBy.CREATED_AT,
    ) -> IncidentList:
        """List incidents with filtering and sorting"""
        params = {
            "limit": limit,
            "offset": offset,
            "sort_by": sort_by.value,
        }
        if status:
            params["status"] = status
        if severity:
            params["severity"] = severity

        response = await self.client.get("/incidents", params=params)
        response.raise_for_status()
        return IncidentList(**response.json())

    async def get_incident(self, incident_id: UUID) -> IncidentDetail:
        """Get a specific incident by ID"""
        response = await self.client.get(f"/incidents/{incident_id}")
        response.raise_for_status()
        return IncidentDetail(**response.json())

    async def create_incident(self, incident: CreateIncidentRequest) -> Incident:
        """Create a new incident"""
        response = await self.client.post(
            "/incidents",
            json=incident.model_dump(mode="json", exclude_none=True),
        )
        response.raise_for_status()
        return Incident(**response.json())

    async def update_incident(
        self, incident_id: UUID, incident: UpdateIncidentRequest
    ) -> Incident:
        """Update an existing incident"""
        response = await self.client.patch(
            f"/incidents/{incident_id}",
            json=incident.model_dump(mode="json", exclude_none=True),
        )
        response.raise_for_status()
        return Incident(**response.json())

    # ========================================================================
    # Triage
    # ========================================================================

    async def triage_incident(self, triage_request: TriageRequest) -> TriageResult:
        """Run AI triage on an incident"""
        response = await self.client.post(
            "/triage",
            json=triage_request.model_dump(mode="json", exclude_none=True),
        )
        response.raise_for_status()
        return TriageResult(**response.json())

    async def get_triage_result(self, triage_id: UUID) -> TriageResult:
        """Get a specific triage result by ID"""
        response = await self.client.get(f"/triage/{triage_id}")
        response.raise_for_status()
        return TriageResult(**response.json())

    async def submit_triage_feedback(
        self, triage_id: UUID, feedback: TriageFeedback
    ) -> None:
        """Submit feedback on a triage result"""
        response = await self.client.post(
            f"/triage/{triage_id}/feedback",
            json=feedback.model_dump(mode="json", exclude_none=True),
        )
        response.raise_for_status()

    # ========================================================================
    # Health & Diagnostics
    # ========================================================================

    async def health(self) -> bool:
        """Check API health"""
        try:
            response = await self.client.get("/health")
            return response.status_code == 200
        except Exception:
            return False


class SyncTriageClient:
    """Synchronous wrapper around TriageClient for use in sync code"""

    def __init__(self, config: TriageClientConfig):
        self.client = httpx.Client(
            base_url=config.base_url,
            headers=config.get_headers(),
            timeout=config.timeout,
        )

    def close(self) -> None:
        """Close the HTTP client"""
        self.client.close()

    def __enter__(self):
        """Sync context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Sync context manager exit"""
        self.close()

    # ========================================================================
    # Logs
    # ========================================================================

    def list_logs(
        self,
        limit: int = 50,
        offset: int = 0,
        incident_id: Optional[UUID] = None,
        cluster_id: Optional[UUID] = None,
        severity: Optional[LogSeverity] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
    ) -> LogList:
        """List logs with filtering and pagination"""
        params = {
            "limit": limit,
            "offset": offset,
        }
        if incident_id:
            params["incident_id"] = str(incident_id)
        if cluster_id:
            params["cluster_id"] = str(cluster_id)
        if severity:
            params["severity"] = severity.value
        if start_time:
            params["start_time"] = start_time
        if end_time:
            params["end_time"] = end_time

        response = self.client.get("/logs", params=params)
        response.raise_for_status()
        return LogList(**response.json())

    def get_log(self, log_id: UUID) -> LogDetail:
        """Get a specific log by ID"""
        response = self.client.get(f"/logs/{log_id}")
        response.raise_for_status()
        return LogDetail(**response.json())

    def create_log(self, log: CreateLogRequest) -> Log:
        """Create a new log entry"""
        response = self.client.post(
            "/logs",
            json=log.model_dump(mode="json", exclude_none=True),
        )
        response.raise_for_status()
        return Log(**response.json())

    # ========================================================================
    # Incidents
    # ========================================================================

    def list_incidents(
        self,
        limit: int = 50,
        offset: int = 0,
        status: Optional[str] = None,
        severity: Optional[str] = None,
        sort_by: IncidentSortBy = IncidentSortBy.CREATED_AT,
    ) -> IncidentList:
        """List incidents with filtering and sorting"""
        params = {
            "limit": limit,
            "offset": offset,
            "sort_by": sort_by.value,
        }
        if status:
            params["status"] = status
        if severity:
            params["severity"] = severity

        response = self.client.get("/incidents", params=params)
        response.raise_for_status()
        return IncidentList(**response.json())

    def get_incident(self, incident_id: UUID) -> IncidentDetail:
        """Get a specific incident by ID"""
        response = self.client.get(f"/incidents/{incident_id}")
        response.raise_for_status()
        return IncidentDetail(**response.json())

    def create_incident(self, incident: CreateIncidentRequest) -> Incident:
        """Create a new incident"""
        response = self.client.post(
            "/incidents",
            json=incident.model_dump(mode="json", exclude_none=True),
        )
        response.raise_for_status()
        return Incident(**response.json())

    def update_incident(
        self, incident_id: UUID, incident: UpdateIncidentRequest
    ) -> Incident:
        """Update an existing incident"""
        response = self.client.patch(
            f"/incidents/{incident_id}",
            json=incident.model_dump(mode="json", exclude_none=True),
        )
        response.raise_for_status()
        return Incident(**response.json())

    # ========================================================================
    # Triage
    # ========================================================================

    def triage_incident(self, triage_request: TriageRequest) -> TriageResult:
        """Run AI triage on an incident"""
        response = self.client.post(
            "/triage",
            json=triage_request.model_dump(mode="json", exclude_none=True),
        )
        response.raise_for_status()
        return TriageResult(**response.json())

    def get_triage_result(self, triage_id: UUID) -> TriageResult:
        """Get a specific triage result by ID"""
        response = self.client.get(f"/triage/{triage_id}")
        response.raise_for_status()
        return TriageResult(**response.json())

    def submit_triage_feedback(
        self, triage_id: UUID, feedback: TriageFeedback
    ) -> None:
        """Submit feedback on a triage result"""
        response = self.client.post(
            f"/triage/{triage_id}/feedback",
            json=feedback.model_dump(mode="json", exclude_none=True),
        )
        response.raise_for_status()

    # ========================================================================
    # Health & Diagnostics
    # ========================================================================

    def health(self) -> bool:
        """Check API health"""
        try:
            response = self.client.get("/health")
            return response.status_code == 200
        except Exception:
            return False


def create_client(
    base_url: str,
    api_key: Optional[str] = None,
    sync: bool = True,
) -> SyncTriageClient | TriageClient:
    """
    Create a configured API client

    Args:
        base_url: Base URL for the API
        api_key: Optional API key for authentication
        sync: If True, returns SyncTriageClient; if False, returns TriageClient

    Returns:
        Configured client instance
    """
    config = TriageClientConfig(base_url=base_url, api_key=api_key)
    if sync:
        return SyncTriageClient(config)
    else:
        return TriageClient(config)
