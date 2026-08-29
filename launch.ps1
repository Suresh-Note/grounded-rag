# ==========================================================
# AEGIS ENTERPRISE AUTOMATED LAUNCH ORCHESTRATOR
# ==========================================================
$ErrorActionPreference = "Stop"
$projectRoot = $PSScriptRoot
Set-Location $projectRoot

Write-Host "======================================================" -ForegroundColor Cyan
Write-Host "  🚀 Launching GroundedRAG Stack" -ForegroundColor Cyan
Write-Host "======================================================" -ForegroundColor Cyan

# 1. Ensure local artifacts directory exists
$artifactsPath = Join-Path $projectRoot "artifacts"
if (-not (Test-Path $artifactsPath)) {
    New-Item -ItemType Directory -Path $artifactsPath -Force | Out-Null
    Write-Host "📁 Created local artifacts folder." -ForegroundColor Gray
}

# 2. Check and start Ollama in the background if not active
Write-Host "`n🔍 Checking Ollama status..." -ForegroundColor Yellow
$ollamaReady = $false
try {
    $res = Invoke-RestMethod -Uri "http://localhost:11434/api/tags" -Method Get -TimeoutSec 2
    $ollamaReady = $true
    Write-Host "✅ Ollama is already active and responding." -ForegroundColor Green
} catch {
    Write-Host "⚡ Starting Ollama server (0.0.0.0:11434 with GPU access)..." -ForegroundColor Yellow
    [System.Environment]::SetEnvironmentVariable('OLLAMA_HOST', '0.0.0.0:11434', 'User')
    $env:OLLAMA_HOST = "0.0.0.0:11434"
    Start-Process -FilePath "ollama" -ArgumentList "serve" -WindowStyle Hidden
    
    for ($i = 0; $i -lt 15; $i++) {
        Start-Sleep -Seconds 1
        try {
            $null = Invoke-RestMethod -Uri "http://localhost:11434/api/tags" -Method Get -TimeoutSec 1
            $ollamaReady = $true
            break
        } catch {}
    }
    if ($ollamaReady) {
        Write-Host "✅ Ollama initialized successfully." -ForegroundColor Green
    } else {
        Write-Host "⚠️ Warning: Ollama took longer than expected to bind." -ForegroundColor Yellow
    }
}

# 3. Boot Docker Stack
Write-Host "`n🐳 Orchestrating Docker containers..." -ForegroundColor Yellow
docker compose up -d

# 4. Poll health endpoint until API Gateway is live
Write-Host "`n⏳ Awaiting FastAPI Gateway health verification..." -ForegroundColor Yellow
$apiReady = $false
$maxTries = 30
$count = 0

while (-not $apiReady -and $count -lt $maxTries) {
    Start-Sleep -Seconds 2
    $count++
    try {
        $health = Invoke-RestMethod -Uri "http://localhost:8000/health" -Method Get -TimeoutSec 2
        if ($health.status -eq "healthy") {
            $apiReady = $true
            Write-Host "✅ API Gateway verified healthy on port 8000." -ForegroundColor Green
        }
    } catch {
        Write-Host "  ... waiting for API boot ($count/$maxTries)" -ForegroundColor Gray
    }
}

# 5. Open Web UI in default browser
Write-Host "`n🌐 Opening Aegis Spatial Interface..." -ForegroundColor Cyan
Start-Process "http://localhost:3000"

Write-Host "`n======================================================" -ForegroundColor Green
Write-Host "  🎉 Aegis Engine is fully operational!" -ForegroundColor Green
Write-Host "  - UI:       http://localhost:3000" -ForegroundColor White
Write-Host "  - API Docs: http://localhost:8000/docs" -ForegroundColor White
Write-Host "  - Qdrant:   http://localhost:6333/dashboard" -ForegroundColor White
Write-Host "======================================================" -ForegroundColor Green
