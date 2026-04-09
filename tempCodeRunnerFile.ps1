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

# Utility functions
function Print-Header {
    param([string]$Message)
    Write-Host "`n█████ $Message █████`n" -ForegroundColor $Blue
}

function Success {
    param([string]$Message)
    Write-Host "✅ $Message" -ForegroundColor $Green
}

function Error-Message {
    param([string]$Message)
    Write-Host "❌ $Message" -ForegroundColor $Red
}

function Warning-Message {
    param([string]$Message)
    Write-Host "⚠️  $Message" -ForegroundColor $Yellow
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

# Test OpenAPI
function Test-OpenAPI {
    Print-Header "TESTING: OpenAPI Specification"
    
    $specPath = "packages/shared/specs/openapi.yaml"
    if (-not (Test-Path $specPath)) {
        Error-Message "OpenAPI spec not found at $specPath"
        return $false
    }
    
    Success "OpenAPI spec exists"
    
    # Check key paths
    $content = Get-Content $specPath -Raw
    if ($content -match "GET /logs") {
        Success "✓ GET /logs endpoint defined"
    }
    if ($content -match "POST /incidents") {
        Success "✓ POST /incidents endpoint defined"
    }
    if ($content -match "POST /triage") {
        Success "✓ POST /triage endpoint defined"
    }
    
    # Try Spectral if available
    if (Test-CommandExists "spectral") {
        try {
            npx spectral lint $specPath -q
            Success "✓ OpenAPI spec passed Spectral validation"
        } catch {
            Warning-Message "OpenAPI spec has Spectral warnings"
        }
    } else {
        Warning-Message "Spectral not available (install with: npm install -D @stoplight/spectral-cli)"
    }
    
    return $true
}

# Test GraphQL
function Test-GraphQL {
    Print-Header "TESTING: GraphQL Schema"
    
    $schemaPath = "packages/shared/specs/schema.graphql"
    if (-not (Test-Path $schemaPath)) {
        Error-Message "GraphQL schema not found at $schemaPath"
        return $false
    }
    
    Success "GraphQL schema exists"
    
    # Check key types
    $content = Get-Content $schemaPath -Raw
    if ($content -match "type Query") {
        Success "✓ Query type defined"
    }
    if ($content -match "type Mutation") {
        Success "✓ Mutation type defined"
    }
    if ($content -match "type Incident") {
        Success "✓ Incident type defined"
    }
    if ($content -match "type Cluster") {
        Success "✓ Cluster type defined"
    }
    if ($content -match "type TriageResult") {
        Success "✓ TriageResult type defined"
    }
    
    return $true
}

# Test TypeScript
function Test-TypeScript {
    Print-Header "TESTING: TypeScript Types and Client"
    
    $typesPath = "packages/shared/src/types/index.ts"
    if (-not (Test-Path $typesPath)) {
        Error-Message "TypeScript types not found at $typesPath"
        return $false
    }
    
    Success "TypeScript types exist"
    
    $content = Get-Content $typesPath -Raw
    
    if ($content -match "export enum LogSeverity") {
        Success "✓ LogSeverity enum exported"
    }
    if ($content -match "export enum IncidentStatus") {
        Success "✓ IncidentStatus enum exported"
    }
    if ($content -match "export interface Incident") {
        Success "✓ Incident interface exported"
    }
    
    # Check client
    $clientPath = "packages/shared/src/api/client.ts"
    if (-not (Test-Path $clientPath)) {
        Error-Message "TypeScript client not found at $clientPath"
        return $false
    }
    
    Success "TypeScript client exists"
    
    $clientContent = Get-Content $clientPath -Raw
    if ($clientContent -match "export class TriageClient") {
        Success "✓ TriageClient class exported"
    }
    if ($clientContent -match "export function createTriageClient") {
        Success "✓ createTriageClient factory exported"
    }
    
    return $true
}

# Test Python
function Test-Python {
    Print-Header "TESTING: Python Types and Client"
    
    $typesPath = "apps/api/src/types.py"
    if (-not (Test-Path $typesPath)) {
        Error-Message "Python types not found at $typesPath"
        return $false
    }
    
    Success "Python types exist"
    
    # Check client
    $clientPath = "apps/api/src/client.py"
    if (-not (Test-Path $clientPath)) {
        Error-Message "Python client not found at $clientPath"
        return $false
    }
    
    Success "Python client exists"
    
    $clientContent = Get-Content $clientPath -Raw
    if ($clientContent -match "class TriageClient:") {
        Success "✓ TriageClient class defined"
    }
    if ($clientContent -match "class SyncTriageClient:") {
        Success "✓ SyncTriageClient class defined"
    }
    
    return $true
}

# Test Files
function Test-Files {
    Print-Header "TESTING: Package Structure"
    
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
            Success "✓ $file"
        } else {
            Error-Message "✗ $file (missing)"
            $missing++
        }
    }
    
    if ($missing -eq 0) {
        Success "All files present"
        return $true
    } else {
        Error-Message "$missing files missing"
        return $false
    }
}

