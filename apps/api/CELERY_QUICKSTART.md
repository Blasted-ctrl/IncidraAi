# Celery + Redis Implementation - Quick Start

## What Was Implemented

✅ **Celery Queue with Redis**
- Distributed task queue for background job processing
- Pub/sub broker pattern using Redis
- Multiple queues: `default`, `clustering`, `dead_letter`

✅ **Idempotent Clustering Job**
- Deduplicates logs by content hash (SHA256)
- Groups related logs into clusters
- Atomic database operations
- Prevents duplicate processing

✅ **Exponential Backoff Retries**
- Auto-retry on transient failures
- Exponential backoff: 2s → 4s → 8s → 16s → 32s
- Jitter to prevent thundering herd
- Max retries: 5 attempts

✅ **Dead-Letter Queue (DLQ)**
- Records failed tasks after max retries
- Stores task info, args, kwargs, error details
- Available for manual recovery and investigation
- API endpoints for querying and managing DLQ

✅ **Log Deduplication via Hash**
- SHA256 hash of (message, source, severity)
- 24-hour TTL in Redis (DB 2)
- Efficient O(1) lookup time
- Configurable cache expiry

✅ **Comprehensive API Endpoints**
- POST `/api/clustering/cluster-logs` - Submit clustering job
- GET `/api/clustering/tasks/{task_id}` - Check task status
- GET `/api/clustering/tasks/{task_id}/result` - Get result
- GET `/api/clustering/stats` - View statistics
- GET `/api/clustering/dead-letter-queue` - Query DLQ
- POST `/api/clustering/tasks/{task_id}/retry` - Retry failed task

## Files Created

```
apps/api/src/
├── celery_app.py              # Celery configuration and initialization
├── tasks.py                   # Celery tasks (cluster_logs, handle_dead_letter)
├── dedup.py                   # Log deduplication utilities with Redis
├── routes_clustering.py       # FastAPI clustering endpoints
└── main.py                    # Updated with clustering routes

apps/api/
├── CELERY_README.md           # Comprehensive documentation
├── examples_clustering.py     # Example usage patterns
└── pyproject.toml            # Updated dependencies

docker-compose.yml            # Updated with PostgreSQL, Redis, Celery services
```

## Quick Start

### 1. Install Dependencies

```bash
cd apps/api
pip install -r requirements.txt  # or update via pyproject.toml
```

Required packages added:
- `celery>=5.3.0`
- `redis>=5.0.0`
- `psycopg2-binary>=2.9.0`

### 2. Start Services

**Option A: Using Docker**
```bash
docker-compose up -d
# Starts: PostgreSQL, Redis, API, Celery Worker, Celery Beat
```

**Option B: Manual Local Setup**

Terminal 1 - Redis:
```bash
redis-server
```

Terminal 2 - PostgreSQL:
```
Already running at localhost:5432
```

Terminal 3 - Celery Worker:
```bash
cd apps/api
celery -A src.celery_app worker --loglevel=info
```

Terminal 4 - API Server:
```bash
cd apps/api
uvicorn src.main:app --reload
```

### 3. Test Clustering

```bash
# Get some log UUIDs from PostgreSQL first
# Then submit a clustering job:

curl -X POST http://localhost:8000/api/clustering/cluster-logs \
  -H "Content-Type: application/json" \
  -d '{
    "log_ids": ["uuid-1", "uuid-2", "uuid-3"],
    "skip_duplicates": true
  }'

# Copy the task_id from response, then check status:

curl http://localhost:8000/api/clustering/tasks/task-id-here
```

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│                    FastAPI Application                    │
│  ┌─────────────────────────────────────────────────────┐  │
│  │  POST /api/clustering/cluster-logs                  │  │
│  │  → Submit task                                      │  │
│  └────────────────┬────────────────────────────────────┘  │
│                   │ submit_task()                          │
│                   ▼                                        │
│        ┌──────────────────────┐                           │
│        │  Celery Task Queue   │                           │
│        │  (Redis Broker)      │                           │
│        ├──────────────────────┤                           │
│        │ Queues:              │                           │
│        │ - default            │                           │
│        │ - clustering         │                           │
│        │ - dead_letter        │                           │
│        └──────────────────────┘                           │
└──────────────────────────────────────────────────────────┘
         │                    │                    │
    ┌────▼────┐          ┌────▼────┐          ┌────▼────┐
    │ Worker 1 │          │ Worker 2 │          │ Worker N │
    │ Running  │          │ Running  │          │ Running  │
    │ Tasks    │          │ Tasks    │          │ Tasks    │
    └────┬─────┘          └────┬─────┘          └────┬─────┘
         │                    │                    │
         └────────┬───────────┴────────┬───────────┘
                  │ on_retry           │ on_failure
                  ▼                    ▼
           ┌─────────────┐      ┌──────────────────┐
           │ Exponential │      │ Dead-Letter Queue │
           │ Backoff     │      │ (DLQ)             │
           │ Retry       │      │ PostgreSQL Table  │
           └─────────────┘      └──────────────────┘
                  │                    │
                  └────────┬───────────┘
                           ▼
                  ┌──────────────────┐
                  │   PostgreSQL     │
                  │  - logs          │
                  │  - incidents     │
                  │  - clusters      │
                  │  - DLQ table     │
                  └──────────────────┘

   ┌────────────────────────────────────┐
   │ Redis Deduplication Cache (DB 2)   │
   │ Keys: log_dedup:{hash}             │
   │ TTL: 24 hours                      │
   └────────────────────────────────────┘
