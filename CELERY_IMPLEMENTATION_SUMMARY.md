# Celery + Redis Implementation - Complete Summary

## ✅ What Was Implemented

This implementation adds a production-ready background job queue system to the incident triage application with the following components:

### 1. **Celery with Redis**
- Task queue for asynchronous job processing
- Redis as message broker (rabbitmq-like pub/sub)
- Separate Redis backends for:
  - DB 0: Task queue (broker)
  - DB 1: Task results (result backend)
  - DB 2: Deduplication cache
- Multiple queues for job prioritization:
  - `default`: General tasks
  - `clustering`: Log clustering jobs
  - `dead_letter`: Failed task handling

### 2. **Idempotent Clustering Job** (`cluster_logs` task)
- **Atomicity**: Entire operation succeeds or fails
- **Deduplication**: Skip logs already processed
- **Idempotency**: Same input always produces same output
- **Error Recovery**: Automatic retries with backoff
- **Creation flow**:
  1. Fetch logs from PostgreSQL
  2. Compute hash for deduplication
  3. Filter duplicates using Redis cache
  4. Create or update cluster
  5. Return aggregated stats

### 3. **Exponential Backoff Retries**
Configuration in `src/tasks.py` CallbackTask class:
```python
max_retries = 5
retry_backoff = True        # exponential backoff enabled
retry_backoff_max = 600     # 10 minute cap
retry_jitter = True         # prevent thundering herd

# Retry schedule:
# 1st: 2^1 = 2 seconds
# 2nd: 2^2 = 4 seconds
# 3rd: 2^3 = 8 seconds
# 4th: 2^4 = 16 seconds
# 5th: 2^5 = 32 seconds
# (with jitter ±10%)
```

### 4. **Dead-Letter Queue (DLQ)**
- Automatic recording of failed tasks after max retries
- PostgreSQL table: `dead_letter_queue`
- Stores: task name, ID, args, kwargs, error message, traceback
- Statuses: `pending`, `retry_pending`, `recovered`
- Web API for querying and manual recovery
- Callback: `handle_dead_letter` task processes failures

### 5. **Log Deduplication via Hash**
Implemented in `src/dedup.py`:
```python
# Algorithm
hash = SHA256(message + source + severity)
redis_key = f"log_dedup:{hash}"

# Check if duplicate
if redis_key_exists:
    return DUPLICATE
else:
    set_expiry(redis_key, 24_hours)
    return NEW

# Performance
# - O(1) lookup time in Redis
# - 24-hour TTL per log pattern
# - Automatic cache cleanup
```

## 📁 Files Created/Modified

### New Files Created

```
apps/api/src/
├── celery_app.py              [NEW] Celery configuration
├── tasks.py                   [NEW] Celery tasks implementation
├── dedup.py                   [NEW] Deduplication logic
├── routes_clustering.py       [NEW] FastAPI clustering endpoints
└── main.py                    [UPDATED] Added clustering routes

apps/api/
├── CELERY_README.md           [NEW] 500+ line comprehensive guide
├── CELERY_QUICKSTART.md       [NEW] Quick reference guide
├── examples_clustering.py     [NEW] Usage examples
├── test/test_celery.py        [NEW] Unit and integration tests
└── pyproject.toml             [UPDATED] Added dependencies

root/
└── docker-compose.yml         [UPDATED] Added PostgreSQL, Redis, workers
```

### Key Files

#### `src/celery_app.py` (75 lines)
- Celery app initialization
- Broker configuration (Redis)
- Result backend configuration
- Queue definitions
- Task routing rules

#### `src/tasks.py` (400+ lines)
- `cluster_logs`: Main clustering task with deduplication
- `handle_dead_letter`: DLQ handler for failed tasks
- `check_clustering_health`: Health check endpoint
- Custom `CallbackTask` class with retry logic
- Error handling and logging

#### `src/dedup.py` (150+ lines)
- `compute_log_hash()`: SHA256 hash computation
- `is_log_duplicate()`: Check dedup cache
- `mark_log_hash_seen()`: Record in cache
- `get_dedup_stats()`: Cache statistics
- `clear_dedup_cache()`: Maintenance utility

#### `src/routes_clustering.py` (350+ lines)
- 7 API endpoints for clustering operations
- Task submission and status monitoring
- Dead-letter queue management
- Statistics and health checks
- Pydantic request/response models

#### `CELERY_README.md` (650+ lines)
- Architecture diagrams (ASCII art)
- Installation and setup guide
- Configuration options
- API usage examples
- Troubleshooting guide
- Production deployment advice
- Best practices and patterns

#### `examples_clustering.py` (250+ lines)
- Example 1: Simple log clustering
- Example 2: Deduplication handling
- Example 3: Monitoring and statistics
- Example 4: Error handling and retries
- Runnable demonstrations

#### `docker-compose.yml` (Updated)
- PostgreSQL 16 service with health checks
- Redis 7 service with persistence
- FastAPI API service
- Celery worker service
- Celery beat service for scheduling
- Proper dependency ordering

