# Celery Queue with Redis - Implementation Guide

This document describes the incident triage system's background job processing using Celery and Redis.

## Architecture Overview

```
┌─────────────────┐
│   FastAPI App   │
│  (Main Process) │
└────────┬────────┘
         │
         │ submit task
         ▼
    ┌────────────┐
    │   Redis    │ ◄──────────┐
    │   Broker   │            │
    └────────────┘            │
         │                    │
    ┌────▼──────────────┬─────┴──────┐
    │                   │            │
    ▼                   ▼            ▼
┌─────────┐      ┌──────────┐   ┌──────────┐
│ Celery  │      │ Celery   │   │ Celery   │
│ Worker  │      │ Worker   │   │ Beat     │
│         │      │          │   │ (Sched)  │
└────┬────┘      └────┬─────┘   └──────────┘
     │                │
     └────────┬───────┘
              │ write results
              ▼
         ┌─────────────┐
         │ PostgreSQL  │
         │  Database   │
         └─────────────┘
```

## Features

### 1. Idempotent Clustering Job

The `cluster_logs` task ensures that:
- **Deduplication**: Logs with identical message/source/severity are skipped using Redis cache
- **Idempotency**: Same logs submitted multiple times won't be re-processed
- **Atomicity**: Cluster creation and updates are transactional

### 2. Exponential Backoff Retries

Automatic retry with exponential backoff:
- Initial retry: 2 seconds (2^1)
- Second retry: 4 seconds (2^2)
- Third retry: 8 seconds (2^3)
- ...up to 600 seconds max (10 minutes)
- Add jitter to prevent thundering herd

### 3. Dead-Letter Queue (DLQ)

Tasks that exceed max retries (5) are automatically:
- Recorded in `dead_letter_queue` table
- Logged for investigation
- Available for manual recovery and retry

### 4. Redis Deduplication

Log deduplication uses:
- SHA256 hash of (message + source + severity)
- 24-hour TTL in Redis (configurable)
- Prevents duplicate processing and data bloat

## Installation & Setup

### 1. Install Dependencies

```bash
pip install celery redis psycopg2-binary
```

Or update `pyproject.toml`:
```toml
dependencies = [
    "celery>=5.3.0",
    "redis>=5.0.0",
    "psycopg2-binary>=2.9.0",
]
```

### 2. Docker Compose Setup

```bash
docker-compose up -d
```

Services started:
- PostgreSQL on `localhost:5432`
- Redis on `localhost:6379`
- API on `localhost:8000`
- Celery Worker (processes clustering tasks)
- Celery Beat (schedules periodic tasks)

### 3. Manual Local Setup

**Start Redis**:
```bash
redis-server
```

**Start Celery Worker**:
```bash
cd apps/api
celery -A src.celery_app worker --loglevel=info
```

**Start Celery Beat** (for scheduled tasks):
```bash
celery -A src.celery_app beat --loglevel=info
```

**Start FastAPI**:
```bash
uvicorn src.main:app --reload
```

## API Usage

### Submit Clustering Job

```bash
curl -X POST http://localhost:8000/api/clustering/cluster-logs \
  -H "Content-Type: application/json" \
  -d '{
    "log_ids": ["uuid1", "uuid2", "uuid3"],
    "skip_duplicates": true
  }'
```

Response:
```json
{
  "task_id": "abc123def456",
  "status": "submitted",
  "message": "Clustering job submitted. Check status with /api/clustering/tasks/abc123def456"
}
```

### Check Task Status

```bash
curl http://localhost:8000/api/clustering/tasks/abc123def456
```

Possible statuses:
- `PENDING`: Waiting in queue
- `STARTED`: Processing
- `SUCCESS`: Completed
- `RETRY`: Retrying after error
- `FAILURE`: Max retries exceeded

Response when complete:
```json
{
  "task_id": "abc123def456",
  "status": "SUCCESS",
  "result": {
    "cluster_id": "cluster-uuid",
    "logs_clustered": 3,
    "logs_deduplicated": 0,
    "status": "success",
    "timestamp": "2026-04-08T10:30:45.123456+00:00"
  }
}
```

### Get Task Result

```bash
curl http://localhost:8000/api/clustering/tasks/abc123def456/result
```

### View Clustering Statistics

```bash
curl http://localhost:8000/api/clustering/stats
```

