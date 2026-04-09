# 🔴 Redis Setup for Windows - Working Solutions

Your Celery worker is running but can't connect to Redis. Here are **3 working options**:

---

## Option 1: Native Windows Redis (Easiest ⭐)

This is the **simplest** - download pre-built Windows binaries.

### Run this command:

```powershell
cd c:\Users\kings\my-monorepo\apps\api
.\install_redis_windows.ps1
```

This will:
1. Download Redis 7.0 for Windows (~10 MB)
2. Extract to `C:\Redis`
3. Add to PATH

### Then start Redis:

```powershell
redis-server
```

You should see:
```
# oO0OoO0OoO0Oo Redis is starting oO0OoO0OoO0Oo
...
* Ready to accept connections
```

**Verify it works:**
```powershell
redis-cli ping
# Should output: PONG
```

---

## Option 2: Docker (If Docker works)

Simplest if Docker is available:

```powershell
docker run -d --name redis -p 6379:6379 redis:7-alpine redis-server --appendonly yes
```

Or use the setup script:
```powershell
cd c:\Users\kings\my-monorepo\apps\api
.\setup_redis.ps1 -Method docker
```

---

## Option 3: Python Mock Redis (For Testing Only)

No dependencies needed, but data doesn't persist:

```powershell
cd c:\Users\kings\my-monorepo\apps\api
.\setup_redis.ps1 -Method python
python mock_redis.py
```

---

## ⚡ Quick Start (Recommended Path)

### Step 1: Install Redis (one-time)
```powershell
cd c:\Users\kings\my-monorepo\apps\api
.\install_redis_windows.ps1
```

### Step 2: Start Redis (in Terminal 1)
```powershell
redis-server
```

Wait for: `Ready to accept connections`

### Step 3: Start Celery Worker (in Terminal 2)
```powershell
cd c:\Users\kings\my-monorepo\apps\api
.\..\..\.venv\Scripts\Activate.ps1
celery -A src.celery_app worker --loglevel=info --concurrency=4
```

Wait for: `ready to accept tasks`

### Step 4: Start API Server (in Terminal 3)
```powershell
cd c:\Users\kings\my-monorepo\apps\api
.\..\..\.venv\Scripts\Activate.ps1
uvicorn src.main:app --reload
```

Wait for: `Application startup complete`

### Step 5: Test (in Terminal 4)
```powershell
cd c:\Users\kings\my-monorepo\apps\api
.\test_clustering.ps1 -Action test
```

You should see:
```
✅ API is healthy
✅ Job submitted successfully
✅ Task status retrieved
✅ SUCCESS
```

---

## Troubleshooting

### "redis-server: command not found"
```powershell
# The installer didn't complete. Re-run:
.\install_redis_windows.ps1

# Check installation:
ls C:\Redis

# If it exists, add to PATH manually:
$env:PATH += ";C:\Redis"
redis-server
```

### "Error 10061: No connection could be made"
This appears in Celery worker - it means Redis isn't running on port 6379.

**Fix:**
```powershell
# Terminal 1:
redis-server

# Wait 2-3 seconds, then start Celery worker in Terminal 2
```

### "Address already in use"
Port 6379 is already taken.

```powershell
# Find what's using port 6379:
netstat -ano | findstr :6379

# Kill it (replace PID):
taskkill /PID <PID> /F

# Then start Redis again:
redis-server
```

### "Can't create directory /data"
If Redis complains about directory permissions, edit:
```powershell
# Start with --dir parameter:
redis-server --dir C:\temp
```

---

## Verify Everything Works

After starting all 3 services (Redis, Celery, API), test:

```powershell
# Terminal 4 - Run tests
cd c:\Users\kings\my-monorepo\apps\api

# Test 1: API health
.\test_clustering.ps1 -Action health
# Expected: ✅ API is healthy

# Test 2: Submit job
.\test_clustering.ps1 -Action test
# Expected: ✅ Job submitted successfully
#           ✅ Task status retrieved
#           ✅ SUCCESS

# Test 3: View statistics
.\test_clustering.ps1 -Action stats
# Expected: Shows dedup cache and active tasks

# Test 4: View failed tasks (if any)
.\test_clustering.ps1 -Action dlq
# Expected: Failed tasks = 0 (or shows details if any failed)
```

---

## What Each Terminal Should Show

### Terminal 1: Redis
```
# oO0OoO0OoO0Oo Redis is starting oO0OoO0OoO0Oo
* Ready to accept connections
```

### Terminal 2: Celery Worker
```
[INFO/MainProcess] Connected to redis://localhost:6379/0
[INFO/MainProcess] celery@... ready to accept tasks
```

### Terminal 3: FastAPI
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete
```

### Terminal 4: Test Output
```
✅ API is healthy
✅ Job submitted successfully
✅ Task status retrieved
Status: SUCCESS
```

---

## Long-term Solutions

### If you want Docker working properly:

1. **Restart Docker Desktop**:
   - Press `Windows` key
   - Search "Docker Desktop"
   - Kill it and restart
   - Wait 30 seconds for it to become ready

2. **Check Docker resources**:
   - Docker Desktop → Settings → Resources
   - Increase CPU cores if needed
   - Increase Memory if needed

3. **Reset Docker**:
   - Docker Desktop → troubleshoot → Reset

### If you want native Redis as a service:

Once Redis is in `C:\Redis`, install as Windows service:
```powershell
# Admin PowerShell:
cd C:\Redis
.\redis-server.exe --service-install
net start Redis
```

Then Redis starts automatically on boot.

---

## Next Steps

1. ✅ Run `.\install_redis_windows.ps1`
2. ✅ Start `redis-server` in Terminal 1
3. ✅ Start Celery worker in Terminal 2 (should connect now!)
4. ✅ Start API server in Terminal 3
5. ✅ Test with `test_clustering.ps1`

You're good to go! 🎉
