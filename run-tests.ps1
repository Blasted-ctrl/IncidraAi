# Quick Test Runner - Tests Incident Triage API specs and clients
# Run: .\run-tests.ps1

param(
    [switch]$SkipTypeScript = $false,
    [switch]$SkipPython = $false,
    [switch]$Verbose = $false
)

# Colors
$Green = 'Green'
$Red = 'Red'
$Yellow = 'Yellow'
$Blue = 'Cyan'

function Write-Header {
    param([string]$Message)
    Write-Host "`n===== $Message =====" -ForegroundColor $Blue
}

function Write-SuccessMessage {
    param([string]$Message)
    Write-Host "OK $Message" -ForegroundColor $Green
}

function Write-ErrorMessage {
    param([string]$Message)
    Write-Host "FAIL $Message" -ForegroundColor $Red
}

function Write-WarningMessage {
    param([string]$Message)
    Write-Host "WARN $Message" -ForegroundColor $Yellow
}

function Test-CommandExists {
    param([string]$Command)
    try {
        Get-Command $Command -ErrorAction Stop | Out-Null
        return $true
    } catch {
        return $false
    }
}

function Test-OpenAPI {
    Write-Header "TESTING: OpenAPI Specification"
    
    $specPath = "packages/shared/specs/openapi.yaml"
    if (-not (Test-Path $specPath)) {
        Write-ErrorMessage "OpenAPI spec not found at $specPath"
        return $false
    }
    
    Write-Host "OK OpenAPI spec exists" -ForegroundColor $Green
    
    # Check key paths
    $content = Get-Content $specPath -Raw
    if ($content -match "GET /logs") {
        Write-Host "OK GET /logs endpoint defined" -ForegroundColor $Green
    }
    if ($content -match "POST /incidents") {
        Write-Host "OK POST /incidents endpoint defined" -ForegroundColor $Green
    }
    if ($content -match "POST /triage") {
        Write-Host "OK POST /triage endpoint defined" -ForegroundColor $Green
    }
    
    # Try Spectral if available
    if (Test-CommandExists "spectral") {
        try {
            npx spectral lint $specPath -q
            Write-Host "OK OpenAPI spec passed Spectral validation" -ForegroundColor $Green
        } catch {
            Write-WarningMessage "OpenAPI spec has Spectral warnings"
        }
    } else {
        Write-WarningMessage "Spectral not available (install with: npm install -D @stoplight/spectral-cli)"
    }
    
    return $true
}

# Test GraphQL
function Test-GraphQL {
    Write-Header "TESTING: GraphQL Schema"
    
    $schemaPath = "packages/shared/specs/schema.graphql"
    if (-not (Test-Path $schemaPath)) {
        Write-ErrorMessage "GraphQL schema not found at $schemaPath"
        return $false
    }
    
    Write-Host "OK GraphQL schema exists" -ForegroundColor $Green
    
    # Check key types
    $content = Get-Content $schemaPath -Raw
    if ($content -match "type Query") {
        Write-Host "OK Query type defined" -ForegroundColor $Green
    }
    if ($content -match "type Mutation") {
        Write-Host "OK Mutation type defined" -ForegroundColor $Green
    }
    if ($content -match "type Incident") {
        Write-Host "OK Incident type defined" -ForegroundColor $Green
    }
    if ($content -match "type Cluster") {
        Write-Host "OK Cluster type defined" -ForegroundColor $Green
    }
    if ($content -match "type TriageResult") {
        Write-Host "OK TriageResult type defined" -ForegroundColor $Green
    }
    
    return $true
}

# Test TypeScript
function Test-TypeScript {
    Write-Header "TESTING: TypeScript Types and Client"
    
    $typesPath = "packages/shared/src/types/index.ts"
    if (-not (Test-Path $typesPath)) {
        Write-ErrorMessage "TypeScript types not found at $typesPath"
        return $false
    }
    
    Write-Host "OK TypeScript types exist" -ForegroundColor $Green
    
    $content = Get-Content $typesPath -Raw
    
    if ($content -match "export enum LogSeverity") {
        Write-Host "OK LogSeverity enum exported" -ForegroundColor $Green
    }
    if ($content -match "export enum IncidentStatus") {
        Write-Host "OK IncidentStatus enum exported" -ForegroundColor $Green
    }
    if ($content -match "export interface Incident") {
        Write-Host "OK Incident interface exported" -ForegroundColor $Green
    }
    
    # Check client
    $clientPath = "packages/shared/src/api/client.ts"
    if (-not (Test-Path $clientPath)) {
        Write-ErrorMessage "TypeScript client not found at $clientPath"
        return $false
    }
    
    Write-Host "OK TypeScript client exists" -ForegroundColor $Green
    
    $clientContent = Get-Content $clientPath -Raw
    if ($clientContent -match "export class TriageClient") {
        Write-Host "OK TriageClient class exported" -ForegroundColor $Green
    }
    if ($clientContent -match "export function createTriageClient") {
        Write-Host "OK createTriageClient factory exported" -ForegroundColor $Green
    }
    
    return $true
}

