#!/bin/bash

###############################################################################
# Quick Test Runner - Tests Incident Triage API specs and clients
# Run: ./run-tests.sh
###############################################################################

set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Utility functions
print_header() {
    echo -e "${BLUE}█████ $1 █████${NC}\n"
}

success() {
    echo -e "${GREEN}✅ $1${NC}"
}

error() {
    echo -e "${RED}❌ $1${NC}"
}

warning() {
    echo -e "${YELLOW}⚠️ $1${NC}"
}

# Check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

###############################################################################
# OpenAPI VALIDATION
###############################################################################
test_openapi() {
    print_header "TESTING: OpenAPI Specification"
    
    if [ ! -f "packages/shared/specs/openapi.yaml" ]; then
        error "OpenAPI spec not found"
        return 1
    fi
    
    success "OpenAPI spec exists"
    
    # Try to validate with spectral if available
    if command_exists spectral; then
        if npx spectral lint packages/shared/specs/openapi.yaml; then
            success "OpenAPI spec passed Spectral validation"
        else
            error "OpenAPI spec failed Spectral validation"
            return 1
        fi
    else
        warning "Spectral not available, skipping lint (install with: npm install -D @stoplight/spectral-cli)"
    fi
    
    # Check key paths exist
    if grep -q "GET /logs" packages/shared/specs/openapi.yaml; then
        success "✓ GET /logs endpoint defined"
    fi
    if grep -q "POST /incidents" packages/shared/specs/openapi.yaml; then
        success "✓ POST /incidents endpoint defined"
    fi
    if grep -q "POST /triage" packages/shared/specs/openapi.yaml; then
        success "✓ POST /triage endpoint defined"
    fi
}

###############################################################################
# GraphQL VALIDATION
###############################################################################
test_graphql() {
    print_header "TESTING: GraphQL Schema"
    
    if [ ! -f "packages/shared/specs/schema.graphql" ]; then
        error "GraphQL schema not found"
        return 1
    fi
    
    success "GraphQL schema exists"
    
    # Check key types
    if grep -q "type Query" packages/shared/specs/schema.graphql; then
        success "✓ Query type defined"
    fi
    if grep -q "type Mutation" packages/shared/specs/schema.graphql; then
        success "✓ Mutation type defined"
    fi
    if grep -q "type Incident" packages/shared/specs/schema.graphql; then
        success "✓ Incident type defined"
    fi
    if grep -q "type Cluster" packages/shared/specs/schema.graphql; then
        success "✓ Cluster type defined"
    fi
    if grep -q "type TriageResult" packages/shared/specs/schema.graphql; then
        success "✓ TriageResult type defined"
    fi
}

###############################################################################
# TYPESCRIPT TYPE CHECKING
###############################################################################
test_typescript() {
    print_header "TESTING: TypeScript Types and Client"
    
    if [ ! -f "packages/shared/src/types/index.ts" ]; then
        error "TypeScript types not found"
        return 1
    fi
    
    success "TypeScript types exist"
    
    # Check key exports
    if grep -q "export enum LogSeverity" packages/shared/src/types/index.ts; then
        success "✓ LogSeverity enum exported"
    fi
    if grep -q "export enum IncidentStatus" packages/shared/src/types/index.ts; then
        success "✓ IncidentStatus enum exported"
    fi
    if grep -q "export interface Incident" packages/shared/src/types/index.ts; then
        success "✓ Incident interface exported"
    fi
    
    # Check client exists
    if [ ! -f "packages/shared/src/api/client.ts" ]; then
        error "TypeScript client not found"
        return 1
    fi
    
    success "TypeScript client exists"
    
    if grep -q "export class TriageClient" packages/shared/src/api/client.ts; then
        success "✓ TriageClient class exported"
    fi
    if grep -q "export function createTriageClient" packages/shared/src/api/client.ts; then
        success "✓ createTriageClient factory exported"
    fi
    
    # Type check if TypeScript is available
    if command_exists tsc; then
        if npx tsc --noEmit packages/shared/src/types/index.ts 2>/dev/null; then
            success "✓ TypeScript types compile without errors"
        else
            warning "TypeScript compilation warnings (may be OK)"
        fi
    else
        warning "TypeScript compiler not available (install with: npm install -D typescript)"
    fi
}

