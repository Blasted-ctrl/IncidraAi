"""
Usage Examples for Incident Triage API

This file demonstrates how to use the generated TypeScript and Python clients.
"""

# ============================================================================
# Python Examples
# ============================================================================

"""
Installation:
    pip install httpx pydantic

Sync Client Example:
"""
import asyncio
from uuid import uuid4
from apps.api.src.client import create_client, TriageClientConfig, SyncTriageClient
from apps.api.src.types import (
    CreateLogRequest,
    CreateIncidentRequest,
    LogSeverity,
    IncidentSeverity,
    TriageRequest,
)


def sync_example():
    """Example using synchronous client"""
    # Create client
    config = TriageClientConfig(
        base_url="http://localhost:8000",
        api_key="your-api-key-here",
    )
    client = SyncTriageClient(config)

    try:
        # Create a log
        log = client.create_log(
            CreateLogRequest(
                message="Database connection timeout",
                severity=LogSeverity.ERROR,
                source="api-service",
                metadata={"connection_pool": "primary", "timeout_ms": 5000},
            )
        )
        print(f"Created log: {log.id}")

        # List logs
        logs = client.list_logs(limit=10, severity=LogSeverity.ERROR)
        print(f"Found {logs.total} error logs")

        # Create an incident
        incident = client.create_incident(
            CreateIncidentRequest(
                title="Database Connection Issues",
                description="Multiple services experiencing database timeouts",
                severity=IncidentSeverity.HIGH,
            )
        )
        print(f"Created incident: {incident.id}")

        # Get incident details
        incident_detail = client.get_incident(incident.id)
        print(f"Incident status: {incident_detail.status}")

        # Run triage
        triage_result = client.triage_incident(
            TriageRequest(
                incident_id=incident.id,
                log_ids=[log.id],
                context={
                    "deployment": "production",
                    "region": "us-east-1",
                },
            )
        )
        print(f"Triage complete: {triage_result.summary}")
        print(f"Root causes: {len(triage_result.root_cause_hypotheses)}")
        print(f"Mitigation steps: {len(triage_result.mitigation_steps)}")

    finally:
        client.close()


async def async_example():
    """Example using asynchronous client"""
    from apps.api.src.client import TriageClient

    config = TriageClientConfig(
        base_url="http://localhost:8000",
        api_key="your-api-key-here",
    )

    async with TriageClient(config) as client:
        # Create a log
        log = await client.create_log(
            CreateLogRequest(
                message="Service CPU usage spike",
                severity=LogSeverity.WARNING,
                source="monitoring-service",
            )
        )
        print(f"Created log: {log.id}")

        # List incidents
        incidents = await client.list_incidents(limit=50)
        print(f"Total incidents: {incidents.total}")

        # Get triage result
        if incidents.items:
            first_incident = incidents.items[0]
            details = await client.get_incident(first_incident.id)
            if details.triage_results:
                triage = details.triage_results[0]
                print(f"Top hypothesis: {triage.root_cause_hypotheses[0].hypothesis}")


# ============================================================================
# TypeScript Examples
# ============================================================================

"""
Installation:
    npm install

TypeScript Client Example (Next.js):
"""

# ============================================================================
# GraphQL Example Queries
# ============================================================================

"""
Get incidents with their clusters and triage results:

query GetIncidentsWithDetails {
  incidents(limit: 20, status: OPEN) {
    items {
      id
      title
      severity
      status
      createdAt
      clusters {
        id
        name
        logCount
        severity
      }
      triageResults {
        id
        summary
        confidenceScore
        rootCauseHypotheses {
          hypothesis
          confidence
          supportingLogs {
            message
            severity
            timestamp
          }
        }
        mitigationSteps {
          step
          order
          riskLevel
          automationPossible
        }
      }
    }
  }
}
"""

# ============================================================================
# GraphQL Example Mutations
# ============================================================================

"""
Create incident and run triage:

mutation TriageNewIncident {
  createIncident(input: {
    title: "High error rate detected",
    severity: CRITICAL,
    description: "Error rate jumped from 0.1% to 5% in last 5 minutes"
  }) {
    id
    title
  }
  
  triageIncident(input: {
    incidentId: "..."
    logIds: ["...", "..."]
    context: {
      deploymentVersion: "1.2.3",
      affectedServices: ["api", "worker"]
    }
  }) {
    id
    summary
    confidenceScore
    rootCauseHypotheses {
      hypothesis
      confidence
    }
    mitigationSteps {
      step
      order
      automationPossible
    }
  }
}
"""


if __name__ == "__main__":
    # Run synchronous example
    sync_example()

    # Run asynchronous example
    asyncio.run(async_example())