Response:
```json
{
  "deduplication": {
    "dedup_prefix": "log_dedup:",
    "ttl_seconds": 86400,
    "cache_ttl_hours": 24.0,
    "redis_db": 2
  },
  "active_tasks": {
    "default": 2,
    "clustering": 4,
    "dead_letter": 0
  },
  "timestamp": "2026-04-08T10:30:50.123456+00:00"
}
```

### View Dead-Letter Queue

```bash
curl http://localhost:8000/api/clustering/dead-letter-queue
```

Parameters:
- `limit`: Max records (default 50, max 1000)
- `status`: Filter by status (pending, retry_pending, recovered)

Response:
```json
{
  "count": 2,
  "records": [
    {
      "id": "dlq-uuid-1",
      "task_name": "tasks.cluster_logs",
      "task_id": "celery-task-id-1",
      "error_message": "Connection timeout after 5 retries",
      "status": "pending",
      "created_at": "2026-04-08T09:30:45.123456+00:00"
    }
  ],
  "timestamp": "2026-04-08T10:30:55.123456+00:00"
}
```

### Retry Failed Task

```bash
curl -X POST http://localhost:8000/api/clustering/tasks/abc123def456/retry
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `CELERY_BROKER_URL` | `redis://localhost:6379/0` | Redis broker URL |
| `CELERY_RESULT_BACKEND` | `redis://localhost:6379/1` | Redis result backend |
| `REDIS_HOST` | `localhost` | Redis hostname |
| `REDIS_PORT` | `6379` | Redis port |
| `REDIS_DB` | `2` | Redis DB for dedup cache |
| `DB_HOST` | `localhost` | PostgreSQL host |
| `DB_NAME` | `incident_triage` | Database name |
| `DB_USER` | `postgres` | DB user |
| `DB_PASSWORD` | `FordsonHigh12` | DB password |
| `DB_PORT` | `5432` | DB port |

### Celery Configuration

In `src/celery_app.py`:

```python
# Retry settings
app.conf.update(
    task_acks_late=True,  # Acknowledge after execution
    task_reject_on_worker_lost=True,  # Reject if worker dies
    result_expires=3600,  # Results expire after 1 hour
)

# Custom Task class retry settings
class CallbackTask(Task):
    autoretry_for = (Exception,)
    retry_kwargs = {'max_retries': 5}
    retry_backoff = True  # Exponential backoff
    retry_backoff_max = 600  # Max 10 minutes
    retry_jitter = True  # Add randomness
```

## Task Details

### cluster_logs

**Purpose**: Cluster logs with deduplication and idempotency

**Parameters**:
- `log_ids` (list[str]): UUIDs of logs to cluster
- `cluster_id` (str, optional): Existing cluster to add logs to
- `skip_duplicates` (bool): Skip duplicate logs (default true)

**Returns**:
```python
{
    "cluster_id": "uuid",
    "logs_clustered": 3,
    "logs_deduplicated": 2,
    "timestamp": "2026-04-08T...",
    "status": "success"
}
```

**Retry Behavior**:
- Max retries: 5
- Backoff: Exponential (2s → 4s → 8s → 16s → 32s)
- Max backoff: 600 seconds (10 minutes)
- On failure: Recorded in `dead_letter_queue` table

### handle_dead_letter

**Purpose**: Process tasks that failed after max retries

**Parameters**:
- `task_name`: Original task name
- `task_id`: Original task ID
- `args`: Original task arguments
- `kwargs`: Original task keyword arguments
- `error_message`: Error message from failure
- `error_traceback`: Full traceback

**Returns**:
```python
{
    "task_id": "celery-id",
    "task_name": "tasks.cluster_logs",
    "recorded_at": "2026-04-08T...",
    "status": "recorded_in_dlq"
}
```

## Monitoring & Debugging

### View Active Worker Tasks

```bash
celery -A src.celery_app inspect active
```

### View Scheduled Tasks

```bash
celery -A src.celery_app inspect scheduled
```

### View Worker Stats

```bash
celery -A src.celery_app inspect stats
```

### Purge Dead Tasks

```bash
celery -A src.celery_app purge
```

### Monitor with Flower (Web UI)

```bash
pip install flower
flower -A src.celery_app --port=5555
```

Then visit: http://localhost:5555