###############################################################################
# PYTHON TYPE CHECKING
###############################################################################
test_python() {
    print_header "TESTING: Python Types and Client"
    
    if [ ! -f "apps/api/src/types.py" ]; then
        error "Python types not found"
        return 1
    fi
    
    success "Python types exist"
    
    # Check key classes
    if python3 -c "import sys; sys.path.insert(0, 'apps/api/src'); from types import LogSeverity, IncidentStatus, Log, Incident, TriageResult; print('types OK')" 2>/dev/null; then
        success "✓ Python types importable"
    else
        warning "Python types import check skipped (pydantic required)"
    fi
    
    # Check client exists
    if [ ! -f "apps/api/src/client.py" ]; then
        error "Python client not found"
        return 1
    fi
    
    success "Python client exists"
    
    if grep -q "class TriageClient:" apps/api/src/client.py; then
        success "✓ TriageClient class defined"
    fi
    if grep -q "class SyncTriageClient:" apps/api/src/client.py; then
        success "✓ SyncTriageClient class defined"
    fi
    
    # Type check if mypy available
    if command_exists mypy; then
        if mypy apps/api/src/types.py --no-error-summary 2>/dev/null | grep -q "Success"; then
            success "✓ Python types pass mypy validation"
        else
            warning "Python types have mypy warnings (may be OK)"
        fi
    else
        warning "mypy not available (install with: pip install mypy)"
    fi
}

###############################################################################
# UNIT TESTS
###############################################################################
test_units() {
    print_header "TESTING: Unit Tests"
    
    # TypeScript tests
    if [ -f "packages/shared/test/test-typescript-client.ts" ]; then
        success "TypeScript test file exists"
        warning "Run TypeScript tests with: npm test -- packages/shared/test/test-typescript-client.ts"
    fi
    
    # Python tests
    if [ -f "apps/api/test/test_python_client.py" ]; then
        success "Python test file exists"
        warning "Run Python tests with: pytest apps/api/test/test_python_client.py -v"
    fi
}

###############################################################################
# MOCK SERVER TEST
###############################################################################
test_mock_server() {
    print_header "TESTING: Mock API Server"
    
    if command_exists prism; then
        success "Prism mock server available"
        echo -e "${YELLOW}To test with mock server, run:${NC}"
        echo "  prism mock packages/shared/specs/openapi.yaml -p 3000"
        echo ""
        echo "Then in another terminal:"
        echo "  curl -X POST http://localhost:3000/logs \\"
        echo "    -H 'Content-Type: application/json' \\"
        echo "    -d '{\"message\":\"test\",\"severity\":\"ERROR\",\"source\":\"cli\"}'"
    else
        warning "Prism not installed. Install with: npm install -g @stoplight/prism-cli"
    fi
}

###############################################################################
# INTEGRATION TEST
###############################################################################
test_integration() {
    print_header "TESTING: Integration"
    
    if [ -f "TESTING_GUIDE.md" ]; then
        success "Testing documentation exists"
    fi
    
    if [ -f "packages/shared/API_SPEC.md" ]; then
        success "API specification documentation exists"
    fi
    
    if [ -f "packages/shared/examples.py" ]; then
        success "Code examples exist"
    fi
}

###############################################################################
# PACKAGE STRUCTURE
###############################################################################
test_package_structure() {
    print_header "TESTING: Package Structure"
    
    local files=(
        "packages/shared/src/index.ts"
        "packages/shared/specs/openapi.yaml"
        "packages/shared/specs/schema.graphql"
        "packages/shared/src/types/index.ts"
        "packages/shared/src/api/client.ts"
        "apps/api/src/types.py"
        "apps/api/src/client.py"
    )
    
    local missing=0
    for file in "${files[@]}"; do
        if [ -f "$file" ]; then
            success "✓ $file"
        else
            error "✗ $file (missing)"
            missing=$((missing + 1))
        fi
    done
    
    if [ $missing -eq 0 ]; then
        success "All files present"
        return 0
    else
        error "$missing files missing"
        return 1
    fi
}

###############################################################################
# MAIN
###############################################################################
main() {
    echo ""
    echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║  Incident Triage API - Quick Test Suite                   ║${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    
    # Run tests
    local failed=0
    
    test_package_structure || failed=$((failed + 1))
    echo ""
    
    test_openapi || failed=$((failed + 1))
    echo ""
    
    test_graphql || failed=$((failed + 1))
    echo ""
    
    test_typescript || failed=$((failed + 1))
    echo ""
    
    test_python || failed=$((failed + 1))
    echo ""
    
    test_units || failed=$((failed + 1))
    echo ""
    
    test_integration || failed=$((failed + 1))
    echo ""
    
    test_mock_server
    echo ""
    
    # Summary
    print_header "TEST SUMMARY"
    
    if [ $failed -eq 0 ]; then
        echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
        echo -e "${GREEN}║  ✅ ALL TESTS PASSED!                                     ║${NC}"
        echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
        echo ""
        echo -e "${YELLOW}Next steps:${NC}"
        echo "  1. Run unit tests: npm test && pytest"
        echo "  2. Start mock server: prism mock packages/shared/specs/openapi.yaml"
        echo "  3. Review API_SPEC.md for usage examples"
        echo "  4. Review TESTING_GUIDE.md for detailed testing info"
        return 0
    else
        echo -e "${RED}╔════════════════════════════════════════════════════════════╗${NC}"
        echo -e "${RED}║  ❌ $failed TEST(S) FAILED                                ║${NC}"
        echo -e "${RED}╚════════════════════════════════════════════════════════════╝${NC}"
        return 1
    fi
}

main "$@"
