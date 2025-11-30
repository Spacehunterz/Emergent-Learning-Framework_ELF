# Record a failure in the Emergent Learning Framework

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$BaseDir = Split-Path -Parent $ScriptDir
$MemoryDir = Join-Path $BaseDir "memory"
$DbPath = Join-Path $MemoryDir "index.db"
$FailuresDir = Join-Path $MemoryDir "failures"

# Ensure failures directory exists
New-Item -ItemType Directory -Force -Path $FailuresDir | Out-Null

# Prompt for inputs
Write-Host "=== Record Failure ===" -ForegroundColor Cyan
Write-Host ""

$title = Read-Host "Title"
if ([string]::IsNullOrWhiteSpace($title)) {
    Write-Host "Error: Title cannot be empty" -ForegroundColor Red
    exit 1
}

$domain = Read-Host "Domain (coordination/architecture/debugging/etc)"
if ([string]::IsNullOrWhiteSpace($domain)) {
    Write-Host "Error: Domain cannot be empty" -ForegroundColor Red
    exit 1
}

$severity = Read-Host "Severity (1-5)"
if ([string]::IsNullOrWhiteSpace($severity)) {
    $severity = "3"
}

$tags = Read-Host "Tags (comma-separated)"

Write-Host "Summary (press Enter on empty line when done):"
$summaryLines = @()
while ($true) {
    $line = Read-Host
    if ([string]::IsNullOrWhiteSpace($line)) { break }
    $summaryLines += $line
}
$summary = $summaryLines -join "`n"

# Generate filename
$datePrefix = Get-Date -Format "yyyyMMdd"
$filenameTitle = $title.ToLower() -replace '[^a-z0-9-]', '-' -replace '-+', '-' -replace '^-|-$', ''
$filename = "${datePrefix}_${filenameTitle}.md"
$filepath = Join-Path $FailuresDir $filename
$relativePath = "memory/failures/$filename"

# Create markdown file
$dateStr = Get-Date -Format "yyyy-MM-dd"
$summaryFirst = ($summaryLines | Select-Object -First 1) -replace "'", "''"

$markdownContent = @"
# $title

**Domain**: $domain
**Severity**: $severity
**Tags**: $tags
**Date**: $dateStr

## Summary

$summary

## What Happened

[Describe the failure in detail]

## Root Cause

[What was the underlying issue?]

## Impact

[What were the consequences?]

## Prevention

[What heuristic or practice would prevent this?]

## Related

- **Experiments**:
- **Heuristics**:
- **Similar Failures**:
"@

Set-Content -Path $filepath -Value $markdownContent -Encoding UTF8
Write-Host "Created: $filepath" -ForegroundColor Green

# Insert into database
$titleEscaped = $title -replace "'", "''"
$summaryEscaped = $summary -replace "'", "''"
$tagsEscaped = $tags -replace "'", "''"
$domainEscaped = $domain -replace "'", "''"

$sql = @"
INSERT INTO learnings (type, filepath, title, summary, tags, domain, severity)
VALUES (
    'failure',
    '$relativePath',
    '$titleEscaped',
    '$summaryEscaped',
    '$tagsEscaped',
    '$domainEscaped',
    $severity
);
"@

sqlite3.exe $DbPath $sql

$lastId = sqlite3.exe $DbPath "SELECT last_insert_rowid();"
Write-Host "Database record created (ID: $lastId)" -ForegroundColor Green

# Git commit
Push-Location $BaseDir
try {
    if (Test-Path ".git") {
        git add $filepath
        git add $DbPath
        git commit -m "failure: $title" -m "Domain: $domain | Severity: $severity" 2>&1 | Out-Null
        Write-Host "Git commit created" -ForegroundColor Green
    } else {
        Write-Host "Warning: Not a git repository. Skipping commit." -ForegroundColor Yellow
    }
} finally {
    Pop-Location
}

Write-Host ""
Write-Host "Failure recorded successfully!" -ForegroundColor Green
Write-Host "Edit the full details at: $filepath"
