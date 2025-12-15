# Emergent Learning Dashboard Launcher
# Double-click to start, close window to stop all servers

$Host.UI.RawUI.WindowTitle = "Emergent Learning Dashboard"

$DashboardPath = $PSScriptRoot
$BackendPath = Join-Path $DashboardPath "backend"
$FrontendPath = Join-Path $DashboardPath "frontend"

Clear-Host
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "        EMERGENT LEARNING DASHBOARD                     " -ForegroundColor Cyan
Write-Host "        Agent Intelligence System                       " -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host ""

# Function to check if a port is responding
function Test-Port {
    param([int]$Port, [string]$Path = "/")
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:$Port$Path" -TimeoutSec 2 -UseBasicParsing -ErrorAction Stop
        return $response.StatusCode -eq 200
    } catch {
        return $false
    }
}

# Function to start backend
function Start-Backend {
    Write-Host "[Starting] Backend API server..." -ForegroundColor Yellow
    Start-Process -FilePath "python" `
        -ArgumentList "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8888" `
        -WorkingDirectory $BackendPath `
        -WindowStyle Hidden
}

# Detect package manager
$PkgMgr = $null
if (Get-Command "bun" -ErrorAction SilentlyContinue) {
    $PkgMgr = "bun"
} elseif (Get-Command "npm" -ErrorAction SilentlyContinue) {
    $PkgMgr = "npm"
} else {
    Write-Host "Error: Neither bun nor npm found. Install from https://bun.sh or https://nodejs.org" -ForegroundColor Red
    exit 1
}

# Function to start frontend
function Start-Frontend {
    Write-Host "[Starting] Frontend dev server (using $PkgMgr)..." -ForegroundColor Yellow
    Start-Process -FilePath $PkgMgr `
        -ArgumentList "run", "dev" `
        -WorkingDirectory $FrontendPath `
        -WindowStyle Hidden
}

# Start servers
Start-Backend
Start-Sleep -Seconds 3
Start-Frontend
Start-Sleep -Seconds 4

# Open browser
Write-Host "[Opening] Browser..." -ForegroundColor Yellow
Start-Process "http://localhost:3001"

Write-Host ""
Write-Host "========================================================" -ForegroundColor Green
Write-Host "  Dashboard is running!                                 " -ForegroundColor Green
Write-Host "                                                        " -ForegroundColor Green
Write-Host "  Frontend:  http://localhost:3001                      " -ForegroundColor Green
Write-Host "  Backend:   http://localhost:8888                      " -ForegroundColor Green
Write-Host "  API Docs:  http://localhost:8888/docs                 " -ForegroundColor Green
Write-Host "                                                        " -ForegroundColor Green
Write-Host "  Close this window to stop all servers                 " -ForegroundColor Green
Write-Host "========================================================" -ForegroundColor Green
Write-Host ""
Write-Host "Press Ctrl+C or close this window to shutdown..." -ForegroundColor DarkGray

# Cleanup function
function Stop-Servers {
    Write-Host ""
    Write-Host "Shutting down servers..." -ForegroundColor Yellow

    # Kill any processes on these ports
    try {
        $portProcesses = Get-NetTCPConnection -LocalPort 3001,8888 -ErrorAction SilentlyContinue |
                         Select-Object -ExpandProperty OwningProcess -Unique
        foreach ($pid in $portProcesses) {
            Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
        }
        Write-Host "  Servers stopped" -ForegroundColor Green
    } catch {
        Write-Host "  Cleanup complete" -ForegroundColor Green
    }

    Write-Host "Goodbye!" -ForegroundColor Cyan
}

# Track restart attempts to avoid spam
$backendRestartCount = 0
$frontendRestartCount = 0
$maxRestarts = 3

# Keep running until closed
try {
    while ($true) {
        Start-Sleep -Seconds 10

        # Health check backend (only if we haven't exceeded restart limit)
        if ($backendRestartCount -lt $maxRestarts) {
            if (-not (Test-Port -Port 8888 -Path "/api/stats")) {
                $backendRestartCount++
                Write-Host "[Warning] Backend not responding (attempt $backendRestartCount/$maxRestarts)..." -ForegroundColor Red
                Start-Backend
                Start-Sleep -Seconds 3
            } else {
                # Reset counter on success
                $backendRestartCount = 0
            }
        }

        # Health check frontend (only if we haven't exceeded restart limit)
        if ($frontendRestartCount -lt $maxRestarts) {
            if (-not (Test-Port -Port 3001)) {
                $frontendRestartCount++
                Write-Host "[Warning] Frontend not responding (attempt $frontendRestartCount/$maxRestarts)..." -ForegroundColor Red
                Start-Frontend
                Start-Sleep -Seconds 3
            } else {
                # Reset counter on success
                $frontendRestartCount = 0
            }
        }
    }
} finally {
    Stop-Servers
}
