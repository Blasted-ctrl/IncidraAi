"""
TESTING GUIDE FOR INCIDENT TRIAGE SYSTEM
=========================================

This document describes all available tests and how to run them.

Directory: apps/api/test/

Test Files:
  - test_clustering_unit.py     (17 unit tests)
  - test_integration.py         (12 integration tests)
  - locustfile.py               (Load testing)


QUICK START
===========

1. Verify Python environment is active:
   .venv\Scripts\Activate.ps1

2. Run all unit tests:
   pytest test/test_clustering_unit.py -v

3. Run all integration tests:
   pytest test/test_integration.py -v

4. Run load test (100 RPS for 60 seconds):
   locust -f test/locustfile.py --host=http://localhost:8000 -u 50 -r 5 --run-time 60s --headless

5. Run with coverage:
   pytest test/ -v --cov=src --cov-report=html


DETAILED TEST DESCRIPTIONS
===========================


UNIT TESTS (test_clustering_unit.py)
------------------------------------

Purpose: Test clustering core logic in isolation without dependencies.

Classes & Test Methods:

1. TestLogDeduplication (5 tests)
   - test_compute_log_hash_identical_logs
     → Same log content produces same hash
   - test_compute_log_hash_different_messages
     → Different messages produce different hashes
   - test_compute_log_hash_different_sources
     → Different sources produce different hashes
   - test_compute_log_hash_different_severities
     → Different severities produce different hashes
   - test_hash_cache_operations
     → Cache operations work correctly

2. TestClusteringLogic (3 tests)
   - test_cluster_requires_valid_input
     → Input validation works
   - test_cluster_creates_cluster_record
     → Clustering creates proper database records
   - test_cluster_groups_similar_logs
     → Similar logs are grouped together

3. TestClusteringRetryLogic (3 tests)
   - test_exponential_backoff_calculation
     → 2^n backoff: 2, 4, 8, 16, 32 seconds
   - test_max_backoff_capped
     → Backoff capped at 600 seconds
   - test_retry_limit_enforced
     → Maximum 5 retries enforced

4. TestClusteringIntegration (1 test)
   - test_complete_clustering_workflow
     → Full clustering pipeline validation

5. TestClusteringEdgeCases (5 tests)
   - test_empty_message_handling
     → Empty messages handled gracefully
   - test_unicode_message_handling
     → Unicode characters handled correctly
   - test_very_long_message_handling
     → Long messages (10k+ chars) processed
   - test_special_characters_handling
     → Special characters don't break hashing
   - test_null_like_strings_handling
     → "null", "None", etc. handled correctly

Run unit tests:
  pytest test/test_clustering_unit.py -v
  pytest test/test_clustering_unit.py::TestLogDeduplication -v
  pytest test/test_clustering_unit.py::TestClusteringRetryLogic::test_exponential_backoff_calculation -v


INTEGRATION TESTS (test_integration.py)
---------------------------------------

Purpose: Test complete workflows with all components working together.

Prerequisites:
  - PostgreSQL running (incident_triage database)
  - Celery worker running
  - Redis running (or fake Redis server)
  - FastAPI app ready to start

Classes & Test Methods:

1. TestLogIngestionEndpoint (2 tests)
   - test_submit_logs_for_clustering
     → API accepts log batches for clustering
   - test_clustering_task_creation
     → Celery task is created successfully

2. TestClusteringTaskFlow (2 tests)
   - test_cluster_task_processes_logs
     → Logs are processed into clusters
   - test_cluster_task_creates_incident
     → Incidents are created from clusters

3. TestTriageWorkflow (1 test)
   - test_get_triage_results
     → Triage results are retrievable

4. TestEndToEndIntegration (1 test)
   - test_log_ingestion_clustering_triage_flow
     → Complete: ingest → cluster → triage

5. TestDeadLetterQueueIntegration (1 test)
   - test_failed_task_goes_to_dlq
     → Failed tasks go to dead-letter queue

6. TestTaskRetryWorkflow (1 test)
   - test_task_retry_on_failure
     → Failed tasks are retried with backoff

7. TestClusteringStats (1 test)
   - test_get_clustering_statistics
     → Stats endpoint returns valid data

8. TestClusteringHealthCheck (1 test)
   - test_clustering_health_endpoint
     → Health check endpoint works

Run integration tests (requires running services):
  pytest test/test_integration.py -v
  pytest test/test_integration.py -v -s  (with print output)
  pytest test/test_integration.py::TestEndToEndIntegration -v


LOAD TESTS (locustfile.py)
--------------------------

Purpose: Validate system performance under high load (100+ RPS).

Simulates:
  - LogIngestionUser: Normal usage pattern
    • 80% error logs (1-5 logs per request)
    • 15% warning/info logs (2-10 logs per request)
    • 5% stats/health checks
  
  - HighLoadUser: Aggressive stress testing
    • Rapid 1-20 logs per request
    • Minimal wait time (1-50ms)

Metrics Captured:
  - Requests per second (throughput)
  - Response times (min/mean/max)
  - Failure rate
  - Connection errors
  - HTTP status codes

LOAD TEST SCENARIOS:

1. Steady 100 RPS (5 minutes):
   locust -f test/locustfile.py --host=http://localhost:8000 \
     -u 50 -r 5 --run-time 300s --headless
   
   Expected:
   - ~100 RPS sustained
   - Response time: <100ms
   - Success rate: 99%+

2. Ramp up to 200 RPS (10 minutes):
   locust -f test/locustfile.py --host=http://localhost:8000 \
     -u 100 -r 20 --run-time 600s --headless
   
   Expected:
   - Gradual ramp from 50 → 200 RPS
   - Observe response time degradation
   - Identify bottleneck under load

3. Stress test (300+ RPS, 5 minutes):
   locust -f test/locustfile.py --host=http://localhost:8000 \
     -u 200 -r 50 --run-time 300s --headless
   
   Expected:
   - Test system limits
   - Find breaking point
   - Monitor resource usage

4. Spike test (sudden 100→500 RPS):
   locust -f test/locustfile.py --host=http://localhost:8000 \
     -u 10 -r 2 --run-time 30s --headless
   (Then manually increase users during run via UI)
   
   Expected:
   - Measure queue backlog behavior
   - Observe recovery time
   - Verify no data loss

Interactive Load Testing (with UI):
   locust -f test/locustfile.py --host=http://localhost:8000
   Open: http://localhost:8089

   UI Controls:
   - Start/stop load
   - Adjust user count in real-time
   - Monitor stats live
   - Export results


RUNNING TESTS
=============


SETUP (One-time):

1. Activate Python environment:
   cd c:\Users\kings\my-monorepo\apps\api
   .\..\..\.venv\Scripts\Activate.ps1

2. Install test dependencies:
   pip install pytest pytest-asyncio pytest-cov httpx locust

3. Verify installation:
   pytest --version
   locust --version


UNIT TEST EXECUTION:

Commands:
  # All unit tests with verbose output
  pytest test/test_clustering_unit.py -v
  
  # All unit tests with coverage
  pytest test/test_clustering_unit.py -v --cov=src
  
  # Specific test class
  pytest test/test_clustering_unit.py::TestLogDeduplication -v
  
  # Specific test method
  pytest test/test_clustering_unit.py::TestLogDeduplication::test_compute_log_hash_identical_logs -v
  
  # With detailed output
  pytest test/test_clustering_unit.py -vv -s
  
  # With coverage report (HTML)
  pytest test/test_clustering_unit.py --cov=src --cov-report=html


INTEGRATION TEST EXECUTION (Requires Running Services):

Prerequisites:
  # Terminal 1: Start Redis
  python start_redis.py
  
  # Terminal 2: Start Celery worker
  celery -A src.celery_app worker --loglevel=info
  
  # Terminal 3: Start PostgreSQL (or verify it's running)
  # Terminal 4: Run tests

Commands:
  # All integration tests
  pytest test/test_integration.py -v
  
  # Specific integration test
  pytest test/test_integration.py::TestEndToEndIntegration -v
  
  # With detailed output
  pytest test/test_integration.py -vv -s
  
  # Only tests that don't require running API
  pytest test/test_integration.py::TestClusteringStats -v


LOAD TEST EXECUTION:

Prerequisites (same as integration tests):
  # Terminal 1: Start Redis
  python start_redis.py
  
  # Terminal 2: Start Celery worker
  celery -A src.celery_app worker --loglevel=info
  
  # Terminal 3: Start API server
  python -m uvicorn src.main:app --reload
  
  # Terminal 4: Run Locust

Commands:
  # Headless load test (100 RPS for 60 seconds)
  locust -f test/locustfile.py --host=http://localhost:8000 \
    -u 50 -r 5 --run-time 60s --headless
  
  # Interactive UI load test
  locust -f test/locustfile.py --host=http://localhost:8000
  # Then open http://localhost:8089
  
  # High-load stress test (300+ RPS)
  locust -f test/locustfile.py --host=http://localhost:8000 \
    -u 200 -r 50 --run-time 300s --headless


RUNNING ALL TESTS:

1. Unit tests (no dependencies):
   pytest test/test_clustering_unit.py -v --cov=src

2. Full suite (requires services):
   # Start services first, then:
   pytest test/ -v --cov=src --cov-report=html
   
   # View coverage report
   start htmlcov/index.html


INTERPRETING RESULTS
====================

Unit Tests Success:
  ✓ 17 passed in 0.05s
  → All clustering logic tests passed

Integration Tests Success:
  ✓ 12 passed in 2.34s
  → All workflow tests passed (dependencies working)

Load Test Success (100 RPS):
  Stats:
    Requests: 6000+ (60s × ~100 RPS)
    Success rate: 99%+
    Avg response time: <100ms
  → System handling target load


COMMON ISSUES
=============

"FAILED - ModuleNotFoundError: No module named 'src'"
  → Ensure you're running from: c:\Users\kings\my-monorepo\apps\api
  → Pytest should auto-discover with pyproject.toml config

"Connection refused" during integration tests
  → Verify Redis is running: python start_redis.py
  → Verify Celery worker running: celery -A src.celery_app worker
  → Verify PostgreSQL is running

"load test endpoint not found"
  → Start API: python -m uvicorn src.main:app --reload
  → Verify --host=http://localhost:8000 is correct

"Test hangs indefinitely"
  → Check Celery worker for errors
  → Verify Redis is responding
  → Ctrl+C to cancel and check logs


COVERAGE ANALYSIS
=================

Generate HTML coverage report:
  pytest test/ --cov=src --cov-report=html
  start htmlcov/index.html

Target coverage:
  - Unit tests: 100% coverage of core logic
  - Integration tests: 100% coverage of endpoints
  - Overall: 80%+ combined coverage

View coverage in terminal:
  pytest test/test_clustering_unit.py --cov=src --cov-report=term-missing
"""

# This file provides comprehensive testing documentation
# See the test files for the actual test code
