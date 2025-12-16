# ELF Update Script - Simple and safe
# Usage: .\update.ps1

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

Write-Host "================================" -ForegroundColor Cyan
Write-Host "  ELF Update" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan
Write-Host ""

# Check we're in a git repo
if (-not (Test-Path ".git")) {
    Write-Host "Error: Not a git repository. Manual update required." -ForegroundColor Red
    exit 1
}

# Show current version
if (Test-Path "VERSION") {
    $version = Get-Content "VERSION" -Raw
    Write-Host "Current version: $version" -ForegroundColor Green
}

# Backup database
Write-Host ""
Write-Host "[1/3] Backing up database..." -ForegroundColor Yellow
$backupDate = Get-Date -Format "yyyyMMdd-HHmmss"
$dbPath = Join-Path $ScriptDir "memory\index.db"
if (Test-Path $dbPath) {
    Copy-Item $dbPath "$dbPath.backup.$backupDate"
    Write-Host "  Backed up to: index.db.backup.$backupDate" -ForegroundColor Gray
} else {
    Write-Host "  No database found, skipping backup" -ForegroundColor Gray
}

# Pull updates
Write-Host ""
Write-Host "[2/3] Pulling updates..." -ForegroundColor Yellow
$status = git status --porcelain
$stashed = $false
if ($status) {
    Write-Host "  Stashing local changes..." -ForegroundColor Gray
    git stash | Out-Null
    $stashed = $true
}

git pull origin main

if ($stashed) {
    Write-Host "  Restoring local changes..." -ForegroundColor Gray
    $result = git stash pop 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  Warning: Merge conflicts in stashed changes. Run 'git stash show -p' to review." -ForegroundColor Yellow
    }
}

# Run migrations
Write-Host ""
Write-Host "[3/3] Running database migrations..." -ForegroundColor Yellow
$migratePath = Join-Path $ScriptDir "scripts\migrate_db.py"
if (Test-Path $migratePath) {
    $pythonCmd = if (Get-Command python3 -ErrorAction SilentlyContinue) { "python3" } else { "python" }
    & $pythonCmd $migratePath (Join-Path $ScriptDir "memory\index.db")
} else {
    Write-Host "  No migration script found, skipping" -ForegroundColor Gray
}

# Done
Write-Host ""
Write-Host "================================" -ForegroundColor Green
Write-Host "  Update complete!" -ForegroundColor Green
Write-Host "================================" -ForegroundColor Green
if (Test-Path "VERSION") {
    $version = Get-Content "VERSION" -Raw
    Write-Host "Now at version: $version" -ForegroundColor Green
}
Write-Host ""
Write-Host "Restart Claude Code to pick up changes."
