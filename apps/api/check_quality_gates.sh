#!/bin/bash
# Quality gates check - run locally before pushing
# Usage: ./check_quality_gates.sh

set -e

cd "$(dirname "$0")"

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
if pytest test/test_clustering_unit.py -v --cov=src --cov-report=term-missing --cov-fail-under=85 > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} Coverage check passed"
    ((PASSED++))
else
    echo -e "${RED}✗${NC} Coverage check failed - must be >= 85%"
    echo "Run: pytest test/test_clustering_unit.py --cov=src --cov-report=term"
    ((FAILED++))
fi

# 2. Unit tests
echo -e "\n${YELLOW}[2/3]${NC} Running unit tests..."
if pytest test/test_clustering_unit.py -v > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} All unit tests passed"
    ((PASSED++))
else
    echo -e "${RED}✗${NC} Unit tests failed"
    echo "Run: pytest test/test_clustering_unit.py -v"
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
    echo "  - Unit tests: pass"
    echo "  - RAG accuracy: >= 70%"
    echo -e "\n${GREEN}Ready to push!${NC}"
    exit 0
else
    echo -e "${RED}✗ Quality gates failed: $FAILED/$((PASSED + FAILED))${NC}"
    echo "Fix issues above and try again"
    exit 1
fi
