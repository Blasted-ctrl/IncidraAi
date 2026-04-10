#!/bin/bash
# Quality gates check - run locally before pushing
# Usage: ./check_quality_gates.sh

set -e

cd "$(dirname "$0")"

COVERAGE_TESTS=(
  test/test_integration.py
  test/test_celery.py
  test/test_runtime_quality.py
)

COVERAGE_TARGETS=(
  --cov=src.main
  --cov=src.routes_clustering
  --cov=src.routes_rag
  --cov=src.tasks
  --cov=src.observability
  --cov=src.config
  --cov=src.rag
)

echo "🔍 Running Quality Gates Check..."
echo "================================="

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

PASSED=0
FAILED=0

# 1. Coverage check
echo -e "\n${YELLOW}[1/3]${NC} Checking test coverage >= 85%..."
if pytest --override-ini addopts= "${COVERAGE_TESTS[@]}" -v "${COVERAGE_TARGETS[@]}" --cov-report=term-missing --cov-fail-under=85 > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} Coverage check passed"
    ((PASSED++))
else
    echo -e "${RED}✗${NC} Coverage check failed - must be >= 85%"
    echo "Run: pytest --override-ini addopts= ${COVERAGE_TESTS[*]} ${COVERAGE_TARGETS[*]} --cov-report=term-missing"
    ((FAILED++))
fi

# 2. Unit tests
echo -e "\n${YELLOW}[2/3]${NC} Running unit tests..."
if pytest --override-ini addopts= "${COVERAGE_TESTS[@]}" -v > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} API runtime test suites passed"
    ((PASSED++))
else
    echo -e "${RED}✗${NC} API runtime tests failed"
    echo "Run: pytest --override-ini addopts= ${COVERAGE_TESTS[*]} -v"
    ((FAILED++))
fi

# 3. Evaluation accuracy
echo -e "\n${YELLOW}[3/3]${NC} Checking RAG evaluation accuracy >= 70%..."
EVAL_OUTPUT=$(python << 'EOF'
import sys
try:
    from src.rag import IncidentRAG
    from test.test_rag_evaluation import RAGEvaluator, GOLDEN_INCIDENTS
    
    rag = IncidentRAG()
    evaluator = RAGEvaluator(rag)
    metrics = evaluator.evaluate_all()
    
    overall_acc = metrics.overall_accuracy
    print(f"{overall_acc:.2%}")
    
    if overall_acc < 0.70:
        sys.exit(1)
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)
EOF
)

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓${NC} RAG evaluation passed (accuracy: $EVAL_OUTPUT)"
    ((PASSED++))
else
    echo -e "${RED}✗${NC} RAG evaluation failed - accuracy below 70%"
    echo "Run: python -c \"from src.rag import IncidentRAG; from test.test_rag_evaluation import RAGEvaluator; rag = IncidentRAG(); evaluator = RAGEvaluator(rag); print(evaluator.report())\""
    ((FAILED++))
fi

# Summary
echo -e "\n================================="
if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ All quality gates passed!${NC}"
    echo "  - Coverage: >= 85%"
    echo "  - API runtime tests: pass"
    echo "  - RAG accuracy: >= 70%"
    echo -e "\n${GREEN}Ready to push!${NC}"
    exit 0
else
    echo -e "${RED}✗ Quality gates failed: $FAILED/$((PASSED + FAILED))${NC}"
    echo "Fix issues above and try again"
    exit 1
fi