## 🚀 API Endpoints

### POST `/api/clustering/cluster-logs`
Submit a clustering job
```json
{
  "log_ids": ["uuid1", "uuid2", "uuid3"],
  "cluster_id": null,
  "skip_duplicates": true
}
```
Returns: `{task_id, status, message}`

### GET `/api/clustering/tasks/{task_id}`
Check task status
Returns: `{task_id, status, result?, error?}`

### GET `/api/clustering/tasks/{task_id}/result`
Get completed task result
Returns: `{cluster_id, logs_clustered, logs_deduplicated, timestamp, status}`

### GET `/api/clustering/health`
Health check
Returns: `{status, clustering, timestamp}`

### GET `/api/clustering/stats`
Clustering statistics
Returns: `{deduplication, active_tasks, timestamp}`

### GET `/api/clustering/dead-letter-queue`
Query failed tasks
Parameters: `limit`, `status`
Returns: `{count, records, timestamp}`

### POST `/api/clustering/tasks/{task_id}/retry`
Manually retry failed task
Returns: `{status, original_task_id, message}`

## 🔧 Configuration

### Environment Variables
```bash
# Redis Configuration
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/1
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=2

# Database Configuration
DB_HOST=localhost
DB_NAME=incident_triage
DB_USER=postgres
DB_PASSWORD=FordsonHigh12
DB_PORT=5432
```

### Celery Configuration (in `src/celery_app.py`)
```python
app.conf.update(
    task_acks_late=True,           # Ack after execution
    task_reject_on_worker_lost=True, # Reject if worker lost
    result_expires=3600,           # 1 hour result TTL
    worker_prefetch_multiplier=1,  # Process 1 task at a time
    worker_max_tasks_per_child=1000, # Restart after 1000 tasks
)
```

## 📊 Task Scheduling Information

### `cluster_logs` Task
- **Queue**: `clustering`
- **Retry**: Automatic exponential backoff (2-32s, max 600s)
- **Max Retries**: 5 attempts
- **DLQ**: Yes (on max retries exceeded)
- **Dedup**: Yes (Redis cache, 24h TTL)
- **Result TTL**: 1 hour
- **Timeout**: No explicit timeout (handles gracefully)

