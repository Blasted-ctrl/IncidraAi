#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Set up Redis for local development - Windows version

.DESCRIPTION
    Provides multiple ways to get Redis running on Windows:
    1. Docker (fastest if working)
    2. WSL with Redis
    3. Python mock Redis for testing
    4. Native Windows Redis (via Git repository)

.PARAMETER Method
    Installation method: docker, wsl, python, or help (default: help)
#>

param(
    [ValidateSet('docker', 'wsl', 'python', 'help')]
    [string]$Method = 'help'
)

$ErrorActionPreference = "Continue"

Write-Host "`n╔═════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║  Redis Setup for Windows - Incident Triage          ║" -ForegroundColor Cyan
Write-Host "╚═════════════════════════════════════════════════════╝`n" -ForegroundColor Cyan

# ============================================================================
# Option 1: Docker (simplest)
# ============================================================================

if ($Method -eq 'docker') {
    Write-Host "🐳 Setting up Redis with Docker..." -ForegroundColor Cyan
    
    Write-Host "`nChecking Docker availability..." -ForegroundColor Gray
    
    try {
        $dockerVersion = docker --version
        Write-Host "✅ Docker found: $dockerVersion" -ForegroundColor Green
    }
    catch {
        Write-Host "❌ Docker not found or not working" -ForegroundColor Red
        Write-Host "   Try: choco install docker-desktop" -ForegroundColor Yellow
        Write-Host "   Or download from: https://www.docker.com/products/docker-desktop" -ForegroundColor Yellow
        exit 1
    }
    
    Write-Host "`nStarting Redis container..." -ForegroundColor Cyan
    
    try {
        # Stop any existing Redis container
        Write-Host "Stopping existing container (if any)..." -ForegroundColor Gray
        docker stop incident-triage-redis 2>$null | Out-Null
        docker rm incident-triage-redis 2>$null | Out-Null
        
        # Start Redis
        Write-Host "Starting Redis container..." -ForegroundColor Yellow
        docker run -d `
            --name incident-triage-redis `
            -p 6379:6379 `
            redis:7-alpine `
            redis-server --appendonly yes
        
        Start-Sleep -Seconds 2
        
        # Verify it's running
        $status = docker ps --filter "name=incident-triage-redis" --format "table {{.Names}}"
        
        if ($status -match "incident-triage-redis") {
            Write-Host "✅ Redis is running in Docker!" -ForegroundColor Green
            Write-Host "   Container: incident-triage-redis" -ForegroundColor Gray
            Write-Host "   Port: 6379" -ForegroundColor Gray
            Write-Host "`n   To stop: docker stop incident-triage-redis" -ForegroundColor Gray
            Write-Host "   To start again: docker start incident-triage-redis" -ForegroundColor Gray
            
            # Test connection
            docker exec incident-triage-redis redis-cli ping
        }
        else {
            Write-Host "❌ Failed to start Redis container" -ForegroundColor Red
            exit 1
        }
    }
    catch {
        Write-Host "❌ Docker command failed: $_" -ForegroundColor Red
        exit 1
    }
    
    exit 0
}

# ============================================================================
# Option 2: WSL with Redis
# ============================================================================

if ($Method -eq 'wsl') {
    Write-Host "🐧 Setting up Redis with WSL..." -ForegroundColor Cyan
    
    Write-Host "`nChecking WSL status..." -ForegroundColor Gray
    
    $wslDist = wsl.exe --list --quiet 2>$null
    
    if (-not $wslDist) {
        Write-Host "❌ No WSL distributions found" -ForegroundColor Red
        Write-Host "`nInstalling Ubuntu..." -ForegroundColor Yellow
        
        try {
            # Install Ubuntu 22.04 (takes 5-10 minutes)
            wsl.exe --install Ubuntu-22.04 --no-launch
            
            Write-Host "`n✅ Ubuntu installed!" -ForegroundColor Green
            Write-Host "   Initialize it by running: wsl" -ForegroundColor Gray
            Write-Host "   Then come back and run this script again" -ForegroundColor Gray
        }
        catch {
            Write-Host "❌ Failed to install WSL: $_" -ForegroundColor Red
            Write-Host "`nAlternatively, try Docker: $PSCommandPath -Method docker" -ForegroundColor Yellow
            exit 1
        }
    }
    else {
        Write-Host "✅ WSL distribution found" -ForegroundColor Green
        
        # Start Redis in WSL
        Write-Host "`nStarting Redis in WSL..." -ForegroundColor Yellow
        
        try {
            wsl.exe -d Ubuntu-22.04 -- sudo service redis-server start 2>$null
            
            # Install Redis if needed
            Write-Host "Ensuring Redis is installed..." -ForegroundColor Gray
            wsl.exe -d Ubuntu-22.04 -- sudo apt-get update 2>&1 | Out-Null
            wsl.exe -d Ubuntu-22.04 -- sudo apt-get install -y redis-server 2>&1 | Out-Null
            
            # Start it
            wsl.exe -d Ubuntu-22.04 -- sudo service redis-server start
            
            Start-Sleep -Seconds 2
            
            # Test it
            $ping = wsl.exe -d Ubuntu-22.04 -- redis-cli ping
            
            if ($ping -match "PONG") {
                Write-Host "✅ Redis is running in WSL!" -ForegroundColor Green
                Write-Host "   Distribution: Ubuntu-22.04" -ForegroundColor Gray
                Write-Host "   Port: 6379" -ForegroundColor Gray
                Write-Host "`n   To test: wsl redis-cli ping" -ForegroundColor Gray
                Write-Host "   To stop: wsl sudo service redis-server stop" -ForegroundColor Gray
            }
        }
        catch {
            Write-Host "❌ Failed to start Redis in WSL: $_" -ForegroundColor Red
            exit 1
        }
    }
    
    exit 0
}

