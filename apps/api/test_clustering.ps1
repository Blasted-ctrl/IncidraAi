#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Test the Incident Triage Clustering API
    
.DESCRIPTION
    PowerShell script to test clustering endpoints using Invoke-WebRequest
    
.PARAMETER ApiBase
    Base URL for the API (default: http://localhost:8000)
    
.PARAMETER LogIds
    Comma-separated log UUIDs to cluster
    
.PARAMETER Action
    Action to perform: test, status, stats, dlq (default: test)
    
.PARAMETER TaskId
    Task ID to check status for

.EXAMPLE
    # Test clustering job
    .\test_clustering.ps1 -Action test
    
    # Check task status
    .\test_clustering.ps1 -Action status -TaskId abc123
    
    # View statistics
    .\test_clustering.ps1 -Action stats
#>

param(
    [string]$ApiBase = "http://localhost:8000",
    [string]$LogIds = "550e8400-e29b-41d4-a716-446655440000,550e8400-e29b-41d4-a716-446655440001",
    [ValidateSet('test', 'status', 'stats', 'dlq', 'health')]
    [string]$Action = 'test',
    [string]$TaskId
)

$ErrorActionPreference = "Continue"

# ============================================================================
# Helper Functions
# ============================================================================

function Test-ApiHealth {
    Write-Host "🏥 Checking API health..." -ForegroundColor Cyan
    
    try {
        $response = Invoke-WebRequest -Uri "$ApiBase/health" -Method GET -ErrorAction Stop
        $health = $response.Content | ConvertFrom-Json
        
        Write-Host "✅ API is healthy" -ForegroundColor Green
        Write-Host "   Status: $($health.status)" -ForegroundColor Gray
        return $true
    }
    catch {
        Write-Host "❌ API is not responding at $ApiBase" -ForegroundColor Red
        Write-Host "   Error: $($_.Exception.Message)" -ForegroundColor Yellow
        return $false
    }
}

function Submit-ClusteringJob {
    Write-Host "📤 Submitting clustering job..." -ForegroundColor Cyan
    
    # Convert log IDs string to array
    $ids = $LogIds -split ','
    
    # Build request body
    $body = @{
        log_ids = $ids
        skip_duplicates = $true
    } | ConvertTo-Json
    
    Write-Host "   Log IDs: $($ids.Count) logs" -ForegroundColor Gray
    Write-Host "   Payload: $body" -ForegroundColor Gray
    
    try {
        $response = Invoke-WebRequest `
            -Uri "$ApiBase/api/clustering/cluster-logs" `
            -Method POST `
            -ContentType "application/json" `
            -Body $body `
            -ErrorAction Stop
        
        $result = $response.Content | ConvertFrom-Json
        
        Write-Host "✅ Job submitted successfully" -ForegroundColor Green
        Write-Host "   Task ID: $($result.task_id)" -ForegroundColor Green
        Write-Host "   Status: $($result.status)" -ForegroundColor Green
        Write-Host "   Message: $($result.message)" -ForegroundColor Gray
        
        return $result.task_id
    }
    catch {
        Write-Host "❌ Failed to submit clustering job" -ForegroundColor Red
        Write-Host "   Error: $($_.Exception.Message)" -ForegroundColor Yellow
        if ($_.ErrorDetails) {
            Write-Host "   Details: $($_.ErrorDetails.Message)" -ForegroundColor Yellow
        }
        return $null
    }
}

function Check-TaskStatus {
    param([string]$Id)
    
    Write-Host "🔍 Checking task status..." -ForegroundColor Cyan
    Write-Host "   Task ID: $Id" -ForegroundColor Gray
    
    try {
        $response = Invoke-WebRequest `
            -Uri "$ApiBase/api/clustering/tasks/$Id" `
            -Method GET `
            -ErrorAction Stop
        
        $result = $response.Content | ConvertFrom-Json
        
        Write-Host "✅ Task status retrieved" -ForegroundColor Green
        Write-Host "   Status: $($result.status)" -ForegroundColor Green
        
        if ($result.result) {
            Write-Host "   Result:" -ForegroundColor Gray
            Write-Host "     - Cluster ID: $($result.result.cluster_id)" -ForegroundColor Gray
            Write-Host "     - Logs Clustered: $($result.result.logs_clustered)" -ForegroundColor Gray
            Write-Host "     - Logs Deduplicated: $($result.result.logs_deduplicated)" -ForegroundColor Gray
            Write-Host "     - Status: $($result.result.status)" -ForegroundColor Gray
        }
        
        if ($result.error) {
            Write-Host "   Error: $($result.error)" -ForegroundColor Red
        }
        
        return $result
    }
    catch {
        Write-Host "❌ Failed to check task status" -ForegroundColor Red
        Write-Host "   Error: $($_.Exception.Message)" -ForegroundColor Yellow
        return $null
    }
}

function Get-ClustertingStats {
    Write-Host "📊 Retrieving clustering statistics..." -ForegroundColor Cyan
    
    try {
        $response = Invoke-WebRequest `
            -Uri "$ApiBase/api/clustering/stats" `
            -Method GET `
            -ErrorAction Stop
        
        $stats = $response.Content | ConvertFrom-Json
        
        Write-Host "✅ Statistics retrieved" -ForegroundColor Green
        Write-Host "   Deduplication:" -ForegroundColor Gray
        Write-Host "     - TTL: $($stats.deduplication.cache_ttl_hours) hours" -ForegroundColor Gray
        Write-Host "     - Redis DB: $($stats.deduplication.redis_db)" -ForegroundColor Gray
        Write-Host "   Active Tasks:" -ForegroundColor Gray
        
        if ($stats.active_tasks) {
            foreach ($queue in $stats.active_tasks.PSObject.Properties) {
                Write-Host "     - $($queue.Name): $($queue.Value) tasks" -ForegroundColor Gray
            }
        }
        else {
            Write-Host "     - No active tasks" -ForegroundColor Gray
        }
        
        return $stats
    }
    catch {
        Write-Host "❌ Failed to retrieve statistics" -ForegroundColor Red
        Write-Host "   Error: $($_.Exception.Message)" -ForegroundColor Yellow
        return $null
    }
}

function Get-DeadLetterQueue {
    Write-Host "💀 Retrieving dead-letter queue..." -ForegroundColor Cyan
    
    try {
        $response = Invoke-WebRequest `
            -Uri "$ApiBase/api/clustering/dead-letter-queue?limit=10" `
            -Method GET `
            -ErrorAction Stop
        
        $dlq = $response.Content | ConvertFrom-Json
        
        Write-Host "✅ Dead-letter queue retrieved" -ForegroundColor Green
        Write-Host "   Failed tasks: $($dlq.count)" -ForegroundColor Gray
        
        if ($dlq.count -gt 0) {
            Write-Host "   Recent failures:" -ForegroundColor Gray
            foreach ($record in $dlq.records | Select-Object -First 3) {
                Write-Host "     - Task: $($record.task_name)" -ForegroundColor Yellow
                Write-Host "       ID: $($record.task_id)" -ForegroundColor Gray
                Write-Host "       Error: $($record.error_message)" -ForegroundColor Red
                Write-Host "       Created: $($record.created_at)" -ForegroundColor Gray
            }
        }
        
        return $dlq
    }
    catch {
        Write-Host "❌ Failed to retrieve dead-letter queue" -ForegroundColor Red
        Write-Host "   Error: $($_.Exception.Message)" -ForegroundColor Yellow
        return $null
    }
}

# ============================================================================
# Main Script
# ============================================================================

Write-Host "`n" 
Write-Host "╔═══════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║  Incident Triage - Clustering API Test                   ║" -ForegroundColor Cyan
Write-Host "╚═══════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# Check API health first
if (-not (Test-ApiHealth)) {
    Write-Host "`n❌ Cannot proceed without API health check passing" -ForegroundColor Red
    Write-Host "   Make sure the API is running:" -ForegroundColor Yellow
    Write-Host "   uvicorn src.main:app --reload" -ForegroundColor Yellow
    exit 1
}

Write-Host ""

# Execute requested action
switch ($Action) {
    'test' {
        $taskId = Submit-ClusteringJob
        
        if ($taskId) {
            Write-Host ""
            Write-Host "⏳ Waiting 3 seconds before checking status..." -ForegroundColor Gray
            Start-Sleep -Seconds 3
            
            Check-TaskStatus -Id $taskId
        }
    }
    
    'status' {
        if (-not $TaskId) {
            Write-Host "❌ TaskId parameter required for status check" -ForegroundColor Red
            Write-Host "   Usage: .\test_clustering.ps1 -Action status -TaskId <task_id>" -ForegroundColor Yellow
            exit 1
        }
        
        Check-TaskStatus -Id $TaskId
    }
    
    'stats' {
        Get-ClustertingStats
    }
    
    'dlq' {
        Get-DeadLetterQueue
    }
    
    'health' {
        Test-ApiHealth
    }
}

Write-Host "`n"
Write-Host "Script completed" -ForegroundColor Green
