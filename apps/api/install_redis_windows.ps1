#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Install native Redis for Windows using pre-built binaries
    
.DESCRIPTION
    Downloads and installs Redis from the native Windows builds
    (maintained by Microsoft and community)
#>

Write-Host "`n======================================================" -ForegroundColor Cyan
Write-Host "  Redis Windows Native Installation" -ForegroundColor Cyan
Write-Host "======================================================`n" -ForegroundColor Cyan

$redisUrl = "https://github.com/tporadowski/redis/releases/download/v7.0.11/Redis-x64-7.0.11.zip"
$downloadPath = "$env:TEMP\redis-windows.zip"
$installPath = "C:\Redis"
$tempExtract = "$env:TEMP\Redis-x64-7.0.11"

Write-Host "Downloading Redis for Windows..." -ForegroundColor Cyan
Write-Host "   URL: $redisUrl" -ForegroundColor Gray
Write-Host "   Size: ~10 MB" -ForegroundColor Gray
Write-Host ""

try {
    # Download
    Write-Host "Downloading..." -ForegroundColor Yellow
    Invoke-WebRequest -Uri $redisUrl -OutFile $downloadPath -ErrorAction Stop
    Write-Host "[OK] Downloaded to: $downloadPath" -ForegroundColor Green
    
    # Extract
    Write-Host "`nExtracting..." -ForegroundColor Cyan
    Expand-Archive -Path $downloadPath -DestinationPath $env:TEMP -Force
    Write-Host "[OK] Extracted" -ForegroundColor Green
    
    # Create install directory
    if (-not (Test-Path $installPath)) {
        New-Item -ItemType Directory -Path $installPath -Force | Out-Null
    }
    
    # Move files
    if (Test-Path $tempExtract) {
        Copy-Item -Path "$tempExtract\*" -Destination $installPath -Recurse -Force
        Write-Host "[OK] Copied to: $installPath" -ForegroundColor Green
    }
    else {
        Write-Host "[ERROR] Extracted folder not found at $tempExtract" -ForegroundColor Red
        exit 1
    }
    
    # Add to PATH
    $currentPath = [Environment]::GetEnvironmentVariable("PATH", "User")
    if ($currentPath -notlike "*$installPath*") {
        $newPath = $currentPath + ";" + $installPath
        [Environment]::SetEnvironmentVariable("PATH", $newPath, "User")
        $env:PATH = $newPath
        Write-Host "[OK] Added to PATH" -ForegroundColor Green
    }
    
    # Cleanup
    Remove-Item $downloadPath -Force -ErrorAction SilentlyContinue
    Remove-Item $tempExtract -Recurse -Force -ErrorAction SilentlyContinue
    
    Write-Host "`n[SUCCESS] Redis installed successfully!" -ForegroundColor Green
    Write-Host "   Location: $installPath" -ForegroundColor Gray
    Write-Host "   Binary: redis-server.exe" -ForegroundColor Gray
    
    Write-Host "`nTo start Redis:" -ForegroundColor Cyan
    Write-Host "   redis-server" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Then in another terminal:" -ForegroundColor Cyan
    Write-Host "   redis-cli ping" -ForegroundColor Yellow
    Write-Host ""
    
}
catch {
    Write-Host "[ERROR] Installation failed: $_" -ForegroundColor Red
    exit 1
}
