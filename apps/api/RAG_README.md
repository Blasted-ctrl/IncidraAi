"""
RAG SYSTEM DOCUMENTATION
========================

Retrieval-Augmented Generation (RAG) for Incident Triage

This document describes the RAG system that enhances incident analysis by retrieving
relevant logs and runbooks, then using LLM reasoning to provide context-aware insights.


OVERVIEW
========

The RAG system consists of three components:

1. EMBEDDING STORE (Vector Database)
   - Uses sentence-transformers for semantic embeddings
   - Powered by ChromaDB for vector storage
   - Stores logs and runbooks for semantic similarity search

2. INCIDENT REASONER (LLM Integration)
   - Uses Claude via Anthropic API
   - Analyzes incidents with retrieved context
   - Provides root cause analysis, severity assessment, and recommendations

3. RAG PIPELINE (Orchestration)
   - Combines embedding + retrieval + LLM reasoning
   - Provides end-to-end incident analysis


SETUP
=====

1. INSTALL DEPENDENCIES
   pip install -r requirements-rag.txt
   
   Or with pip:
   pip install sentence-transformers chromadb anthropic numpy

2. SET ANTHROPIC API KEY
   export ANTHROPIC_API_KEY=sk-ant-xxx  # Your key from https://console.anthropic.com/

3. (Optional) VERIFY INSTALLATION
   python -c "from src.rag import IncidentRAG; print('RAG imported successfully')"


USAGE
=====

PYTHON API
----------

from src.rag import IncidentRAG

# Initialize RAG system
rag = IncidentRAG(
    embedding_model="all-MiniLM-L6-v2",
    llm_model="claude-3-5-sonnet-20241022",
    persist_dir="./vector_db"  # Persistent vector store
)

# Ingest runbooks
runbooks = [
    {
        "id": "rb-001",
        "title": "Database Troubleshooting",
        "service": "database",
        "tags": ["database", "connection"],
        "content": "Steps to troubleshoot database issues..."
    }
]
rag.ingest_runbooks(runbooks)

# Analyze incident
logs = [
    "Database connection timeout error",
    "Connection pool exhausted",
]

result = rag.analyze_incident(
    incident_summary="API service unable to reach database",
    logs=logs,
    cluster_info={"service": "api"},
    top_k_logs=5,        # Retrieve 5 similar logs
    top_k_runbooks=3     # Retrieve 3 relevant runbooks
)

print(result["reasoning"]["reasoning"])
# Output:
# {
#   "root_cause": "Database connection pool exhausted...",
#   "severity": "critical",
#   "affected_services": ["api-service", "database"],
#   "actions": ["Check database status", ...],
#   "metrics": ["pool_utilization", ...],
#   "escalation": "yes - to database team"
# }


REST API
--------

ENDPOINT: POST /api/rag/analyze
Request:
{
  "incident_summary": "Database connection failures",
  "logs": [
    "Connection timeout after 30s",
    "Pool exhausted: 100/100 active"
  ],
  "cluster_info": {"service": "api"},
  "top_k_logs": 5,
  "top_k_runbooks": 3
}

Response:
{
  "incident_summary": "...",
  "retrieved_logs": {
    "count": 3,
    "documents": [...],
    "relevance_scores": [0.95, 0.87, 0.75]
  },
  "retrieved_runbooks": {
    "count": 2,
    "documents": [...],
    "relevance_scores": [0.92, 0.81]
  },
  "reasoning": {
    "success": true,
    "reasoning": {
      "root_cause": "...",
      "severity": "critical",
      ...
    },
    "model": "claude-3-5-sonnet-20241022",
    "tokens_used": 512
  }
}


INGESTING RUNBOOKS
------------------

ENDPOINT: POST /api/rag/ingest-runbooks
Request:
[
  {
    "id": "rb-db-001",
    "title": "Database Connection Troubleshooting",
    "service": "database",
    "tags": ["database", "connection", "troubleshooting"],
    "content": "Full runbook content..."
  },
  ...
]

Response:
{
  "status": "success",
  "runbooks_ingested": 1,
  "timestamp": "2026-04-08T..."
}


TESTING
=======

1. UNIT TESTS
   pytest test/test_rag_integration.py::TestEmbeddingStore -v
   pytest test/test_rag_integration.py::TestIncidentReasoner -v
   pytest test/test_rag_integration.py::TestIncidentRAG -v

2. EVALUATION TESTS
   pytest test/test_rag_evaluation.py -v

3. EVALUATION HARNESS
   python -c "
   from src.rag import IncidentRAG
   from test.test_rag_evaluation import RAGEvaluator, GOLDEN_INCIDENTS
   
   rag = IncidentRAG()
   evaluator = RAGEvaluator(rag)
   metrics = evaluator.evaluate_all()
   print(evaluator.report())
   "

4. INTEGRATION TESTS (with running API)
   # Terminal 1: Start API
   python -m uvicorn src.main:app --reload
   
   # Terminal 2: Run tests
   pytest test/test_rag_integration.py::TestRAGEndpoints -v


EVALUATION METRICS
==================

The evaluation harness compares RAG predictions against golden dataset (20 incidents).

Metrics Reported:

1. ROOT CAUSE ACCURACY
   - Percentage of incidents where predicted root cause matches expected
   - Target: > 80%

2. SEVERITY ACCURACY
   - Percentage of incidents where predicted severity matches expected
   - Target: > 85%

3. SERVICE ACCURACY
   - Percentage of incidents where predicted affected services are correct
   - Target: > 75%

4. RETRIEVAL QUALITY
   - Average relevance score of retrieved logs and runbooks
   - Target: > 0.8 relevance

5. OVERALL ACCURACY
   - Average of all accuracy metrics
   - Target: > 80%

6. RESPONSE TIME
   - Average time to complete analysis
   - Target: < 500ms

7. PRECISION AT K
   - Precision of top-k results
   - Precision@1, Precision@3, Precision@5

RUNNING EVALUATION
------------------

python test/test_rag_evaluation.py

Output includes:
- Individual incident results (✓ or ✗ for each metric)
- Aggregate metrics
- HTML report (if pytest-cov installed)


GOLDEN DATASET
==============

The evaluation harness includes 20 golden incidents covering common scenarios:

1. incident-001: Database Connection Pool Exhaustion
2. incident-002: High Memory Usage in Cache Service
3. incident-003: TLS Certificate Expiration
4. incident-004: Message Queue Backlog
5. incident-005: DNS Resolution Failures
6. incident-006: Authentication Service Timeout
7. incident-007: Disk Space Critical
8. incident-008: Rate Limit Exceeded
9. incident-009: Deployment Failed - Rollback Needed
10. incident-010: Memory Leak Detected
11. incident-011: Cross-Service Network Partition
12. incident-012: Third-Party API Dependency Failure
13. incident-013: Database Replication Lag
14. incident-014: Container Restart Loop
15. incident-015: Resource Quota Exceeded
16. incident-016: Stuck Transactions
17. incident-017: Cascading Service Failures
18. incident-018: Data Corruption Detected
19. incident-019: Slow Query Performance
20. incident-020: Configuration Drift

Each golden incident contains:
- ID and title
- Description and logs
- Expected root cause, severity, and affected services
- Expected remediation actions
- Relevant runbooks


ARCHITECTURE
============

Data Flow:

1. INGESTION
   Logs and Runbooks → Embedding Store
   
2. RETRIEVAL
   Query (Incident Summary) → Vector Similarity Search
   Returns: Similar Logs + Relevant Runbooks

3. AUGMENTATION
   Logs + Runbooks → Context Building
   Creates comprehensive context for LLM

4. REASONING
   Context → LLM Analysis → Reasoning Results
   Outputs: Root Cause, Severity, Actions, Metrics

5. RESPONSE
   Combined Results → API Response
   Includes retrieval quality and reasoning confidence

Performance Characteristics:

- Embedding Generation: ~50-100ms per item
- Vector Search: ~10-50ms for top-k retrieval
- LLM Reasoning: ~200-500ms per analysis
- Total Pipeline: ~300-700ms per incident


CUSTOMIZATION
=============

1. EMBEDDING MODEL
   Change model in IncidentRAG initialization:
   
   rag = IncidentRAG(
       embedding_model="all-mpnet-base-v2"  # Larger, higher quality
   )
   
   Options:
   - "all-MiniLM-L6-v2" (fast, small)
   - "all-mpnet-base-v2" (slow, high quality)
   - "paraphrase-MiniLM-L6-v2" (general purpose)
   - "multi-qa-mpnet-base-dot-v1" (QA focused)

2. LLM MODEL
   Change model in IncidentRAG initialization:
   
   rag = IncidentRAG(
       llm_model="claude-3-opus-20240229"  # More capable
   )

3. VECTOR STORE PERSISTENCE
   rag = IncidentRAG(persist_dir="./my_vector_db")
   
   Persistent storage allows:
   - Runbook reuse across restarts
   - Historical incident context
   - Incremental ingestion

4. PROMPT CUSTOMIZATION
   Edit prompt in IncidentReasoner.reason_about_incident()
   Adjust for:
   - Different reasoning style
   - Additional output fields
   - Company-specific requirements


TROUBLESHOOTING
===============

1. "ANTHROPIC_API_KEY not set"
   Fix: export ANTHROPIC_API_KEY=sk-ant-...
   Note: Without key, uses mock reasoning (debug mode)

2. "sentence-transformers not installed"
   Fix: pip install sentence-transformers

3. "chromadb connection failed"
   Fix: pip install chromadb

4. Poor retrieval quality
   - Increase top_k in analyze_incident()
   - Ingest more comprehensive runbooks
   - Consider different embedding model

5. Slow LLM responses
   - Use faster model (sonnet vs opus)
   - Reduce prompt complexity
   - Check API rate limits


PERFORMANCE TUNING
==================

1. Vector Store Optimization
   - Use smaller model for faster embeddings: all-MiniLM-L6-v2
   - Batch ingest runbooks for efficiency
   - Use persistence to avoid re-embedding

2. LLM Optimization
   - Use faster model: claude-3-5-sonnet
   - Reduce context window size
   - Implement result caching

3. Retrieval Optimization
   - Tune top_k based on performance vs quality tradeoff
   - Implement query expansion for better matching
   - Add semantic cache layer


EXAMPLES
========

Example 1: Analyzing Database Issue

logs = [
    "Error: connection pool exhausted",
    "Connection timeout after 30000ms",
    "Max pool size reached: 100/100"
]

rag.analyze_incident(
    incident_summary="API unable to connect to database",
    logs=logs
)

Output:
{
  "root_cause": "Database connection pool exhausted due to slow queries",
  "severity": "critical",
  "affected_services": ["api-service", "database"],
  "actions": [
    "Check running queries and kill long-running transactions",
    "Increase connection pool size temporarily",
    "Monitor query performance"
  ]
}


Example 2: Analyzing Performance Issue

logs = [
    "p99 latency: 5000ms",
    "Database query avg: 4500ms",
    "Cache hit ratio: only 25%"
]

rag.analyze_incident(
    incident_summary="Service experiencing high latency",
    logs=logs,
    top_k_logs=10,  # Get more context for performance issues
    top_k_runbooks=5
)

Output:
{
  "root_cause": "Database queries not cached, causing high latency",
  "severity": "high",
  "affected_services": ["api-service", "cache-service"],
  "metrics": ["query_time", "cache_hit_ratio", "p99_latency"]
}


FAQ
===

Q: Can I train the model on custom domain?
A: The embedding model is pre-trained. For domain-specific improvements,
   augment the prompt context with domain-specific runbooks.

Q: Does RAG reduce hallucinations?
A: Yes. By providing specific retrieved context, the LLM has factual
   information to base reasoning on, reducing confabulation.

Q: How do I improve accuracy?
A: Add more runbooks, improve prompt templates, tune retrieval parameters,
   and evaluate against golden dataset regularly.

Q: Can I use a different LLM?
A: Yes. Modify IncidentReasoner to use your preferred LLM (GPT-4, Llama, etc).

Q: How do I add custom reasoning logic?
A: Extend reason_about_incident() or create custom ReasonerStrategy classes.
"""

# This is documentation for the RAG system
