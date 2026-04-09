#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Install Celery and Redis dependencies for the incident triage API
    
.DESCRIPTION
    Installs required packages: celery, redis, psycopg2-binary, faker
    
.PARAMETER SkipVenvCheck
    Skip checking for virtual environment activation
#>

param(
    [switch]$SkipVenvCheck
)

$ErrorActionPreference = "Stop"

Write-Host "`n╔═════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║  Celery + Redis Dependencies Installer              ║" -ForegroundColor Cyan
Write-Host "╚═════════════════════════════════════════════════════╝`n" -ForegroundColor Cyan

# Check if in venv
if (-not $SkipVenvCheck) {
    $pythonPath = (Get-Command python -ErrorAction SilentlyContinue).Source
    
    if (-not $pythonPath -or $pythonPath -notmatch "\.venv") {
        Write-Host "⚠️  Warning: Not running in a virtual environment" -ForegroundColor Yellow
        Write-Host "   Current Python: $pythonPath`n" -ForegroundColor Gray
        
        $choice = Read-Host "Install dependencies anyway? (y/n)"
        if ($choice -ne 'y') {
            Write-Host "Cancelled." -ForegroundColor Red
            exit 0
        }
    }
}

Write-Host "📦 Installing Celery and dependencies..." -ForegroundColor Cyan
Write-Host ""

# List of packages to install
$packages = @(
    "celery>=5.3.0",
    "redis>=5.0.0",
    "psycopg2-binary>=2.9.0",
    "faker>=20.0.0"
)

Write-Host "Packages to install:" -ForegroundColor Gray
foreach ($pkg in $packages) {
    Write-Host "  • $pkg" -ForegroundColor Gray
}

Write-Host ""

# Install packages
try {
    foreach ($package in $packages) {
        Write-Host "Installing $package..." -ForegroundColor Yellow
        python -m pip install $package
        Write-Host "✅ $package installed`n" -ForegroundColor Green
    }
    
    Write-Host "✅ All dependencies installed successfully!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Cyan
    Write-Host "  1. Start Redis: redis-server" -ForegroundColor Gray
    Write-Host "  2. Start Celery: celery -A src.celery_app worker --loglevel=info" -ForegroundColor Gray
    Write-Host "  3. Start API: uvicorn src.main:app --reload" -ForegroundColor Gray
    Write-Host "  4. Test: .\test_clustering.ps1 -Action test" -ForegroundColor Gray
    Write-Host ""
}
catch {
    Write-Host "❌ Installation failed" -ForegroundColor Red
    Write-Host "Error: $($_)" -ForegroundColor Yellow
    exit 1
}
