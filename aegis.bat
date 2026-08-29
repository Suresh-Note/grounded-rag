<# :
@echo off
powershell -NoProfile -ExecutionPolicy Bypass -Command "$scriptDir = '%~dp0'; Invoke-Expression ([System.IO.File]::ReadAllText('%~f0'))"
exit /b
#>

Set-Location $scriptDir

while ($true) {
    Clear-Host
    Write-Host "======================================================" -ForegroundColor Cyan
    Write-Host "          AEGIS COMPLIANCE STACK CONTROLLER           " -ForegroundColor Cyan
    Write-Host "======================================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "  [1] START Stack   (Launch Ollama, Docker, and UI)" -ForegroundColor Green
    Write-Host "  [2] STOP Stack    (Safely halt containers & free GPU)" -ForegroundColor Red
    Write-Host "  [3] VIEW Logs     (Live Celery & API logs)" -ForegroundColor Yellow
    Write-Host "  [4] EXIT" -ForegroundColor Gray
    Write-Host ""
    Write-Host "======================================================" -ForegroundColor Cyan
    $choice = Read-Host "Select an option (1-4)"

    switch ($choice) {
        "1" {
            Clear-Host
            Write-Host "Starting Aegis Compliance Stack..." -ForegroundColor Green
            & ".\launch.ps1"
            Write-Host ""
            Write-Host "Project is active. Returning to main menu..." -ForegroundColor Cyan
            Start-Sleep -Seconds 2
        }
        "2" {
            Clear-Host
            Write-Host "Stopping containers and reclaiming VRAM..." -ForegroundColor Yellow
            docker compose down
            Stop-Process -Name "ollama", "llama-server" -ErrorAction SilentlyContinue
            Write-Host "Stack cleanly stopped." -ForegroundColor Green
            Start-Sleep -Seconds 2
        }
        "3" {
            Clear-Host
            Write-Host "Streaming live backend logs (Press Ctrl+C to return to menu)..." -ForegroundColor Yellow
            docker compose logs -f api celery_worker
        }
        "4" { 
            exit 
        }
        Default { 
            Write-Host "Invalid selection. Please enter 1, 2, 3, or 4." -ForegroundColor Red 
            Start-Sleep -Seconds 1
        }
    }
}
