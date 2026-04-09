# Quality gates check for Windows - run locally before pushing
# Usage: .\check_quality_gates.ps1

$ErrorActionPreference = "Stop"

Write-Host "🔍 Running Quality Gates Check..." -ForegroundColor Cyan
Write-Host "=================================" -ForegroundColor Cyan

$PASSED = 0
$FAILED = 0

# 1. Coverage check
Write-Host "`n[1/3] Checking test coverage >= 85%..." -ForegroundColor Yellow

try {
    $result = pytest test/test_clustering_unit.py -v --cov=src `
      --cov-report=term-missing --cov-fail-under=85 2>$null
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ Coverage check passed" -ForegroundColor Green
        $PASSED++
    } else {
        Write-Host "✗ Coverage check failed - must be >= 85%" -ForegroundColor Red
        Write-Host "Run: pytest test/test_clustering_unit.py --cov=src --cov-report=term" -ForegroundColor Gray
        $FAILED++
    }
} catch {
    Write-Host "✗ Coverage check error: $_" -ForegroundColor Red
    $FAILED++
}

# 2. Unit tests
Write-Host "`n[2/3] Running unit tests..." -ForegroundColor Yellow

try {
    pytest test/test_clustering_unit.py -v 2>$null
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ All unit tests passed" -ForegroundColor Green
        $PASSED++
    } else {
        Write-Host "✗ Unit tests failed" -ForegroundColor Red
        Write-Host "Run: pytest test/test_clustering_unit.py -v" -ForegroundColor Gray
        $FAILED++
    }
} catch {
    Write-Host "✗ Unit test error: $_" -ForegroundColor Red
    $FAILED++
}

# 3. Evaluation accuracy
Write-Host "`n[3/3] Checking RAG evaluation accuracy >= 70%..." -ForegroundColor Yellow

try {
    $evalScript = @"
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
"@
    
    $output = python -c $evalScript 2>$null
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ RAG evaluation passed (accuracy: $output)" -ForegroundColor Green
        $PASSED++
    } else {
        Write-Host "✗ RAG evaluation failed - accuracy below 70%" -ForegroundColor Red
        Write-Host "Run: python -c `"from src.rag import IncidentRAG; from test.test_rag_evaluation import RAGEvaluator; rag = IncidentRAG(); evaluator = RAGEvaluator(rag); print(evaluator.report())`"" -ForegroundColor Gray
        $FAILED++
    }
} catch {
    Write-Host "✗ RAG evaluation error: $_" -ForegroundColor Red
    $FAILED++
}

# Summary
Write-Host "`n=================================" -ForegroundColor Cyan

if ($FAILED -eq 0) {
    Write-Host "✓ All quality gates passed!" -ForegroundColor Green
    Write-Host "  - Coverage: >= 85%" -ForegroundColor Green
    Write-Host "  - Unit tests: pass" -ForegroundColor Green
    Write-Host "  - RAG accuracy: >= 70%" -ForegroundColor Green
    Write-Host "`n Ready to push!" -ForegroundColor Green
    exit 0
} else {
    Write-Host "✗ Quality gates failed: $FAILED/$($PASSED + $FAILED)" -ForegroundColor Red
    Write-Host "Fix issues above and try again" -ForegroundColor Red
    exit 1
}
