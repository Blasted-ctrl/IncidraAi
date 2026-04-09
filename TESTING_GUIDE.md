# Testing Guide - Incident Triage API

Complete testing strategies for OpenAPI specs, GraphQL schema, TypeScript client, and Python client.

## 📋 Quick Testing Checklist

- [ ] Validate OpenAPI spec syntax
- [ ] View OpenAPI with Swagger UI
- [ ] Validate GraphQL schema syntax
- [ ] Test TypeScript client unit tests
- [ ] Test Python client unit tests
- [ ] Run integration tests against mock server
- [ ] Test with real API server

---

## OpenAPI Specification Testing

### 1. Validate OpenAPI Syntax

**Using Spectral (Recommended)**
```bash
# Install Spectral
npm install -D @stoplight/spectral-cli

# Validate spec
npx spectral lint packages/shared/specs/openapi.yaml
```

**Using Swagger CLI**
```bash
# Install
npm install -g swagger-cli

# Validate
swagger-cli validate packages/shared/specs/openapi.yaml
```

**Online Validators**
- [OpenAPI.Tools](https://openapi.tools/)
- [Stoplight Studio](https://stoplight.io/studio/)

### 2. View OpenAPI with Swagger UI

**Docker Option (easiest)**
```bash
docker run -p 8081:8080 \
  -e SWAGGER_JSON=/specs/openapi.yaml \
  -v $(pwd)/packages/shared/specs:/specs \
  swaggerapi/swagger-ui
```
Visit: http://localhost:8081

**npm Option**
```bash
npm install -g swagger-ui-express

# Create simple server
cat > swagger-server.js << 'EOF'
const express = require('express');
const serveStatic = require('serve-static');
const path = require('path');

const app = express();
app.use(serveStatic(path.join(__dirname, 'packages/shared/specs')));
app.listen(8081, () => console.log('Swagger UI at http://localhost:8081'));
EOF

node swagger-server.js
```

### 3. Generate OpenAPI Report

```bash
# Using Swagger Stats
npm install swagger-stats

# Or generate HTML report
npx swagger-cli bundle packages/shared/specs/openapi.yaml -o openapi-bundle.yaml
```

### 4. Test OpenAPI Against Mock Data

```bash
# Using Prism for mock server
npm install -g @stoplight/prism-cli

# Start mock server based on OpenAPI spec
prism mock packages/shared/specs/openapi.yaml -p 3000
```

Then test with curl:
```bash
# Create a log
curl -X POST http://localhost:3000/logs \
  -H "Content-Type: application/json" \
  -d '{"message":"test","severity":"ERROR","source":"cli"}'

# List logs
curl http://localhost:3000/logs

# Create incident
curl -X POST http://localhost:3000/incidents \
  -H "Content-Type: application/json" \
  -d '{"title":"Test","severity":"HIGH"}'
```

---

## 📊 GraphQL Schema Testing

### 1. Validate GraphQL Schema

```bash
# Using GraphQL Tools
npm install -D graphql graphql-schema-linter

# Validate
npx graphql-schema-linter packages/shared/specs/schema.graphql
```

### 2. GraphQL Playground / Apollo Studio

**Option 1: Using GraphQL Playground Desktop**
```bash
npm install -g graphql-playground-electron
graphql-playground
# Open: packages/shared/specs/schema.graphql
```

**Option 2: Apollo Sandbox (Online)**
```bash
# Upload GraphQL schema to Apollo Sandbox
# https://www.apollographql.com/docs/studio/
```

### 3. Test GraphQL Queries

**Using graphql-cli**
```bash
npm install -g graphql-cli

cat > .graphqlconfig.yml << 'EOF'
projects:
  triage:
    schema:
      file: packages/shared/specs/schema.graphql
EOF

# Validate query
graphql validate
```

**Manual Query Testing**
```bash
# Test introspection query
cat > test-query.graphql << 'EOF'
query {
  __schema {
    types {
      name
      kind
    }
  }
}
EOF

# Validate schema references types
grep -o "type [A-Za-z]*" packages/shared/specs/schema.graphql | sort -u
```

### 4. Generate TypeScript Types from GraphQL

```bash
# Install GraphQL code generator
npm install -D @graphql-codegen/cli @graphql-codegen/typescript

# Create config
cat > codegen.ts << 'EOF'
import type { CodegenConfig } from '@graphql-codegen/cli'

const config: CodegenConfig = {
  schema: 'packages/shared/specs/schema.graphql',
  generates: {
    'packages/shared/src/graphql/types.ts': {
      plugins: ['typescript'],
    },
  },
}
export default config
EOF

# Generate types
npx graphql-codegen
```

---

## 🧪 TypeScript Client Testing

### 1. Run TypeScript Unit Tests

**Install dependencies**
```bash
npm install -D vitest @vitest/ui ts-node
```

**Run tests**
```bash
# Single run
npm test -- packages/shared/test/test-typescript-client.ts

# Watch mode
npm test -- --watch packages/shared/test/test-typescript-client.ts

# With UI
npm test -- --ui
```

### 2. Test Coverage

```bash
npm test -- --coverage packages/shared/test/test-typescript-client.ts
```

Expected coverage:
- ✅ Client initialization
- ✅ Type guards (UUID, enums)
- ✅ Logs API (list, create, get)
- ✅ Incidents API (list, create, get, update)
- ✅ Triage API (triage, get result, feedback)
- ✅ Error handling

### 3. Manual TypeScript Testing

**In Node REPL**
```bash
# Install tsx for running TypeScript
npm install -D tsx

# Create test file
cat > test-client.ts << 'EOF'
import { createTriageClient, LogSeverity, IncidentSeverity } from '@my-monorepo/shared'

const client = createTriageClient({
  baseURL: 'http://localhost:8000',
  apiKey: 'test-key',
})

// Test it type-checks
const logReq = {
  message: 'Test',
  severity: LogSeverity.ERROR,
  source: 'test',
}

console.log('✅ Types are correct!')
EOF

# Run it
npx tsx test-client.ts
```

### 4. Integration Test Against Mock Server

```bash
# Start mock server
npm install -g @stoplight/prism-cli
prism mock packages/shared/specs/openapi.yaml -p 3000 &

# Run integration tests
npm test -- --env=integration

# Or manually with curl
curl -X POST http://localhost:3000/logs \
  -H "Content-Type: application/json" \
  -d '{"message":"test","severity":"ERROR","source":"debug"}'
```

### 5. Type Checking

```bash
# Check for type errors
npx tsc --noEmit packages/shared/src/

# Strict mode
npx tsc --strict --noEmit packages/shared/src/
```

---

## 🐍 Python Client Testing

### 1. Install Test Dependencies

```bash
# Add to pyproject.toml
pip install pytest pytest-asyncio pytest-cov httpx pydantic

# Or install directly
pip install pytest pytest-asyncio pytest-cov httpx pydantic
```

### 2. Run Python Unit Tests

```bash
# All tests
pytest apps/api/test/test_python_client.py -v

# Specific test class
pytest apps/api/test/test_python_client.py::TestSyncLogsAPI -v

# With coverage
pytest apps/api/test/test_python_client.py --cov=api.client --cov-report=html

# Watch mode
pytest-watch apps/api/test/test_python_client.py

# Verbose output
pytest apps/api/test/test_python_client.py -vv -s
```

### 3. Test Coverage Report

```bash
# Generate coverage report
pytest apps/api/test/test_python_client.py \
  --cov=api \
  --cov-report=html \
  --cov-report=term-missing

# View report
open htmlcov/index.html
```

Expected coverage:
- ✅ Client configuration and initialization
- ✅ Logs API (list, create, get)
- ✅ Incidents API (list, create, get, update)
- ✅ Triage API (triage, get result, feedback)
- ✅ Data validation (Pydantic models)
- ✅ Error handling
- ✅ Context managers

### 4. Manual Python Testing

**Interactive Shell**
```bash
python3 << 'EOF'
from api.client import create_client
from api.types import CreateLogRequest, LogSeverity

# Create sync client
client = create_client("http://localhost:8000", sync=True)

# Create a log
log = client.create_log(
    CreateLogRequest(
        message="Test error",
        severity=LogSeverity.ERROR,
        source="python-test"
    )
)

print(f"✅ Created log: {log.id}")
EOF
```

### 5. Async Testing

```bash
python3 << 'EOF'
import asyncio
from api.client import create_client
from api.types import CreateLogRequest, LogSeverity

async def test():
    async with create_client("http://localhost:8000", sync=False) as client:
        logs = await client.list_logs()
        print(f"✅ Listed {logs.total} logs")

asyncio.run(test())
EOF
```

### 6. Type Checking

```bash
# Install mypy
pip install mypy

# Check types
mypy apps/api/src/

# Strict mode
mypy --strict apps/api/src/
```

---

## 🔗 Integration Testing

### 1. Start Mock API Server

```bash
# Using Prism (easiest)
npm install -g @stoplight/prism-cli
prism mock packages/shared/specs/openapi.yaml -p 3000

# Or using mock server from FastAPI
# See mock_server.py below
```

### 2. Test Against Mock Server

**Create test script**
```bash
cat > test-mock-server.sh << 'EOF'
#!/bin/bash

API="http://localhost:3000"

echo "Testing Log Creation..."
LOG_RESPONSE=$(curl -s -X POST "$API/logs" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Test error",
    "severity": "ERROR",
    "source": "test-script"
  }')

LOG_ID=$(echo $LOG_RESPONSE | grep -o '"id":"[^"]*' | cut -d'"' -f4)
echo "✅ Created log: $LOG_ID"

echo "Testing Incident Creation..."
INCIDENT_RESPONSE=$(curl -s -X POST "$API/incidents" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Test Incident",
    "severity": "HIGH"
  }')

INCIDENT_ID=$(echo $INCIDENT_RESPONSE | grep -o '"id":"[^"]*' | cut -d'"' -f4)
echo "✅ Created incident: $INCIDENT_ID"

echo "Testing Triage..."
TRIAGE_RESPONSE=$(curl -s -X POST "$API/triage" \
  -H "Content-Type: application/json" \
  -d "{
    \"incident_id\": \"$INCIDENT_ID\",
    \"log_ids\": [\"$LOG_ID\"]
  }")

echo "✅ Triage result: $(echo $TRIAGE_RESPONSE | grep -o '"summary":"[^"]*')"
EOF

chmod +x test-mock-server.sh
./test-mock-server.sh
```

### 3. Load Testing

```bash
# Using Apache Bench
ab -n 100 -c 10 http://localhost:3000/logs

# Or using k6
npm install -g k6

cat > load-test.js << 'EOF'
import http from 'k6/http'
import { check } from 'k6'

export const options = {
  vus: 10,
  duration: '30s',
}

export default function() {
  const res = http.get('http://localhost:3000/logs')
  check(res, {
    'status is 200': (r) => r.status === 200,
  })
}
EOF

k6 run load-test.js
```

### 4. End-to-End Testing

**TypeScript/Playwright**
```bash
npm install -D @playwright/test

cat > e2e.test.ts << 'EOF'
import { test, expect } from '@playwright/test'
import { createTriageClient } from '@my-monorepo/shared'

test('E2E: Create incident and run triage', async () => {
  const client = createTriageClient({
    baseURL: 'http://localhost:3000',
  })

  // Create log
  const log = await client.createLog({
    message: 'E2E test error',
    severity: 'ERROR',
    source: 'e2e-test',
  })
  expect(log.data.id).toBeDefined()

  // Create incident
  const incident = await client.createIncident({
    title: 'E2E Test Incident',
    severity: 'CRITICAL',
  })
  expect(incident.data.id).toBeDefined()

  // Run triage
  const triage = await client.triageIncident({
    incident_id: incident.data.id,
    log_ids: [log.data.id],
  })
  expect(triage.data.root_cause_hypotheses).toHaveLength(1)
})
EOF

npx playwright test
```

---

## 📝 Testing Checklist

### Before Committing

- [ ] TypeScript types compile without errors
- [ ] Python types pass mypy strict checks
- [ ] All unit tests pass
- [ ] Coverage > 80%
- [ ] Linting passes (ESLint, pylint)
- [ ] OpenAPI spec is valid
- [ ] GraphQL schema is valid

### Before Deploying

- [ ] Integration tests pass against staging API
- [ ] Load tests show acceptable performance
- [ ] Security tests pass (auth, input validation)
- [ ] Documentation is up to date
- [ ] Changelog is updated

---

## 🐛 Debugging

### TypeScript Debugging

```bash
# Add to VS Code launch.json
{
  "type": "node",
  "request": "launch",
  "name": "Debug TypeScript Tests",
  "program": "${workspaceFolder}/node_modules/.bin/vitest",
  "args": ["run", "packages/shared/test/test-typescript-client.ts"],
  "console": "integratedTerminal"
}
```

### Python Debugging

```bash
# Add breakpoint
import pdb; pdb.set_trace()

# Or use VS Code Python debugger
# .vscode/launch.json
{
  "name": "Python: Current File",
  "type": "python",
  "request": "launch",
  "program": "${file}",
  "console": "integratedTerminal"
}
```

### API Debugging

```bash
# Enable verbose logging in Python client
import logging
logging.basicConfig(level=logging.DEBUG)

# In TypeScript, add console logging to client
client.onRequest = (req) => console.log('Request:', req)
client.onResponse = (res) => console.log('Response:', res)
```

---

## 📊 Test Results Summary

When all tests pass, you'll see:

```
✅ TypeScript Client Tests (12/12)
  ✓ Client initialization
  ✓ Type guards
  ✓ Logs API
  ✓ Incidents API
  ✓ Triage API
  ✓ Error handling

✅ Python Client Tests (18/18)
  ✓ Client initialization
  ✓ Sync logs API
  ✓ Sync incidents API
  ✓ Sync triage API
  ✓ Data validation
  ✓ Error handling
  ✓ Context managers

✅ OpenAPI Validation
  ✓ Syntax valid
  ✓ No schema errors
  ✓ All endpoints documented

✅ GraphQL Schema Validation
  ✓ Schema valid
  ✓ All types defined
  ✓ All queries/mutations valid
```

Ready to proceed with more prompts! 🚀
