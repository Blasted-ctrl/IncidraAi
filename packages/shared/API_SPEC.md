# Incident Triage API - Specifications & Clients

Complete OpenAPI spec, GraphQL schema, and typed clients for the AI-assisted incident triage system.

## 📋 Contents

This package includes three main components:

1. **OpenAPI Specification** (`specs/openapi.yaml`) - REST API definition
2. **GraphQL Schema** (`specs/schema.graphql`) - GraphQL API definition
3. **Typed Clients** - Auto-generated clients for TypeScript and Python

## 🚀 Quick Start

### TypeScript/Next.js

```typescript
import { createTriageClient, setDefaultClient } from "@my-monorepo/shared";

// Initialize client
const client = createTriageClient({
  baseURL: "http://localhost:8000",
  apiKey: process.env.API_KEY,
});

setDefaultClient(client);

// Use convenience functions
const incidents = await listIncidents({
  status: "OPEN",
  severity: "CRITICAL",
});

// Or use client methods
const result = await client.triageIncident({
  incident_id: incidentId,
  log_ids: logIds,
});
```

### Python

```python
from api.client import create_client
from api.types import CreateIncidentRequest, IncidentSeverity

# Sync client
client = create_client("http://localhost:8000", api_key="your-key")

incident = client.create_incident(
    CreateIncidentRequest(
        title="Database Connection Failed",
        severity=IncidentSeverity.CRITICAL,
    )
)

# Async client
import asyncio
async_client = create_client("http://localhost:8000", sync=False)
async with async_client as client:
    incidents = await client.list_incidents(limit=50)
```

## 📚 API Endpoints

### Logs
- `GET /logs` - List logs with filtering
- `GET /logs/{logId}` - Get log details
- `POST /logs` - Create new log

### Incidents
- `GET /incidents` - List incidents with filtering and sorting
- `GET /incidents/{incidentId}` - Get incident details
- `POST /incidents` - Create new incident
- `PATCH /incidents/{incidentId}` - Update incident

### Triage
- `POST /triage` - Run AI triage analysis
- `GET /triage/{triageId}` - Get triage result
- `POST /triage/{triageId}/feedback` - Submit feedback on triage

## 🎯 Core Models

### Log
```typescript
interface Log {
  id: UUID;
  message: string;
  severity: LogSeverity; // DEBUG, INFO, WARNING, ERROR, CRITICAL
  timestamp: DateTime;
  source: string; // Service that generated the log
  trace_id?: UUID;
  span_id?: UUID;
  metadata?: Record<string, any>;
}
```

### Incident
```typescript
interface Incident {
  id: UUID;
  title: string;
  description?: string;
  status: IncidentStatus; // OPEN, INVESTIGATING, RESOLVED, CLOSED
  severity: IncidentSeverity; // LOW, MEDIUM, HIGH, CRITICAL
  created_at: DateTime;
  updated_at: DateTime;
  resolved_at?: DateTime;
  assigned_to?: string;
  cluster_ids: UUID[];
}
```

### TriageResult
```typescript
interface TriageResult {
  id: UUID;
  incident_id: UUID;
  created_at: DateTime;
  completed_at: DateTime;
  root_cause_hypotheses: RootCauseHypothesis[];
  mitigation_steps: MitigationStep[];
  summary: string;
  confidence_score: number; // 0-1
  model_version: string;
}

interface RootCauseHypothesis {
  id: UUID;
  hypothesis: string;
  confidence: number; // 0-1
  supporting_logs: UUID[];
  relevant_runbooks: Runbook[];
  similar_incidents: SimilarIncident[];
}

interface MitigationStep {
  id: UUID;
  step: string;
  order: number;
  estimated_time_minutes?: number;
  risk_level: RiskLevel; // LOW, MEDIUM, HIGH
  automation_possible: boolean;
}
```

### Cluster
```typescript
interface Cluster {
  id: UUID;
  name: string;
  description?: string;
  log_count: number;
  created_at: DateTime;
  severity: IncidentSeverity;
}
```

## 🔍 GraphQL Queries

### List Incidents with Clusters and Triage

```graphql
query GetIncidents {
  incidents(limit: 20, status: OPEN, severity: CRITICAL) {
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
      }
      triageResults {
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
    total
  }
}
```

### Search Logs and Incidents

```graphql
query Search {
  search(query: "database timeout", types: [LOG, INCIDENT], limit: 50) {
    ... on Log {
      id
      message
      severity
      timestamp
    }
    ... on Incident {
      id
      title
      severity
    }
  }
}
```

### Get Cluster Details

```graphql
query GetCluster {
  cluster(id: "cluster-uuid") {
    id
    name
    logs(limit: 50) {
      items {
        id
        message
        severity
        timestamp
      }
      total
    }
    incidents {
      id
      title
      status
    }
  }
}
```

## 📝 GraphQL Mutations

### Create Incident and Run Triage

```graphql
mutation TriageIncident {
  createIncident(input: {
    title: "High Error Rate",
    severity: CRITICAL,
    description: "Error rate jumped to 5%"
  }) {
    id
    title
  }

  triageIncident(input: {
    incidentId: "incident-uuid"
    logIds: ["log-1", "log-2", "log-3"]
    context: {
      deploymentVersion: "1.2.3"
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
    }
  }
}
```

### Submit Triage Feedback

```graphql
mutation ProvideFeedback {
  submitTriageFeedback(
    triageId: "triage-uuid"
    input: {
      correctHypothesisId: "hypothesis-uuid"
      helpfulStepIds: ["step-1", "step-2"]
      resolutionTimeMinutes: 45
      comment: "This diagnosis was very accurate"
    }
  ) {
    id
    feedback {
      correctHypothesis {
        hypothesis
        confidence
      }
    }
  }
}
```

