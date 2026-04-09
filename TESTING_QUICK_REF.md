# Testing Quick Reference

## 🚀 START HERE - Quick Test Commands

### Run All Tests (Windows)
```powershell
.\run-tests.ps1
```

### Run All Tests (Mac/Linux)
```bash
chmod +x run-tests.sh
./run-tests.sh
```

---

## ⚡ 5-Minute Testing

### 1. **Validate Everything (2 min)**
```bash
# Windows
.\run-tests.ps1

# Mac/Linux  
./run-tests.sh
```
✅ Checks all files exist, OpenAPI valid, GraphQL valid

### 2. **Start Mock API Server (1 min)**
```bash
npm install -g @stoplight/prism-cli
prism mock packages/shared/specs/openapi.yaml -p 3000
```
✅ Creates a fake API server based on your spec

### 3. **Test with Curl (2 min)**
```bash
# Create a log
curl -X POST http://localhost:3000/logs \
  -H "Content-Type: application/json" \
  -d '{"message":"test error","severity":"ERROR","source":"test-cli"}'

# List logs
curl http://localhost:3000/logs

# Create incident
curl -X POST http://localhost:3000/incidents \
  -H "Content-Type: application/json" \
  -d '{"title":"Test Incident","severity":"HIGH"}'
```

---

## 🧪 Unit Tests

### TypeScript Tests
```bash
# Install dependencies
npm install -D vitest

# Run tests once
npm test -- packages/shared/test/test-typescript-client.ts

# Watch mode (re-runs on changes)
npm test -- --watch packages/shared/test/test-typescript-client.ts

# With coverage
npm test -- --coverage packages/shared/test/test-typescript-client.ts
```

### Python Tests
```bash
# Install dependencies
pip install pytest pytest-asyncio pytest-cov httpx pydantic

# Run all tests
pytest apps/api/test/test_python_client.py -v

# Run specific test class
pytest apps/api/test/test_python_client.py::TestSyncLogsAPI -v

# With coverage report
pytest apps/api/test/test_python_client.py --cov=api.client --cov-report=html

# View coverage report
open htmlcov/index.html  # Mac
start htmlcov/index.html # Windows
```

---

## 👀 Manual Testing

### Test TypeScript Client in Node
```bash
cat > test-client.js << 'EOF'
import { createTriageClient, LogSeverity } from './packages/shared/src/api/client.ts'

const client = createTriageClient({
  baseURL: 'http://localhost:3000',
})

// Type-check this works
const log = await client.createLog({
  message: 'Test',
  severity: LogSeverity.ERROR,
  source: 'test'
})

console.log('✅ Created log:', log.data.id)
EOF

npx tsx test-client.js
```

### Test Python Client in Python Shell
```bash
python3 << 'EOF'
from apps.api.src.client import create_client
from apps.api.src.types import CreateLogRequest, LogSeverity

client = create_client("http://localhost:3000", sync=True)

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

---

## 📊 Validate Specs

### OpenAPI Validation
```bash
# Using Spectral (recommended)
npm install -D @stoplight/spectral-cli
npx spectral lint packages/shared/specs/openapi.yaml

# View in browser (Swagger UI)
docker run -p 8081:8080 \
  -e SWAGGER_JSON=/specs/openapi.yaml \
  -v $(pwd)/packages/shared/specs:/specs \
  swaggerapi/swagger-ui
# Visit http://localhost:8081
```

### GraphQL Validation
```bash
# Install tools
npm install -D graphql

# Create simple validation script
cat > validate-graphql.js << 'EOF'
const fs = require('fs')
const { buildSchema } = require('graphql')

const schemaString = fs.readFileSync('packages/shared/specs/schema.graphql', 'utf8')
try {
  buildSchema(schemaString)
  console.log('✅ GraphQL schema is valid!')
} catch (error) {
  console.error('❌ GraphQL schema error:', error.message)
}
EOF

node validate-graphql.js
```

---

## 🔗 Integration Testing

### Full Flow Test (using mock server and client)
```bash
# Terminal 1: Start mock server
prism mock packages/shared/specs/openapi.yaml -p 3000

# Terminal 2: Run full flow
npm install -g load-test  # Optional for load testing

cat > test-flow.js << 'EOF'
import { createTriageClient, LogSeverity, IncidentSeverity } from '@my-monorepo/shared'

const client = createTriageClient({
  baseURL: 'http://localhost:3000',
})

try {
  // 1. Create log
  const log = await client.createLog({
    message: 'Database timeout',
    severity: LogSeverity.ERROR,
    source: 'api-service',
  })
  console.log('✅ Created log:', log.data.id)

  // 2. Create incident
  const incident = await client.createIncident({
    title: 'Database Connection Issues',
    severity: IncidentSeverity.HIGH,
  })
  console.log('✅ Created incident:', incident.data.id)

  // 3. Run triage
  const triage = await client.triageIncident({
    incident_id: incident.data.id,
    log_ids: [log.data.id],
  })
  console.log('✅ Triage complete:', triage.data.root_cause_hypotheses.length, 'hypotheses')

} catch (error) {
  console.error('❌ Error:', error)
}
EOF

npx tsx test-flow.js
```

---

## 📋 Testing Checklist

- [ ] Run `./run-tests.ps1` or `./run-tests.sh`
- [ ] All files exist and paths are correct
- [ ] OpenAPI spec is valid
- [ ] GraphQL schema is valid  
- [ ] TypeScript compiles without errors
- [ ] Python types are importable
- [ ] Unit tests pass (npm test + pytest)
- [ ] Mock server starts without errors
- [ ] Can create logs via API
- [ ] Can create incidents via API
- [ ] Can run triage via API

---

## 🐛 Debugging

### If tests fail:

1. **File not found error**
   ```bash
   # Check current directory
   pwd
   
   # Should show path to my-monorepo root
   # If not, cd to the right place
   ```

2. **Module not found (npm)**
   ```bash
   npm install
   ```

3. **Module not found (Python)**
   ```bash
   pip install pytest pytest-asyncio pytest-cov httpx pydantic
   ```

4. **Type errors in TypeScript**
   ```bash
   npx tsc --noEmit packages/shared/src/
   ```

5. **Type errors in Python**
   ```bash
   pip install mypy
   mypy apps/api/src/
   ```

---

## 📖 Documentation

- **Full Testing Guide**: [TESTING_GUIDE.md](../TESTING_GUIDE.md)
- **API Specification**: [API_SPEC.md](../packages/shared/API_SPEC.md)
- **Code Examples**: [examples.py](../packages/shared/examples.py)

---

## ✅ What You Should See

### Successful Test Run Output

```
✅ Package Structure
✅ All files present

✅ OpenAPI Specification  
✓ GET /logs endpoint defined
✓ POST /incidents endpoint defined
✓ POST /triage endpoint defined

✅ GraphQL Schema
✓ Query type defined
✓ Mutation type defined
✓ Incident type defined

✅ TypeScript Types and Client
✓ LogSeverity enum exported
✓ IncidentStatus enum exported
✓ TriageClient class exported

✅ Python Types and Client
✓ Python types importable
✓ TriageClient class defined
✓ SyncTriageClient class defined

✓ Unit test files exist
✓ Documentation exists

╔════════════════════════════════════════════════════════════╗
║  ✅ ALL TESTS PASSED!                                     ║
╚════════════════════════════════════════════════════════════╝
```

Ready for next prompts! 🚀
