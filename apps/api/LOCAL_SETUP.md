# Local Development Setup (Without Docker)

If Docker Desktop isn't running or you prefer local development, follow these steps:

## Requirements

- PostgreSQL 16+ (already running at localhost:5432)
- Redis 7+ 
- Python 3.12+ with venv

## Setup Steps

### 1. Start Redis

**Windows (using WSL2 or native Redis):**
```powershell
# If you have Redis installed locally:
redis-server

# Or using WSL:
wsl redis-server
```

**Check Redis is running:**
```powershell
redis-cli ping
# Should return: PONG
```

### 2. Start Celery Worker

In a new PowerShell terminal:
```powershell
cd c:\Users\kings\my-monorepo\apps\api

# Activate venv if not already active
.\..\..\.venv\Scripts\Activate.ps1

# Start worker
celery -A src.celery_app worker --loglevel=info --concurrency=4
```

You should see:
```
 ---------- celery@COMPUTERNAME v5.x.x (...
 --- ***** -----
 -- ******* ----
 - *** --- * ---
 - ** ---------- [config]
 - ** ----------
 - ** ----------
 *** --- * --- [Queues]
 ---------- celery@... v5.x.x

[Tasks]
  . src.tasks.check_clustering_health
  . src.tasks.cluster_logs
  . src.tasks.handle_dead_letter

[2026-04-08 23:10:00,000: INFO/MainProcess] Connected to redis://localhost:6379/0
[2026-04-08 23:10:00,000: INFO/MainProcess] mingle: searching for method...
[2026-04-08 23:10:00,000: INFO/MainProcess] mingle: ready.
[2026-04-08 23:10:00,000: INFO/MainProcess] celery@... ready to accept tasks
```

### 3. Start Celery Beat (Optional - for scheduled tasks)

In another terminal:
```powershell
cd c:\Users\kings\my-monorepo\apps\api
.\..\..\.venv\Scripts\Activate.ps1
celery -A src.celery_app beat --loglevel=info
```

### 4. Start FastAPI Server

In another terminal:
```powershell
cd c:\Users\kings\my-monorepo\apps\api
.\..\..\.venv\Scripts\Activate.ps1
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

You should see:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete
```

### 5. Test the API

Open a new PowerShell terminal and test:

```powershell
cd c:\Users\kings\my-monorepo\apps\api

# Run the test script
.\test_clustering.ps1 -Action test
```

Or test specific endpoints:

```powershell
# Check API health
.\test_clustering.ps1 -Action health

# View statistics
.\test_clustering.ps1 -Action stats

# Check specific task
.\test_clustering.ps1 -Action status -TaskId abc123
```

## Verification Checklist

- [ ] Redis running: `redis-cli ping` → `PONG`
- [ ] PostgreSQL running: Database accessible at localhost:5432
- [ ] Celery worker started: Shows "ready to accept tasks"
- [ ] FastAPI running: http://localhost:8000/health returns 200
- [ ] Database seeded: Has logs, incidents, clusters

## Troubleshooting

### Redis not connecting
```powershell
# Check if Redis is running
redis-cli ping

# If not installed, install via Chocolatey:
choco install redis-64

# Or use WSL (Windows Subsystem for Linux):
wsl apt install redis-server
wsl service redis-server start
```

### Celery worker not starting
```powershell
# Check if Redis is available
redis-cli PING  # Must return PONG

# Check database connection
.\..\..\.venv\Scripts\python.exe -c "import psycopg2; print('DB OK')"

# Try verbose startup
celery -A src.celery_app worker --loglevel=debug
```

### API not responding
```powershell
# Check if running
.\test_clustering.ps1 -Action health

# Check for port conflicts
netstat -ano | findstr :8000

# Try different port
uvicorn src.main:app --port 8001
```

## Alternative: Docker Desktop Setup

If you want to use Docker but it won't start:

1. **Check Docker Desktop**:
   ```powershell
   docker --version
   docker ps
   ```

2. **Restart Docker Desktop**:
   - Press Windows key, search "Docker Desktop"
   - Quit and restart it
   - Wait for system tray icon to show it's running

3. **Check Docker resources**:
   - Docker Desktop → Settings → Resources
   - Ensure sufficients CPU/Memory allocated
   - Increase if needed

4. **Then run**:
   ```powershell
   docker-compose up -d
   ```

## API Endpoints Ready to Use

Once everything is running:

```powershell
# Submit clustering job
.\test_clustering.ps1 -Action test

# Check task status
.\test_clustering.ps1 -Action status -TaskId <task-id>

# View statistics
.\test_clustering.ps1 -Action stats

# View dead-letter queue (failed tasks)
.\test_clustering.ps1 -Action dlq

# Health check
.\test_clustering.ps1 -Action health
```

## Swagger UI

Once API is running, visit:
- **http://localhost:8000/docs** - Interactive API explorer
- **http://localhost:8000/redoc** - Alternative documentation

## Monitoring

### Celery Tasks
```powershell
# View active tasks
celery -A src.celery_app inspect active

# View task stats
celery -A src.celery_app inspect stats

# Purge dead tasks
celery -A src.celery_app purge
```

### Redis
```powershell
redis-cli
> KEYS log_dedup:*           # View dedup hashes
> DBSIZE                     # Check DB size
> INFO memory                # Memory usage
> FLUSHDB                    # Clear current DB
```

### Database
```powershell
.\..\..\.venv\Scripts\python.exe -c "
import psycopg2
conn = psycopg2.connect('host=localhost user=postgres password=FordsonHigh12 database=incident_triage')
cursor = conn.cursor()
for table in ['logs', 'incidents', 'clusters', 'triage_results']:
    cursor.execute(f'SELECT COUNT(*) FROM {table}')
    print(f'{table}: {cursor.fetchone()[0]}')
cursor.close()
conn.close()
"
```

## Next Steps

1. **Submit your first clustering job**:
   ```powershell
   .\test_clustering.ps1 -Action test
   ```

2. **Monitor the worker**:
   - Watch the Celery worker terminal for task execution
   - Check the API terminal for logs

3. **View results**:
   ```powershell
   .\test_clustering.ps1 -Action stats
   ```

4. **Scale up**:
   - Start additional worker processes for parallel job processing
   - Monitor task completion time and adjust concurrency

## Performance Tips

- **Worker concurrency**: 4 is good for development, adjust based on CPU cores
- **Result TTL**: Set to 1 hour to auto-clean old results
- **Redis memory**: Monitor with `redis-cli INFO memory`
- **PostgreSQL**: Verify connection pooling for high throughput

## References

- [Celery Documentation](https://docs.celeryproject.org)
- [FastAPI Guide](https://fastapi.tiangolo.com)
- [Redis CLI Commands](https://redis.io/commands)
- [PostgreSQL Connection](https://www.postgresql.org/docs/current/libpq-connect.html)