### Check Redis

```bash
redis-cli
> KEYS log_dedup:*  # View dedup hashes
> DBSIZE  # Check DB usage
> FLUSHDB  # Clear all keys (careful!)
```

## Deduplication Details

### How Deduplication Works

1. **Hash Computation**:
   ```python
   hash = SHA256(message + source + severity)
   ```

2. **Redis Key**:
   ```
   log_dedup:{hash}
   ```

3. **TTL**: 24 hours (86400 seconds)

4. **Check Flow**:
   ```
   hash = compute_hash(msg, source, severity)
   if key_exists(hash):
       return DUPLICATE
   else:
       set_key(hash, data, ttl=24h)
       return NEW
   ```

### Bypass Deduplication

To process duplicate logs anyway:

```bash
curl -X POST http://localhost:8000/api/clustering/cluster-logs \
  -H "Content-Type: application/json" \
  -d '{
    "log_ids": ["uuid1", "uuid2"],
    "skip_duplicates": false  # ← Process duplicates
  }'
```

## Troubleshooting

### Issue: Workers not processing tasks

```bash
# Check if worker is running
celery -A src.celery_app inspect active

# Check for stalled/dead tasks
celery -A src.celery_app inspect query_task task_id

# Restart worker
pkill -f 'celery worker'
celery -A src.celery_app worker --loglevel=info
```

### Issue: Tasks stuck in PENDING

```bash
# Check if broker connection works
redis-cli ping  # Should return PONG

# Check queue size
celery -A src.celery_app inspect reserved
```

### Issue: DLQ growing too large

```python
# Query DLQ
SELECT COUNT(*) FROM dead_letter_queue;

# Clean up old records
DELETE FROM dead_letter_queue 
WHERE created_at < NOW() - INTERVAL '30 days';
```

### Issue: Redis memory full

```bash
# Check Redis info
redis-cli info memory

# Find large keys
redis-cli --bigkeys

# Clean old dedup entries
redis-cli SCAN 0 MATCH "log_dedup:*" COUNT 1000
```

## Best Practices

1. **Always check task status before polling results**
   ```python
   task = cluster_logs.apply_async(...)
   result = task.get(timeout=30)  # Wait max 30s
   ```

2. **Handle task timeouts gracefully**
   ```python
   try:
       result = task.get(timeout=5)
   except TimeLimitExceeded:
       # Task took too long
       pass
   ```

3. **Monitor DLQ regularly**
   ```bash
   curl http://localhost:8000/api/clustering/dead-letter-queue | jq '.records | length'
   ```

4. **Set appropriate retry limits**
   - Too high: Long delays in failure detection
   - Too low: May miss transient failures

5. **Use separate Redis DBs for different purposes**
   - DB 0: Broker (task queue)
   - DB 1: Result backend
   - DB 2: Dedup cache
   - DB 3+: Other applications

## Production Deployment

### Using Systemd (Linux)

Create `/etc/systemd/system/celery-worker.service`:
```ini
[Unit]
Description=Celery Worker for Incident Triage
After=network.target redis-server.service postgres.service

[Service]
Type=forking
WorkingDirectory=/opt/incident-triage/apps/api
User=celery
Group=celery
ExecStart=/opt/incident-triage/.venv/bin/celery -A src.celery_app worker \
  --loglevel=info \
  --concurrency=4 \
  --queues=default,clustering,dead_letter \
  --pidfile=/var/run/celery/worker.pid \
  --logfile=/var/log/celery/worker.log

Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### Using Docker

Already configured in `docker-compose.yml`:
- `celery_worker`: Processes tasks
- `celery_beat`: Schedules recurring tasks

### Scaling Workers

Run multiple workers:
```bash
celery -A src.celery_app worker --loglevel=info --concurrency=8
celery -A src.celery_app worker --loglevel=info --concurrency=8 -n worker2@%h
```

Or use Docker Compose:
```yaml
celery_worker_1:
  # ... config ...
  
celery_worker_2:
  # ... config ...
```

## References

- [Celery Documentation](https://docs.celeryproject.org)
- [Redis Documentation](https://redis.io/docs)
- [PostgreSQL JSON Support](https://www.postgresql.org/docs/current/datatype-json.html)
- [Flower Monitoring](https://flower.readthedocs.io)
