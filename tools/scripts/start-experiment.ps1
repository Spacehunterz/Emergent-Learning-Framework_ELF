# Start a new experiment in the Emergent Learning Framework

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$BaseDir = Split-Path -Parent $ScriptDir
$MemoryDir = Join-Path $BaseDir "memory"
$DbPath = Join-Path $MemoryDir "index.db"
$ExperimentsDir = Join-Path $BaseDir "experiments\active"

# Ensure experiments directory exists
New-Item -ItemType Directory -Force -Path $ExperimentsDir | Out-Null

# Prompt for inputs
Write-Host "=== Start Experiment ===" -ForegroundColor Cyan
Write-Host ""

$name = Read-Host "Experiment Name"
if ([string]::IsNullOrWhiteSpace($name)) {
    Write-Host "Error: Name cannot be empty" -ForegroundColor Red
    exit 1
}

$hypothesis = Read-Host "Hypothesis"
if ([string]::IsNullOrWhiteSpace($hypothesis)) {
    Write-Host "Error: Hypothesis cannot be empty" -ForegroundColor Red
    exit 1
}

$successCriteria = Read-Host "Success Criteria"

$failureCriteria = Read-Host "Failure Criteria"

# Generate folder name
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$folderName = $name.ToLower() -replace '[^a-z0-9-]', '-' -replace '-+', '-' -replace '^-|-$', ''
$folderPath = Join-Path $ExperimentsDir "${timestamp}_${folderName}"
$relativeFolder = "experiments/active/${timestamp}_${folderName}"

# Create experiment folder
New-Item -ItemType Directory -Force -Path $folderPath | Out-Null

# Create hypothesis.md
$dateStr = Get-Date -Format "yyyy-MM-dd"
$hypothesisContent = @"
# Experiment: $name

**Started**: $dateStr
**Status**: Active

## Hypothesis

$hypothesis

## Success Criteria

$successCriteria

## Failure Criteria

$failureCriteria

## Variables

[What parameters are we varying?]

## Controls

[What are we keeping constant?]

## Methodology

[How will we conduct this experiment?]

## Expected Outcomes

[What do we expect to learn?]
"@

Set-Content -Path (Join-Path $folderPath "hypothesis.md") -Value $hypothesisContent -Encoding UTF8

# Create log.md
$logContent = @"
# Experiment Log: $name

## Cycle 1

**Date**: $dateStr
**Status**: Planned

### Try

[What did we attempt?]

### Break

[What did we observe? What broke?]

### Analysis

[What does this tell us?]

### Learning

[What heuristic or insight emerged?]

---

"@

Set-Content -Path (Join-Path $folderPath "log.md") -Value $logContent -Encoding UTF8
Write-Host "Created experiment folder: $folderPath" -ForegroundColor Green

# Insert into database
$nameEscaped = $name -replace "'", "''"
$hypothesisEscaped = $hypothesis -replace "'", "''"
$relativeFolderEscaped = $relativeFolder -replace "'", "''"

$sql = @"
INSERT INTO experiments (name, hypothesis, status, folder_path)
VALUES (
    '$nameEscaped',
    '$hypothesisEscaped',
    'active',
    '$relativeFolderEscaped'
);
"@

sqlite3.exe $DbPath $sql

$experimentId = sqlite3.exe $DbPath "SELECT last_insert_rowid();"
Write-Host "Database record created (ID: $experimentId)" -ForegroundColor Green

# Git commit
Push-Location $BaseDir
try {
    if (Test-Path ".git") {
        git add $folderPath
        git add $DbPath
        git commit -m "experiment: Start '$name'" -m "Hypothesis: $hypothesis" 2>&1 | Out-Null
        Write-Host "Git commit created" -ForegroundColor Green
    } else {
        Write-Host "Warning: Not a git repository. Skipping commit." -ForegroundColor Yellow
    }
} finally {
    Pop-Location
}

Write-Host ""
Write-Host "Experiment started successfully!" -ForegroundColor Green
Write-Host "Folder: $folderPath"
Write-Host "Edit hypothesis at: $(Join-Path $folderPath 'hypothesis.md')"
Write-Host "Log cycles at: $(Join-Path $folderPath 'log.md')"
