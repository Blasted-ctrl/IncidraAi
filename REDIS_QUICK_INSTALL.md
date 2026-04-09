# ⚡ 2-Minute Redis Setup (Windows)

## Option A: One-Line Setup

Copy-paste this into **PowerShell** (as admin):

```powershell
# Download and run Redis installer
Invoke-WebRequest -Uri "https://github.com/tporadowski/redis/releases/download/v7.0.11/Redis-x64-7.0.11.zip" -OutFile "$env:TEMP\redis.zip"; Expand-Archive "$env:TEMP\redis.zip" -DestinationPath "C:\" -Force; "C:\Redis-x64-7.0.11\redis-server.exe"
```

Then in another **PowerShell** window:
```powershell
redis-cli ping
# Should output: PONG
```

---

## Option B: Manual Steps (3 minutes)

1. **Download**:
   - Go to: https://github.com/tporadowski/redis/releases
   - Download: `Redis-x64-7.0.11.zip`

2. **Extract**:
   - Extract to `C:\Redis`
   - You should see `redis-server.exe` in that folder

3. **Run Redis**:
   ```powershell
   C:\Redis\redis-server.exe
   ```

4. **Test in another PowerShell**:
   ```powershell
   C:\Redis\redis-cli.exe ping
   # Should output: PONG
   ```

---

## Option C: Using our installer script (Recommended)

**Run this in PowerShell**:

```powershell
cd c:\Users\kings\my-monorepo\apps\api
.\install_redis_windows.ps1
redis-server
```

---

## What Happens Next

Once Redis is running (you'll see "Ready to accept connections"):

**Terminal 2 - Celery Worker:**
```powershell
cd c:\Users\kings\my-monorepo\apps\api
.\..\..\.venv\Scripts\Activate.ps1
celery -A src.celery_app worker --loglevel=info
```

Wait for: `ready to accept tasks`

This error will go away:
```
ERROR/MainProcess] consumer: Cannot connect to redis://localhost:6379/0
```

And you'll see:
```
[INFO/MainProcess] Connected to redis://localhost:6379/0
[INFO/MainProcess] celery@... ready to accept tasks
```

---

## Verification

In a 3rd PowerShell:

```powershell
cd c:\Users\kings\my-monorepo\apps\api

# Check Redis
redis-cli ping
# Output: PONG

# Test API
.\test_clustering.ps1 -Action health
# Output: ✅ API is healthy
```

---

## Quick Reference

```powershell
# Start Redis (Terminal 1)
redis-server

# Start Celery (Terminal 2)
cd c:\Users\kings\my-monorepo\apps\api
.\..\..\.venv\Scripts\Activate.ps1
celery -A src.celery_app worker --loglevel=info

# Start API (Terminal 3)
cd c:\Users\kings\my-monorepo\apps\api
.\..\..\.venv\Scripts\Activate.ps1
uvicorn src.main:app --reload

# Test (Terminal 4)
cd c:\Users\kings\my-monorepo\apps\api
.\test_clustering.ps1 -Action test
```

All three should show "ready" or "connected" messages, and testing should work! 🎉