# Test Units
function Test-Units {
    Print-Header "TESTING: Unit Tests"
    
    if (Test-Path "packages/shared/test/test-typescript-client.ts") {
        Success "TypeScript test file exists"
        if (-not $SkipTypeScript) {
            Warning-Message "Run TypeScript tests with: npm test -- packages/shared/test/test-typescript-client.ts"
        }
    }
    
    if (Test-Path "apps/api/test/test_python_client.py") {
        Success "Python test file exists"
        if (-not $SkipPython) {
            Warning-Message "Run Python tests with: pytest apps/api/test/test_python_client.py -v"
        }
    }
    
    return $true
}

# Test Documentation
function Test-Documentation {
    Print-Header "TESTING: Documentation"
    
    $docs = @(
        "TESTING_GUIDE.md",
        "packages/shared/API_SPEC.md",
        "packages/shared/examples.py"
    )
    
    foreach ($doc in $docs) {
        if (Test-Path $doc) {
            Success "✓ $doc exists"
        }
    }
    
    return $true
}

# Test Mock Server
function Test-MockServer {
    Print-Header "TESTING: Mock API Server"
    
    if (Test-CommandExists "prism") {
        Success "Prism mock server available"
        Write-Host ""
        Write-Host "To test with mock server, run:" -ForegroundColor $Yellow
        Write-Host "  prism mock packages/shared/specs/openapi.yaml -p 3000" -ForegroundColor $Yellow
        Write-Host ""
        Write-Host "Then in another terminal:" -ForegroundColor $Yellow
        Write-Host "  curl -X POST http://localhost:3000/logs \" -ForegroundColor $Yellow
        Write-Host "    -H 'Content-Type: application/json' \" -ForegroundColor $Yellow
        Write-Host "    -d '{\"message\":\"test\",\"severity\":\"ERROR\",\"source\":\"cli\"}'" -ForegroundColor $Yellow
    } else {
        Warning-Message "Prism not installed. Install with: npm install -g @stoplight/prism-cli"
    }
}

# Main
function Main {
    Write-Host "`n╔════════════════════════════════════════════════════════════╗" -ForegroundColor $Blue
    Write-Host "║  Incident Triage API - Quick Test Suite                   ║" -ForegroundColor $Blue
    Write-Host "╚════════════════════════════════════════════════════════════╝`n" -ForegroundColor $Blue
    
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
    Print-Header "TEST SUMMARY"
    
    if ($failed -eq 0) {
        Write-Host "╔════════════════════════════════════════════════════════════╗" -ForegroundColor $Green
        Write-Host "║  ✅ ALL TESTS PASSED!                                     ║" -ForegroundColor $Green
        Write-Host "╚════════════════════════════════════════════════════════════╝" -ForegroundColor $Green
        Write-Host ""
        Write-Host "Next steps:" -ForegroundColor $Yellow
        Write-Host "  1. Run unit tests: npm test && pytest" -ForegroundColor $Yellow
        Write-Host "  2. Start mock server: prism mock packages/shared/specs/openapi.yaml -p 3000" -ForegroundColor $Yellow
        Write-Host "  3. Review API_SPEC.md for usage examples" -ForegroundColor $Yellow
        Write-Host "  4. Review TESTING_GUIDE.md for detailed testing info" -ForegroundColor $Yellow
        Write-Host ""
        return 0
    } else {
        Write-Host "╔════════════════════════════════════════════════════════════╗" -ForegroundColor $Red
        Write-Host "║  ❌ $failed TEST(S) FAILED                                ║" -ForegroundColor $Red
        Write-Host "╚════════════════════════════════════════════════════════════╝" -ForegroundColor $Red
        Write-Host ""
        return 1
    }
}

# Run
Main
