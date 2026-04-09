# 🚀 Celery Clustering - Local Setup (No Docker Required)

Your Docker Desktop isn't running, but no problem! Here's the local setup:

## Prerequisites Check

✅ PostgreSQL running at `localhost:5432` (already verified in your db)  
✅ Python 3.12+ virtual environment (`.venv`)  
⚠️ Redis 7+ (need to install/start)  
⚠️ Celery dependencies (need to install)

---

## Step 1: Install Dependencies (2 minutes)

**Run this in PowerShell from `apps/api`:**

```powershell
cd c:\Users\kings\my-monorepo\apps\api
.\..\..\.venv\Scripts\Activate.ps1
pip install celery>=5.3.0 redis>=5.0.0 psycopg2-binary>=2.9.0 faker>=20.0.0
```

Or use the provided script:
```powershell
cd c:\Users\kings\my-monorepo\apps\api
.\..\..\.venv\Scripts\Activate.ps1
.\install_celery_deps.ps1
```

---

## Step 2: Install & Start Redis (3 minutes)

**Option A: Install via Chocolatey:**
```powershell
# Admin PowerShell:
choco install redis-64
redis-server
```

**Option B: Use WSL (Windows Subsystem for Linux):**
```powershell
wsl
sudo apt update
sudo apt install redis-server
redis-server
```

**Option C: Use Docker Desktop (if you can fix it):**
```powershell
docker run -d -p 6379:6379 redis:7-alpine
```

**Verify Redis is running:**
```powershell
redis-cli ping
# Should output: PONG
```

---

## Step 3: Start Services (Run Each in New PowerShell Terminal)

### Terminal 1: Celery Worker
```powershell
cd c:\Users\kings\my-monorepo\apps\api
.\..\..\.venv\Scripts\Activate.ps1
celery -A src.celery_app worker --loglevel=info --concurrency=4
```

Wait for this message:
```
[INFO/MainProcess] celery@... ready to accept tasks
```

### Terminal 2: FastAPI Server
```powershell
cd c:\Users\kings\my-monorepo\apps\api
.\..\..\.venv\Scripts\Activate.ps1
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

Wait for this message:
```
INFO:     Application startup complete
```

---

## Step 4: Test the Clustering API (1 minute)

### In a 3rd PowerShell terminal:

```powershell
cd c:\Users\kings\my-monorepo\apps\api

# Test 1: Health check
.\test_clustering.ps1 -Action health

# Test 2: Submit clustering job
.\test_clustering.ps1 -Action test

# Test 3: View statistics
.\test_clustering.ps1 -Action stats

# Test 4: View dead-letter queue (failed tasks)
.\test_clustering.ps1 -Action dlq
```

---

## What You Should See

### Terminal 1 (Worker) Output:
```
[2026-04-08 23:10:00,000: INFO/MainProcess] Connected to redis://localhost:6379/0
[2026-04-08 23:10:00,000: INFO/MainProcess] celery@... ready to accept tasks

# When task is submitted:
[2026-04-08 23:10:15,000: INFO/MainProcess] Task tasks.cluster_logs received
[2026-04-08 23:10:15,000: DEBUG/MainProcess] User task 'tasks.cluster_logs' in processes: ...
```

### Terminal 2 (API) Output:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete

# When API is called:
INFO:     POST /api/clustering/cluster-logs HTTP/1.1" 200
```

### Terminal 3 (Test Script) Output:
```
 ╔═══════════════════════════════════════════════════════════╗
 ║  Incident Triage - Clustering API Test                   ║
 ╚═══════════════════════════════════════════════════════════╝

 🏥 Checking API health...
 ✅ API is healthy
    Status: ok

 📤 Submitting clustering job...
    Log IDs: 3 logs
 ✅ Job submitted successfully
    Task ID: e5a4b234-c1a2-4d8e-b1c2-d8e4f5a6b7c8
    Status: submitted

 🔍 Checking task status...
    Task ID: e5a4b234-c1a2-4d8e-b1c2-d8e4f5a6b7c8
 ✅ Task status retrieved
    Status: SUCCESS
    Result:
      - Cluster ID: c5d8e9f0-a1b2-4c3d-e4f5-6a7b8c9d0e1f
      - Logs Clustered: 3
      - Logs Deduplicated: 0
      - Status: success
```

---

## PowerShell Test Scripts

### Built-in Test Script Commands:

```powershell
# Health check
.\test_clustering.ps1 -Action health

# Submit job and check status
.\test_clustering.ps1 -Action test

# Check specific task status
.\test_clustering.ps1 -Action status -TaskId "abc123..."

# View statistics
.\test_clustering.ps1 -Action stats

# View failed tasks
.\test_clustering.ps1 -Action dlq
```

