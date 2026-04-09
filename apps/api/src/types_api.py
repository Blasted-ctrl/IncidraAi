"""
Incident Triage API - Python Types
Auto-generated from OpenAPI specification
Uses Pydantic v2 for validation and serialization
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field


# ============================================================================
# Enums
# ============================================================================


class LogSeverity(str, Enum):
    """Log severity levels"""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class IncidentStatus(str, Enum):
    """Incident status values"""

    OPEN = "OPEN"
    INVESTIGATING = "INVESTIGATING"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"


class IncidentSeverity(str, Enum):
    """Incident severity levels"""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class RiskLevel(str, Enum):
    """Risk level for mitigation steps"""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class TimelineEventType(str, Enum):
    """Types of events in incident timeline"""

    STATUS_CHANGE = "STATUS_CHANGE"
    ASSIGNMENT = "ASSIGNMENT"
    TRIAGE = "TRIAGE"
    COMMENT = "COMMENT"
    RESOLUTION = "RESOLUTION"


class IncidentSortBy(str, Enum):
    """Incident sorting options"""

    CREATED_AT = "created_at"
    UPDATED_AT = "updated_at"
    SEVERITY = "severity"


# ============================================================================
# Log Models
# ============================================================================


class Log(BaseModel):
    """Log entry with tracing information"""

    id: UUID
    message: str
    severity: LogSeverity
    timestamp: datetime
    source: str = Field(description="Service or component that generated the log")
    trace_id: Optional[UUID] = Field(None, description="Trace ID for distributed tracing")
    span_id: Optional[UUID] = Field(None, description="Span ID for distributed tracing")
    metadata: Optional[dict[str, Any]] = Field(
        None, description="Custom metadata associated with the log"
    )

    class Config:
        use_enum_values = False


class LogDetail(Log):
    """Detailed log information with relationships"""

    cluster_id: Optional[UUID] = None
    incident_ids: list[UUID] = Field(default_factory=list)
    related_logs: list[Log] = Field(default_factory=list)


class LogList(BaseModel):
    """Paginated log results"""

    items: list[Log] = Field(description="List of logs")
    total: int = Field(description="Total number of logs")
    limit: int = Field(description="Limit used in query")
    offset: int = Field(description="Offset used in query")


class CreateLogRequest(BaseModel):
    """Request to create a new log"""

    message: str
    severity: LogSeverity
    source: str
    trace_id: Optional[UUID] = None
    span_id: Optional[UUID] = None
    metadata: Optional[dict[str, Any]] = None

    class Config:
        use_enum_values = False


# ============================================================================
# Cluster Models
# ============================================================================


class Cluster(BaseModel):
    """Log cluster grouping similar logs"""

    id: UUID
    name: str
    description: Optional[str] = None
    log_count: int = Field(description="Number of logs in this cluster")
    created_at: datetime
    severity: IncidentSeverity

    class Config:
        use_enum_values = False


# ============================================================================
# Incident Models
# ============================================================================


class Incident(BaseModel):
    """Incident in the system"""

    id: UUID
    title: str
    description: Optional[str] = None
    status: IncidentStatus
    severity: IncidentSeverity
    created_at: datetime
    updated_at: datetime
    resolved_at: Optional[datetime] = None
    assigned_to: Optional[str] = None
    cluster_ids: list[UUID] = Field(default_factory=list)

    class Config:
        use_enum_values = False


class IncidentDetail(Incident):
    """Detailed incident information with relationships"""

    logs: list[Log] = Field(default_factory=list)
    triage_results: list["TriageResult"] = Field(default_factory=list)
    timeline: list["TimelineEvent"] = Field(default_factory=list)


class IncidentList(BaseModel):
    """Paginated incident results"""

    items: list[Incident] = Field(description="List of incidents")
    total: int = Field(description="Total number of incidents")
    limit: int = Field(description="Limit used in query")
    offset: int = Field(description="Offset used in query")


class CreateIncidentRequest(BaseModel):
    """Request to create a new incident"""

    title: str = Field(min_length=1, max_length=200)
    description: Optional[str] = None
    severity: IncidentSeverity
    cluster_ids: Optional[list[UUID]] = Field(default_factory=list)

    class Config:
        use_enum_values = False


class UpdateIncidentRequest(BaseModel):
    """Request to update an incident"""

    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    status: Optional[IncidentStatus] = None
    severity: Optional[IncidentSeverity] = None
    assigned_to: Optional[str] = None

    class Config:
        use_enum_values = False


class TimelineEvent(BaseModel):
    """Event in the incident timeline"""

    id: UUID
    timestamp: datetime
    event_type: TimelineEventType
    actor: Optional[str] = Field(None, description="User who performed the action")
    details: Optional[dict[str, Any]] = Field(None, description="Additional event details")

    class Config:
        use_enum_values = False


# ============================================================================
# Triage Models
# ============================================================================


class Runbook(BaseModel):
    """Runbook reference"""

    id: UUID
    title: str
    url: str


class SimilarIncident(BaseModel):
    """Reference to a similar past incident"""

    id: UUID
    title: str
    resolution: str


class RootCauseHypothesis(BaseModel):
    """Root cause hypothesis generated by AI triage"""

    id: UUID
    hypothesis: str = Field(description="Detailed root cause hypothesis")
    confidence: float = Field(
        description="Confidence score between 0 and 1", ge=0, le=1
    )
    supporting_logs: list[UUID] = Field(default_factory=list)
    relevant_runbooks: list[Runbook] = Field(default_factory=list)
    similar_incidents: list[SimilarIncident] = Field(default_factory=list)


class MitigationStep(BaseModel):
    """Mitigation step suggested by triage"""

    id: UUID
    step: str = Field(description="The action to take")
    order: int = Field(description="Order to execute this step")
    estimated_time_minutes: Optional[int] = Field(
        None, description="Estimated time to complete in minutes"
    )
    risk_level: RiskLevel
    automation_possible: bool = Field(description="Whether this step can be automated")

    class Config:
        use_enum_values = False


class TriageRequest(BaseModel):
    """Request to run AI triage"""

    incident_id: UUID = Field(description="ID of the incident to triage")
    log_ids: list[UUID] = Field(
        min_length=1, description="IDs of logs to analyze"
    )
    context: Optional[dict[str, Any]] = Field(
        None, description="Additional context for triage"
    )


class TriageResult(BaseModel):
    """Triage result with AI analysis"""

    id: UUID
    incident_id: UUID
    created_at: datetime
    completed_at: datetime
    root_cause_hypotheses: list[RootCauseHypothesis] = Field(
        description="Root cause hypotheses ranked by confidence"
    )
    mitigation_steps: list[MitigationStep] = Field(
        description="Suggested mitigation steps"
    )
    summary: str = Field(description="Executive summary of triage results")
    confidence_score: float = Field(
        description="Overall confidence score for this triage", ge=0, le=1
    )
    model_version: str = Field(description="Version of the AI model")


class TriageFeedback(BaseModel):
    """Feedback on triage result"""

    correct_hypothesis: Optional[UUID] = Field(
        None, description="The hypothesis that was correct (if any)"
    )
    actual_root_cause: Optional[str] = Field(
        None, description="Actual root cause if different from hypotheses"
    )
    helpful_steps: list[UUID] = Field(
        description="Mitigation steps that were helpful"
    )
    resolution_time_minutes: Optional[int] = Field(
        None, description="Time taken to resolve in minutes"
    )
    comment: Optional[str] = Field(None, description="Additional comments")


# ============================================================================
# Error Model
# ============================================================================


class APIError(BaseModel):
    """API error response"""

    code: str
    message: str
    details: Optional[dict[str, Any]] = None


# ============================================================================
# Update forward references for circular dependencies
# ============================================================================

IncidentDetail.model_rebuild()
TriageResult.model_rebuild()