### `handle_dead_letter` Task
- **Queue**: `dead_letter`
- **Purpose**: Record failed tasks
- **Retry**: No (logs errors, doesn't retry itself)
- **Storage**: PostgreSQL `dead_letter_queue` table
- **Result TTL**: 1 hour

## 📈 Monitoring & Observability

### Celery Inspect Commands
```bash
# View active tasks
celery -A src.celery_app inspect active

# View queued tasks
celery -A src.celery_app inspect reserved

# Worker statistics
celery -A src.celery_app inspect stats

# Query specific task
celery -A src.celery_app inspect query_task task_id
```

### Redis CLI Commands
```bash
redis-cli
> KEYS log_dedup:*           # View dedup keys
> DBSIZE                     # Check DB usage
> GET log_dedup:{hash}       # View specific entry
> TTL log_dedup:{hash}       # Check expiry
> FLUSHDB 2                  # Clear dedup DB
```

### API Endpoints for Monitoring
- `GET /api/clustering/health` - System health
- `GET /api/clustering/stats` - Statistics
- `GET /api/clustering/dead-letter-queue` - Failed tasks

### Flower Web UI (Optional)
```bash
pip install flower
flower -A src.celery_app --port=5555
# Visit http://localhost:5555
```

## 🧪 Testing

Test file: `apps/api/test/test_celery.py` (200+ lines)

### Test Classes
- `TestDeduplication`: Hash computation and cache logic
- `TestClusterLogsTask`: Task execution and error handling
- `TestDeadLetterQueueTask`: DLQ recording
- `TestHealthCheck`: Health monitoring
- `TestDeduplicationIntegration`: Full workflow integration
- `TestCeleryConfiguration`: Configuration validation

### Running Tests
```bash
pytest apps/api/test/test_celery.py -v
```

## 🔄 Workflow Diagram

```
┌─ Submit Task ──────────────────────────────────────────┐
│                                                         │
├─ POST /api/clustering/cluster-logs                    │
│  └─ Celery: cluster_logs.apply_async()                │
│                                                         │
├─ Task Queue (Redis DB 0)                              │
│  ├─ Queue: clustering                                 │
│  └─ Task: cluster_logs(...args)                       │
│                                                         │
├─ Celery Worker                                         │
│  ├─ Fetch task from queue                             │
│  ├─ Execute: load logs from PostgreSQL                │
│  ├─ Dedup: check hashes in Redis DB 2                 │
│  ├─ Cluster: create/update clusters in PostgreSQL     │
│  ├─ Store result in Redis DB 1                        │
│  └─ Mark task as SUCCESS                              │
│                                                         │
├─ On Transient Error                                    │
│  ├─ Exponential backoff retry                         │
│  └─ Max 5 attempts                                    │
│                                                         │
├─ On Max Retries Exceeded                              │
│  ├─ Trigger: handle_dead_letter task                  │
│  ├─ Record: INSERT into dead_letter_queue             │
│  └─ Status: FAILURE                                   │
│                                                         │
└─ Get Status ───────────────────────────────────────────┘
   GET /api/clustering/tasks/{task_id}
   └─ Returns: PENDING → STARTED → SUCCESS (or FAILURE)
```

## 📚 Documentation Files

1. **CELERY_README.md** (650+ lines)
   - Architecture and design
   - Complete setup guide
   - Configuration reference
   - API documentation
   - Troubleshooting guide
   - Production deployment
   - Best practices

2. **CELERY_QUICKSTART.md** (350+ lines)
   - Quick start instructions
   - What was implemented
   - File structure overview
   - Key features explained
   - Monitoring guide
   - Troubleshooting tips

3. **examples_clustering.py** (250+ lines)
   - 4 runnable examples
   - Error handling patterns
   - Monitoring techniques

4. **test_celery.py** (200+ lines)
   - Unit tests for tasks
   - Integration tests
   - Configuration validation
   - Deduplication tests

## 🎯 Key Design Decisions

### 1. Separate Redis DBs
- DB 0: Broker (task queue) - requires persistence
- DB 1: Results (task results) - OK to lose on restart
- DB 2: Dedup cache - custom data, isolated from other DBs

### 2. Exponential Backoff Formula
- `delay = 2^attempt` seconds
- Jitter added to prevent thundering herd
- Capped at 600 seconds (10 minutes)
- Prevents overwhelming system during recovery

### 3. Deduplication Strategy
- Content-based hash (not ID-based)
- Includes source and severity (false positive prevention)
- 24-hour TTL (reasonable window for dedup)
- O(1) lookup in Redis

### 4. DLQ Implementation
- Stored in PostgreSQL (not Redis) for durability
- Includes full task context for debugging
- Stateful (tracks recovery attempts)
- Queryable via API for investigation

### 5. Task Routing
- Three separate queues prevent blocking
- Dead-letter queue isolated from main work
- Easier to scale specific queue types

## 🔐 Error Handling

### Graceful Degradation
```python
# Database connection fails → auto-retry
# Redis connection fails → auto-retry  
# Task timeout → auto-retry
# Max retries → record in DLQ
# DLQ recording fails → log and continue
```

### Idempotency Guarantees
1. **Deduplication**: Same logs never re-processed
2. **Database constraints**: ON CONFLICT clauses prevent duplicates
3. **Idempotent operations**: Only INSERT/UPDATE, no DELETE

### Callback Hooks
```python
# On task retry
on_retry() → Log warning with retry number

# On task failure (max retries)
on_failure() → Send to handle_dead_letter task
```

## 🚀 Getting Started

### 1. Quick Start (5 minutes)
```bash
cd apps/api
docker-compose up -d          # Start all services
sleep 5                       # Wait for healthchecks

# Check API is ready
curl http://localhost:8000/health
```

### 2. Submit a Job (2 minutes)
```bash
# Get some log UUIDs first
curl http://localhost:8000/api/clustering/stats

# Submit clustering job
curl -X POST http://localhost:8000/api/clustering/cluster-logs \
  -H "Content-Type: application/json" \
  -d '{"log_ids": ["uuid1", "uuid2"], "skip_duplicates": true}'
```

### 3. Monitor Progress (Real-time)
```bash
# Check status
curl http://localhost:8000/api/clustering/tasks/{task_id}

# Or use Flower
pip install flower
flower -A src.celery_app --port=5555
# Visit http://localhost:5555
```

## 📋 Checklist

- [x] Celery with Redis broker/backend
- [x] Idempotent clustering task
- [x] Exponential backoff retries
- [x] Dead-letter queue for failures
- [x] Log deduplication via SHA256 hash
- [x] Comprehensive API endpoints
- [x] Docker Compose setup
- [x] Full documentation (650+ lines)
- [x] Example usage patterns
- [x] Unit and integration tests
- [x] Configuration guide
- [x] Monitoring guide
- [x] Troubleshooting guide
- [x] Production deployment guide

## ✨ Next Steps

1. **Run the implementation**:
   ```bash
   docker-compose up -d
   ```

2. **Test with examples**:
   ```bash
   python examples_clustering.py 1
   ```

3. **Monitor with Flower**:
   ```bash
   flower -A src.celery_app
   ```

4. **Scale to production**:
   - Add multiple worker instances
   - Configure persistent Redis
   - Set up monitoring/alerting
   - Implement task rate limiting

## 📞 Support

See detailed documentation in:
- [CELERY_README.md](./CELERY_README.md) - Full reference
- [CELERY_QUICKSTART.md](./CELERY_QUICKSTART.md) - Quick guide
- [examples_clustering.py](./examples_clustering.py) - Code examples
- [test_celery.py](./test_celery.py) - Test patterns