---

## Manual PowerShell API Calls

If you want to use `Invoke-WebRequest` directly:

```powershell
# Health check
Invoke-WebRequest -Uri "http://localhost:8000/health" -Method GET | ConvertFrom-Json

# Submit clustering job
$body = @{
    log_ids = @("550e8400-e29b-41d4-a716-446655440000", "550e8400-e29b-41d4-a716-446655440001")
    skip_duplicates = $true
} | ConvertTo-Json

$response = Invoke-WebRequest `
    -Uri "http://localhost:8000/api/clustering/cluster-logs" `
    -Method POST `
    -ContentType "application/json" `
    -Body $body

$response.Content | ConvertFrom-Json

# Check task status (replace task_id)
Invoke-WebRequest -Uri "http://localhost:8000/api/clustering/tasks/{task_id}" -Method GET | ConvertFrom-Json

# Get statistics
Invoke-WebRequest -Uri "http://localhost:8000/api/clustering/stats" -Method GET | ConvertFrom-Json
```

---

## Monitoring in Real-Time

### Watch Celery Tasks:
```powershell
celery -A src.celery_app inspect active  # Current tasks
celery -A src.celery_app inspect reserved  # Queued tasks
```

### Watch Redis:
```powershell
redis-cli
> KEYS log_dedup:*  # Dedup cache entries
> DBSIZE  # Total keys in Redis
> INFO memory  # Memory usage
```

### Watch Database:
```powershell
.\..\..\.venv\Scripts\python.exe -c "
import psycopg2
conn = psycopg2.connect('host=localhost user=postgres password=FordsonHigh12 database=incident_triage')
cursor = conn.cursor()
for table in ['logs', 'incidents', 'clusters', 'triage_results', 'dead_letter_queue']:
    try:
        cursor.execute(f'SELECT COUNT(*) FROM {table}')
        print(f'{table}: {cursor.fetchone()[0]}')
    except: pass
cursor.close()
conn.close()
"
```

---

## Swagger API Browser

Once the API is running, visit:
- **http://localhost:8000/docs** - Interactive API documentation
- **http://localhost:8000/redoc** - Alternative docs view

---

## Troubleshooting

### "Redis is not available"
```powershell
# Check if Redis running
redis-cli ping

# If not:
redis-server

# Or if on WSL:
wsl redis-server
```

### "Cannot connect to API"
```powershell
# Check if API is running
curl http://localhost:8000/health

# Or with Invoke-WebRequest
Invoke-WebRequest http://localhost:8000/health

# If port 8000 is in use:
netstat -ano | findstr :8000
# Kill the process and try again
```

### "Task is stuck in PENDING"
```powershell
# Check if Celery worker is running
celery -A src.celery_app inspect active

# If not responding, restart worker in Terminal 1
Ctrl+C
celery -A src.celery_app worker --loglevel=info --concurrency=4
```

### "PostgreSQL connection failed"
```powershell
# Verify database exists
.\..\..\.venv\Scripts\python.exe verify_database.py

# Should show:
# clusters: 25
# incidents: 20
# logs: 600
# triage_results: 20
```

---

## Summary of Windows Commands

```powershell
# Quick setup (copy-paste):

# 1. Install dependencies
cd c:\Users\kings\my-monorepo\apps\api
.\..\..\.venv\Scripts\Activate.ps1
pip install celery redis psycopg2-binary faker

# 2. Run Redis (Terminal 1)
redis-server

# 3. Run Worker (Terminal 2)
cd c:\Users\kings\my-monorepo\apps\api
.\..\..\.venv\Scripts\Activate.ps1
celery -A src.celery_app worker --loglevel=info

# 4. Run API (Terminal 3)
cd c:\Users\kings\my-monorepo\apps\api
.\..\..\.venv\Scripts\Activate.ps1
uvicorn src.main:app --reload

# 5. Test (Terminal 4)
cd c:\Users\kings\my-monorepo\apps\api
.\test_clustering.ps1 -Action test
```

---

## Next Steps

1. ✅ Install dependencies
2. ✅ Start Redis
3. ✅ Start Celery worker
4. ✅ Start FastAPI server
5. ✅ Run test script
6. ✅ Monitor with Flower (optional): `pip install flower && flower -A src.celery_app`

**You're ready to go!** 🎉

Need help? Check the detailed guides:
- [CELERY_README.md](./CELERY_README.md) - Full technical reference
- [LOCAL_SETUP.md](./LOCAL_SETUP.md) - Detailed local setup
- [CELERY_QUICKSTART.md](./CELERY_QUICKSTART.md) - Quick reference
