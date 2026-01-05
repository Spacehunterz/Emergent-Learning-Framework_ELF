# Emergent Learning Dashboard - Startup Script
# Run this script to start both backend and frontend

$ErrorActionPreference = "Stop"

$DashboardPath = $PSScriptRoot
$BackendPath = Join-Path $DashboardPath "backend"
$FrontendPath = Join-Path $DashboardPath "frontend"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Emergent Learning Dashboard Startup  " -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check Python
Write-Host "[1/4] Checking Python..." -ForegroundColor Yellow
try {
    $pythonVersion = python --version 2>&1
    Write-Host "  Found: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "  ERROR: Python not found. Please install Python 3.9+" -ForegroundColor Red
    exit 1
}

# Check Bun or npm
Write-Host "[2/4] Checking package manager..." -ForegroundColor Yellow
$useBun = $false
$useNpm = $false
try {
    $bunVersion = bun --version 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  Found: bun $bunVersion" -ForegroundColor Green
        $useBun = $true
    }
} catch {
    # Bun not found, try npm
}
if (-not $useBun) {
    try {
        $npmVersion = npm --version 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  Found: npm $npmVersion (bun not available, using npm)" -ForegroundColor Yellow
            $useNpm = $true
        }
    } catch {
        # npm not found either
    }
}
if (-not $useBun -and -not $useNpm) {
    Write-Host "  ERROR: Neither Bun nor npm found. Please install Bun (https://bun.sh) or Node.js (https://nodejs.org)" -ForegroundColor Red
    exit 1
}

# Install backend dependencies
Write-Host "[3/4] Installing backend dependencies..." -ForegroundColor Yellow
Push-Location $BackendPath
pip install -q -r requirements.txt
if ($LASTEXITCODE -ne 0) {
    Write-Host "  ERROR: Failed to install Python dependencies" -ForegroundColor Red
    Pop-Location
    exit 1
}
Write-Host "  Backend dependencies installed" -ForegroundColor Green
Pop-Location

# Install frontend dependencies
Write-Host "[4/4] Installing frontend dependencies..." -ForegroundColor Yellow
Push-Location $FrontendPath
if ($useBun) {
    bun install
} else {
    npm install
}
if ($LASTEXITCODE -ne 0) {
    Write-Host "  ERROR: Failed to install frontend dependencies" -ForegroundColor Red
    Pop-Location
    exit 1
}
Write-Host "  Frontend dependencies installed" -ForegroundColor Green
Pop-Location

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Starting Services                     " -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Start backend
Write-Host "Starting backend (FastAPI)..." -ForegroundColor Yellow
$backendJob = Start-Process -FilePath "python" -ArgumentList "-m", "uvicorn", "main:app", "--reload", "--host", "0.0.0.0", "--port", "8888" -WorkingDirectory $BackendPath -PassThru -NoNewWindow
Start-Sleep -Seconds 2

# Start frontend
Write-Host "Starting frontend (Vite)..." -ForegroundColor Yellow
if ($useBun) {
    $frontendJob = Start-Process -FilePath "bun" -ArgumentList "run", "dev" -WorkingDirectory $FrontendPath -PassThru -NoNewWindow
} else {
    $frontendJob = Start-Process -FilePath "npm" -ArgumentList "run", "dev" -WorkingDirectory $FrontendPath -PassThru -NoNewWindow
}
Start-Sleep -Seconds 3

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  Dashboard is running!                 " -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "  Frontend: http://localhost:3001" -ForegroundColor Cyan
Write-Host "  Backend:  http://localhost:8888" -ForegroundColor Cyan
Write-Host "  API Docs: http://localhost:8888/docs" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Press Ctrl+C to stop" -ForegroundColor Yellow
Write-Host ""

# Wait for exit
try {
    while ($true) {
        Start-Sleep -Seconds 1
    }
} finally {
    Write-Host "Shutting down..." -ForegroundColor Yellow
    Stop-Process -Id $backendJob.Id -Force -ErrorAction SilentlyContinue
    Stop-Process -Id $frontendJob.Id -Force -ErrorAction SilentlyContinue
}