```

## Key Features

### Deduplication
```python
# SHA256 hash of message + source + severity
hash = SHA256("DB connection timeout" + "database" + "ERROR")

# Checked in Redis before processing
if hash_exists_in_redis:
    skip_log()
else:
    process_log()
```

### Exponential Backoff
```
Attempt 1: 2 seconds (2^1)
Attempt 2: 4 seconds (2^2)
Attempt 3: 8 seconds (2^3)
Attempt 4: 16 seconds (2^4)
Attempt 5: 32 seconds (2^5)
Max:      600 seconds (10 minutes cap)
+ Jitter: Random ± 10% variance
```

### Dead-Letter Queue
```sql
-- Recording location
CREATE TABLE dead_letter_queue (
    id UUID PRIMARY KEY,
    task_name VARCHAR(255),        -- e.g., "tasks.cluster_logs"
    task_id VARCHAR(255) UNIQUE,   -- Celery task ID
    task_args JSONB,               -- Original arguments
    task_kwargs JSONB,             -- Original keyword args
    error_message TEXT,            -- Error that occurred
    error_traceback TEXT,          -- Full traceback
    created_at TIMESTAMP,          -- When recorded
    status VARCHAR(50)             -- pending/retry_pending/recovered
);
```

### Configuration

**Environment Variables** (all optional with sensible defaults):
```bash
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/1
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=2
DB_HOST=localhost
DB_NAME=incident_triage
DB_USER=postgres
DB_PASSWORD=FordsonHigh12
DB_PORT=5432
```

## API Examples

### Submit Job
```bash
curl -X POST http://localhost:8000/api/clustering/cluster-logs \
  -H "Content-Type: application/json" \
  -d '{
    "log_ids": ["uuid1", "uuid2"],
    "cluster_id": null,
    "skip_duplicates": true
  }'
```

### Check Status
```bash
curl http://localhost:8000/api/clustering/tasks/abc123
# Returns: PENDING, STARTED, SUCCESS, RETRY, FAILURE
```

### Get Result
```bash
curl http://localhost:8000/api/clustering/tasks/abc123/result
# Returns clustering result with stats
```

### View Statistics
```bash
curl http://localhost:8000/api/clustering/stats
# Returns dedup cache stats and active task counts
```

### Query DLQ
```bash
curl http://localhost:8000/api/clustering/dead-letter-queue?limit=50&status=pending
# Returns failed tasks for investigation
```

## Monitoring

### Celery Inspect
```bash
# Active tasks
celery -A src.celery_app inspect active

# Queue stats
celery -A src.celery_app inspect reserved

# Worker stats
celery -A src.celery_app inspect stats
```

### Flower Web UI (optional)
```bash
pip install flower
flower -A src.celery_app --port=5555
# Visit http://localhost:5555
```

### Redis CLI
```bash
redis-cli
> KEYS log_dedup:*        # View all dedup hashes
> DBSIZE                  # Check size
> FLUSHDB 2               # Clear dedup DB
```

## Troubleshooting

### Workers not processing tasks
```bash
# Check worker status
celery -A src.celery_app inspect active

# Restart worker
pkill -f 'celery worker'
celery -A src.celery_app worker --loglevel=info
```

### Tasks stuck in PENDING
```bash
# Redis connection issue?
redis-cli ping

# Check queue size
celery -A src.celery_app inspect reserved
```

### DLQ growing
```bash
# View failed tasks
curl http://localhost:8000/api/clustering/dead-letter-queue

# Clean up old records
# DELETE FROM dead_letter_queue WHERE created_at < NOW() - INTERVAL '30 days';
```

## Next Steps

1. **Scale workers**: Run multiple worker instances for parallelism
2. **Add scheduled tasks**: Use Celery Beat for recurring clustering jobs
3. **Implement recovery**: Auto-retry DLQ tasks after investigation
4. **Monitor metrics**: Track success rate, latency, DLQ growth
5. **Optimize hashing**: Consider algorithm changes based on performance

## Documentation

- Full details: [CELERY_README.md](./CELERY_README.md)
- Examples: [examples_clustering.py](./examples_clustering.py)
- API: http://localhost:8000/docs (Swagger)

## Status

✅ **Complete Implementation**
- Celery with Redis broker and backend
- Idempotent clustering task with deduplication
- Exponential backoff retries with jitter
- Dead-letter queue for failed tasks
- Comprehensive API endpoints
- Docker Compose setup
- Full documentation and examples