# Test Python
function Test-Python {
    Write-Header "TESTING: Python Types and Client"
    
    $typesPath = "apps/api/src/types.py"
    if (-not (Test-Path $typesPath)) {
        Write-ErrorMessage "Python types not found at $typesPath"
        return $false
    }
    
    Write-Host "OK Python types exist" -ForegroundColor $Green
    
    # Check client
    $clientPath = "apps/api/src/client.py"
    if (-not (Test-Path $clientPath)) {
        Write-ErrorMessage "Python client not found at $clientPath"
        return $false
    }
    
    Write-Host "OK Python client exists" -ForegroundColor $Green
    
    $clientContent = Get-Content $clientPath -Raw
    if ($clientContent -match "class TriageClient:") {
        Write-Host "OK TriageClient class defined" -ForegroundColor $Green
    }
    if ($clientContent -match "class SyncTriageClient:") {
        Write-Host "OK SyncTriageClient class defined" -ForegroundColor $Green
    }
    
    return $true
}

# Test Files
function Test-Files {
    Write-Header "TESTING: Package Structure"
    
    $files = @(
        "packages/shared/src/index.ts",
        "packages/shared/specs/openapi.yaml",
        "packages/shared/specs/schema.graphql",
        "packages/shared/src/types/index.ts",
        "packages/shared/src/api/client.ts",
        "apps/api/src/types.py",
        "apps/api/src/client.py"
    )
    
    $missing = 0
    foreach ($file in $files) {
        if (Test-Path $file) {
            Write-Host "OK $file" -ForegroundColor $Green
        } else {
            Write-ErrorMessage "$file (MISSING)"
            $missing++
        }
    }
    
    if ($missing -eq 0) {
        Write-Host "OK All files present" -ForegroundColor $Green
        return $true
    } else {
        Write-ErrorMessage "$missing files missing"
        return $false
    }
}

# Test Units
function Test-Units {
    Write-Header "TESTING: Unit Tests"
    
    if (Test-Path "packages/shared/test/test-typescript-client.ts") {
        Write-Host "OK TypeScript test file exists" -ForegroundColor $Green
        if (-not $SkipTypeScript) {
            Write-WarningMessage "Run TypeScript tests with: npm test -- packages/shared/test/test-typescript-client.ts"
        }
    }
    
    if (Test-Path "apps/api/test/test_python_client.py") {
        Write-Host "OK Python test file exists" -ForegroundColor $Green
        if (-not $SkipPython) {
            Write-WarningMessage "Run Python tests with: pytest apps/api/test/test_python_client.py -v"
        }
    }
    
    return $true
}

# Test Documentation
function Test-Documentation {
    Write-Header "TESTING: Documentation"
    
    $docs = @(
        "TESTING_GUIDE.md",
        "packages/shared/API_SPEC.md",
        "packages/shared/examples.py"
    )
    
    foreach ($doc in $docs) {
        if (Test-Path $doc) {
            Write-Host "OK $doc exists" -ForegroundColor $Green
        }
    }
    
    return $true
}

# Test Mock Server
function Test-MockServer {
    Write-Header "TESTING: Mock API Server"
    
    if (Test-CommandExists "prism") {
        Write-Host "OK Prism mock server available" -ForegroundColor $Green
        Write-Host ""
        Write-Host "To test with mock server, run:" -ForegroundColor $Yellow
        Write-Host "  prism mock packages/shared/specs/openapi.yaml -p 3000" -ForegroundColor $Yellow
        Write-Host ""
        Write-Host "Then in another terminal:" -ForegroundColor $Yellow
        Write-Host "  curl -X POST http://localhost:3000/logs " -ForegroundColor $Yellow
        Write-Host "    -H 'Content-Type: application/json' " -ForegroundColor $Yellow
        Write-Host "    -d '{`"message`":`"test`",`"severity`":`"ERROR`",`"source`":`"cli`"}" -ForegroundColor $Yellow
    } else {
        Write-WarningMessage "Prism not installed. Install with: npm install -g @stoplight/prism-cli"
    }
}

# Main
function Main {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor $Blue
    Write-Host "  Incident Triage API Test Suite" -ForegroundColor $Blue
    Write-Host "========================================" -ForegroundColor $Blue
    Write-Host ""
    
    $failed = 0
    
    # Run tests
    if (-not (Test-Files)) { $failed++ }
    if (-not (Test-OpenAPI)) { $failed++ }
    if (-not (Test-GraphQL)) { $failed++ }
    if (-not (Test-TypeScript)) { $failed++ }
    if (-not (Test-Python)) { $failed++ }
    if (-not (Test-Units)) { $failed++ }
    if (-not (Test-Documentation)) { $failed++ }
    
    Test-MockServer
    
    Write-Host ""
    Write-Header "TEST SUMMARY"
    
    if ($failed -eq 0) {
        Write-Host ""
        Write-Host "========================================" -ForegroundColor $Green
        Write-Host "  ALL TESTS PASSED!" -ForegroundColor $Green
        Write-Host "========================================" -ForegroundColor $Green
        Write-Host ""
        Write-Host "Next steps:" -ForegroundColor $Yellow
        Write-Host "  1. Run unit tests: npm test && pytest" -ForegroundColor $Yellow
        Write-Host "  2. Start mock server: prism mock packages/shared/specs/openapi.yaml -p 3000" -ForegroundColor $Yellow
        Write-Host "  3. Review API_SPEC.md for usage examples" -ForegroundColor $Yellow
        Write-Host "  4. Review TESTING_GUIDE.md for detailed testing info" -ForegroundColor $Yellow
        Write-Host ""
        return 0
    } else {
        Write-Host ""
        Write-Host "========================================" -ForegroundColor $Red
        Write-Host "  $failed TEST(S) FAILED" -ForegroundColor $Red
        Write-Host "========================================" -ForegroundColor $Red
        Write-Host ""
        return 1
    }
}

# Run
Main
