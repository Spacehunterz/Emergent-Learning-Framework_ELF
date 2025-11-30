# Record a heuristic in the Emergent Learning Framework

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$BaseDir = Split-Path -Parent $ScriptDir
$MemoryDir = Join-Path $BaseDir "memory"
$DbPath = Join-Path $MemoryDir "index.db"
$HeuristicsDir = Join-Path $MemoryDir "heuristics"

# Ensure heuristics directory exists
New-Item -ItemType Directory -Force -Path $HeuristicsDir | Out-Null

# Prompt for inputs
Write-Host "=== Record Heuristic ===" -ForegroundColor Cyan
Write-Host ""

$domain = Read-Host "Domain"
if ([string]::IsNullOrWhiteSpace($domain)) {
    Write-Host "Error: Domain cannot be empty" -ForegroundColor Red
    exit 1
}

$rule = Read-Host "Rule (the heuristic)"
if ([string]::IsNullOrWhiteSpace($rule)) {
    Write-Host "Error: Rule cannot be empty" -ForegroundColor Red
    exit 1
}

$explanation = Read-Host "Explanation"

$sourceType = Read-Host "Source type (failure/success/observation)"
if ([string]::IsNullOrWhiteSpace($sourceType)) {
    $sourceType = "observation"
}

$confidence = Read-Host "Confidence (0.0-1.0)"
if ([string]::IsNullOrWhiteSpace($confidence)) {
    $confidence = "0.5"
}

# Insert into database
$domainEscaped = $domain -replace "'", "''"
$ruleEscaped = $rule -replace "'", "''"
$explanationEscaped = $explanation -replace "'", "''"
$sourceTypeEscaped = $sourceType -replace "'", "''"

$sql = @"
INSERT INTO heuristics (domain, rule, explanation, source_type, confidence)
VALUES (
    '$domainEscaped',
    '$ruleEscaped',
    '$explanationEscaped',
    '$sourceTypeEscaped',
    $confidence
);
"@

sqlite3.exe $DbPath $sql

$heuristicId = sqlite3.exe $DbPath "SELECT last_insert_rowid();"
Write-Host "Database record created (ID: $heuristicId)" -ForegroundColor Green

# Append to domain markdown file
$domainFile = Join-Path $HeuristicsDir "${domain}.md"
$dateStr = Get-Date -Format "yyyy-MM-dd"

if (-not (Test-Path $domainFile)) {
    $header = @"
# Heuristics: $domain

Generated from failures, successes, and observations in the **$domain** domain.

---

"@
    Set-Content -Path $domainFile -Value $header -Encoding UTF8
}

$entry = @"

## H-$heuristicId: $rule

**Confidence**: $confidence
**Source**: $sourceType
**Created**: $dateStr

$explanation

---

"@

Add-Content -Path $domainFile -Value $entry -Encoding UTF8
Write-Host "Appended to: $domainFile" -ForegroundColor Green

# Git commit
Push-Location $BaseDir
try {
    if (Test-Path ".git") {
        git add $domainFile
        git add $DbPath
        git commit -m "heuristic: $rule" -m "Domain: $domain | Confidence: $confidence" 2>&1 | Out-Null
        Write-Host "Git commit created" -ForegroundColor Green
    } else {
        Write-Host "Warning: Not a git repository. Skipping commit." -ForegroundColor Yellow
    }
} finally {
    Pop-Location
}

Write-Host ""
Write-Host "Heuristic recorded successfully!" -ForegroundColor Green