# ============================================================================
# Option 3: Python Mock Redis (for development/testing)
# ============================================================================

if ($Method -eq 'python') {
    Write-Host "🐍 Setting up Python mock Redis (development mode)..." -ForegroundColor Cyan
    
    Write-Host "`nInstalling fakeredis package..." -ForegroundColor Gray
    
    try {
        python -m pip install fakeredis[aioredis] -q
        Write-Host "✅ fakeredis installed" -ForegroundColor Green
    }
    catch {
        Write-Host "❌ Failed to install fakeredis: $_" -ForegroundColor Red
        exit 1
    }
    
    Write-Host "`n📝 Creating mock Redis server..." -ForegroundColor Cyan
    
    $mockRedisScript = @'
#!/usr/bin/env python3
"""Mock Redis server for local development"""

import fakeredis
import socket
from redis.server import Server

def main():
    """Start mock Redis server"""
    print("🚀 Starting mock Redis server (development mode)...")
    print("   Port: 6379")
    print("   Type: fakeredis (in-memory, no persistence)")
    print("   Warning: Data will be lost on restart")
    print("\n   Press Ctrl+C to stop")
    print("   Note: This is for development only\n")
    
    # Create fake Redis server
    redis_server = fakeredis.FakeStrictRedis(host='localhost', port=6379)
    
    # Verify it works
    try:
        redis_server.ping()
        print("✅ Mock Redis is ready!")
        print("   You can connect with: redis-cli")
    except Exception as e:
        print(f"❌ Error: {e}")
        exit(1)
    
    # Keep server running
    import time
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\n👋 Mock Redis server stopped")

if __name__ == '__main__':
    main()
'@

    $scriptPath = Join-Path $PSScriptRoot "mock_redis.py"
    Set-Content -Path $scriptPath -Value $mockRedisScript
    
    Write-Host "✅ Mock Redis script created: $scriptPath" -ForegroundColor Green
    Write-Host "`n📌 To run the mock Redis server:" -ForegroundColor Cyan
    Write-Host "   python mock_redis.py" -ForegroundColor Yellow
    Write-Host "`n⚠️  Note: fakeredis runs in-memory and doesn't persist data" -ForegroundColor Yellow
    Write-Host "    This is suitable for local development only" -ForegroundColor Yellow
    
    exit 0
}

# ============================================================================
# Help & Default
# ============================================================================

if ($Method -eq 'help' -or $Method -eq '') {
    Write-Host "📚 Redis Setup Methods for Windows`n" -ForegroundColor Cyan
    
    Write-Host "Method 1: DOCKER (Recommended if Docker works)" -ForegroundColor Green
    Write-Host "  .\setup_redis.ps1 -Method docker" -ForegroundColor Yellow
    Write-Host "  Pros: Most reliable, persistent data" -ForegroundColor Gray
    Write-Host "  Cons: Requires Docker Desktop" -ForegroundColor Gray
    Write-Host ""
    
    Write-Host "Method 2: WSL (Linux on Windows)" -ForegroundColor Green
    Write-Host "  .\setup_redis.ps1 -Method wsl" -ForegroundColor Yellow
    Write-Host "  Pros: Native Redis, persistent data" -ForegroundColor Gray
    Write-Host "  Cons: Takes 10 min first time, requires setup" -ForegroundColor Gray
    Write-Host ""
    
    Write-Host "Method 3: PYTHON Mock Redis (Development)" -ForegroundColor Green
    Write-Host "  .\setup_redis.ps1 -Method python" -ForegroundColor Yellow
    Write-Host "  Pros: No extra dependencies, instant setup" -ForegroundColor Gray
    Write-Host "  Cons: In-memory only, no persistence" -ForegroundColor Gray
    Write-Host ""
    
    Write-Host "Quick Decision:" -ForegroundColor Cyan
    Write-Host "  If Docker works: Use Method 1" -ForegroundColor Gray
    Write-Host "  If Docker broken: Use Method 2 or 3" -ForegroundColor Gray
    Write-Host "  For quick testing: Use Method 3" -ForegroundColor Gray
    Write-Host ""
    
    Write-Host "Recommended commands:" -ForegroundColor Yellow
    Write-Host "  # Try Docker first:" -ForegroundColor Gray
    Write-Host "  .\setup_redis.ps1 -Method docker" -ForegroundColor White
    Write-Host ""
    Write-Host "  # If that fails, try Python:" -ForegroundColor Gray
    Write-Host "  .\setup_redis.ps1 -Method python" -ForegroundColor White
    Write-Host "  python mock_redis.py" -ForegroundColor White
    Write-Host ""
}