## 🔧 Configuration

### Environment Variables

```bash
# API Configuration
TRIAGE_API_URL=http://localhost:8000
TRIAGE_API_KEY=your-secret-key

# Client Configuration (TypeScript)
NEXT_PUBLIC_TRIAGE_API_URL=http://localhost:8000
```

### TypeScript Setup

```typescript
// lib/triage-client.ts
import { createTriageClient, setDefaultClient } from "@my-monorepo/shared";

export function initializeTriageClient() {
  const client = createTriageClient({
    baseURL: process.env.NEXT_PUBLIC_TRIAGE_API_URL || "http://localhost:8000",
    apiKey: process.env.TRIAGE_API_KEY,
  });

  setDefaultClient(client);
  return client;
}

// Use in your app
export async function getIncidents() {
  const response = await listIncidents({ limit: 50 });
  return response.data;
}
```

### Python Setup

```python
# config.py
from api.client import SyncTriageClient, TriageClientConfig

TRIAGE_CONFIG = TriageClientConfig(
    base_url=os.getenv("TRIAGE_API_URL", "http://localhost:8000"),
    api_key=os.getenv("TRIAGE_API_KEY"),
    timeout=30.0,
)

# Use in your routes
client = SyncTriageClient(TRIAGE_CONFIG)
incidents = client.list_incidents()
```

## 🧪 Testing

### TypeScript
```typescript
import { vi } from "vitest";
import * as triageClient from "@my-monorepo/shared";

// Mock the client
vi.mock("@my-monorepo/shared", () => ({
  triageClient: {
    listIncidents: vi.fn(),
    createIncident: vi.fn(),
  },
}));

// Test with mocked responses
it("loads incidents", async () => {
  vi.spyOn(triageClient, "listIncidents").mockResolvedValue({
    data: {
      items: [/* mock incidents */],
      total: 1,
    },
  });

  const response = await triageClient.listIncidents();
  expect(response.data.items).toHaveLength(1);
});
```

### Python
```python
from unittest.mock import Mock, patch
from api.client import SyncTriageClient
from api.types import IncidentList

def test_list_incidents():
    client = SyncTriageClient(mock_config)
    
    with patch.object(client.client, "get") as mock_get:
        mock_response = Mock()
        mock_response.json.return_value = {
            "items": [],
            "total": 0,
            "limit": 50,
            "offset": 0,
        }
        mock_get.return_value = mock_response
        
        result = client.list_incidents()
        assert isinstance(result, IncidentList)
```

## 📖 OpenAPI Tools

The OpenAPI spec can be used with various tools:

```bash
# Generate Swagger UI documentation
docker run -p 8080:8080 -e SWAGGER_JSON=/openapi.yaml \
  -v $(pwd)/specs/openapi.yaml:/openapi.yaml \
  swaggerapi/swagger-ui

# Generate client code
openapi-generator-cli generate \
  -i specs/openapi.yaml \
  -g python \
  -o generated/python-client

# Validate spec
npx @stoplight/spectral-cli lint specs/openapi.yaml
```

## 🎁 Enums & Constants

### LogSeverity
- `DEBUG` - Debug level logs
- `INFO` - Informational messages
- `WARNING` - Warning messages
- `ERROR` - Error messages
- `CRITICAL` - Critical errors

### IncidentStatus
- `OPEN` - Incident is open and not being actively investigated
- `INVESTIGATING` - Incident is being investigated
- `RESOLVED` - Root cause found and mitigation applied
- `CLOSED` - Incident is closed

### IncidentSeverity
- `LOW` - Low impact incident
- `MEDIUM` - Medium impact incident
- `HIGH` - High impact incident
- `CRITICAL` - Critical incident requiring immediate attention

### RiskLevel
- `LOW` - Low risk mitigation step
- `MEDIUM` - Medium risk mitigation step
- `HIGH` - High risk mitigation step

## 🚨 Error Handling

### TypeScript
```typescript
import { isAPIError } from "@my-monorepo/shared";

try {
  await triageIncident(request);
} catch (error) {
  if (isAPIError(error)) {
    console.error(`API Error [${error.code}]: ${error.message}`);
    console.error("Details:", error.details);
  } else {
    console.error("Unknown error:", error);
  }
}
```

### Python
```python
from httpx import HTTPStatusError
from api.types import APIError

try:
    result = client.triage_incident(request)
except HTTPStatusError as e:
    try:
        error = APIError(**e.response.json())
        print(f"API Error [{error.code}]: {error.message}")
    except:
        print(f"HTTP {e.response.status_code}: {e.response.text}")
```

## 📦 Integration with Stack

- **Frontend**: Next.js + React with TypeScript client
- **Backend**: FastAPI with Python dataclass models
- **Database**: PostgreSQL (via Supabase) for persistence
- **Real-time**: GraphQL subscriptions for live updates
- **Queue**: Celery + Redis for async triage processing
- **Monitoring**: OpenTelemetry + Grafana integration

## 🔗 Related Files

- OpenAPI Spec: [specs/openapi.yaml](specs/openapi.yaml)
- GraphQL Schema: [specs/schema.graphql](specs/schema.graphql)
- TypeScript Types: [src/types/index.ts](src/types/index.ts)
- TypeScript Client: [src/api/client.ts](src/api/client.ts)
- Python Types: [apps/api/src/types.py](apps/api/src/types.py)
- Python Client: [apps/api/src/client.py](apps/api/src/client.py)

## 📄 License

Part of the my-monorepo project.
