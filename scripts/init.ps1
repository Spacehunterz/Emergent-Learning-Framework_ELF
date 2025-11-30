# Initialize the Emergent Learning Framework

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$BaseDir = Split-Path -Parent $ScriptDir

Write-Host "=== Initializing Emergent Learning Framework ===" -ForegroundColor Cyan
Write-Host "Base directory: $BaseDir"
Write-Host ""

# Create directory structure
Write-Host "Creating directory structure..."
$directories = @(
    "memory\failures",
    "memory\successes",
    "memory\heuristics",
    "experiments\active",
    "experiments\completed",
    "cycles",
    "ceo-inbox",
    "agents",
    "logs",
    "query",
    "scripts"
)

foreach ($dir in $directories) {
    $path = Join-Path $BaseDir $dir
    New-Item -ItemType Directory -Force -Path $path | Out-Null
}
Write-Host "✓ Directory structure created" -ForegroundColor Green

# Initialize git repository
Push-Location $BaseDir
try {
    if (-not (Test-Path ".git")) {
        Write-Host ""
        Write-Host "Initializing git repository..."
        git init

        # Create .gitignore
        $gitignoreContent = @"
# Logs
logs/*.log
*.tmp

# OS files
.DS_Store
Thumbs.db

# Editor files
.vscode/
.idea/
*.swp
*.swo
"@
        Set-Content -Path ".gitignore" -Value $gitignoreContent -Encoding UTF8

        Write-Host "✓ Git repository initialized" -ForegroundColor Green
    } else {
        Write-Host "✓ Git repository already exists" -ForegroundColor Green
    }
} finally {
    Pop-Location
}

# Initialize database
$DbPath = Join-Path $BaseDir "memory\index.db"
$SchemaPath = Join-Path $BaseDir "memory\schema.sql"

if (Test-Path $SchemaPath) {
    Write-Host ""
    Write-Host "Initializing database..."
    Get-Content $SchemaPath | sqlite3.exe $DbPath
    Write-Host "✓ Database initialized" -ForegroundColor Green
} else {
    Write-Host "Warning: schema.sql not found at $SchemaPath" -ForegroundColor Yellow
    Write-Host "Database initialization skipped"
}

# Create initial golden rules
$GoldenRulesPath = Join-Path $BaseDir "memory\golden-rules.md"
if (-not (Test-Path $GoldenRulesPath)) {
    Write-Host ""
    Write-Host "Creating golden rules..."
    $goldenRules = @"
# Golden Rules

These are the most validated and critical heuristics - promoted from the general pool after proving their value repeatedly.

---

## Rule 1: Make It Work, Then Make It Right

**Confidence**: 0.9
**Source**: observation
**Domain**: architecture

First focus on getting a working solution, even if imperfect. Then refactor and optimize. Trying to build the perfect architecture from the start often leads to analysis paralysis.

**Validated**: Proven across multiple projects
**Violations**: Premature optimization often causes delays

---

## Rule 2: Explicit is Better Than Implicit

**Confidence**: 0.95
**Source**: failure
**Domain**: coordination

When coordinating between agents, explicit communication of intent, state, and expectations prevents misunderstandings. Hidden assumptions are the enemy of reliable systems.

**Validated**: Critical for agent coordination
**Violations**: Implicit assumptions cause cascading failures

---

## Rule 3: Fail Fast, Learn Faster

**Confidence**: 0.85
**Source**: observation
**Domain**: debugging

Design systems to fail quickly and obviously rather than silently degrading. Fast feedback loops accelerate learning.

**Validated**: Speeds up debugging cycles
**Violations**: Silent failures waste time

---

## Rule 4: Document Decisions, Not Just Code

**Confidence**: 0.9
**Source**: success
**Domain**: coordination

Record the "why" behind decisions, not just the "what". Future you (or future agents) will thank you.

**Validated**: Prevents repeated mistakes
**Violations**: Forgotten context leads to regression

---

*These rules are living documents. As we learn more, they evolve.*
"@
    Set-Content -Path $GoldenRulesPath -Value $goldenRules -Encoding UTF8
    Write-Host "✓ Golden rules created" -ForegroundColor Green
} else {
    Write-Host "✓ Golden rules already exist" -ForegroundColor Green
}

# Create README if it does not exist
$ReadmePath = Join-Path $BaseDir "README.md"
if (-not (Test-Path $ReadmePath)) {
    Write-Host ""
    Write-Host "Creating README..."
    $readme = @"
# Emergent Learning Framework

A systematic approach to learning from failures, extracting heuristics, and running deliberate experiments.

## Directory Structure

``````
emergent-learning/
├── memory/              # The knowledge base
│   ├── failures/        # Documented failures
│   ├── successes/       # Documented successes
│   ├── heuristics/      # Extracted rules by domain
│   ├── schema.sql       # Database schema
│   └── index.db         # SQLite index
├── experiments/         # Active learning experiments
│   ├── active/          # Currently running
│   └── completed/       # Finished experiments
├── cycles/              # Try/Break cycle logs
├── ceo-inbox/           # Decisions requiring human input
├── agents/              # Agent configurations
├── logs/                # Execution logs
├── query/               # Query tools and dashboards
└── scripts/             # Helper scripts
``````

## Quick Start

### Initialize the Framework

``````bash
./scripts/init.sh         # Bash
./scripts/init.ps1        # PowerShell
``````

### Record a Failure

``````bash
./scripts/record-failure.sh      # Bash
./scripts/record-failure.ps1     # PowerShell
``````

### Record a Heuristic

``````bash
./scripts/record-heuristic.sh    # Bash
./scripts/record-heuristic.ps1   # PowerShell
``````

### Start an Experiment

``````bash
./scripts/start-experiment.sh    # Bash
./scripts/start-experiment.ps1   # PowerShell
``````

## Philosophy

1. **Fail Deliberately**: Create controlled experiments to test assumptions
2. **Extract Patterns**: Convert experiences into reusable heuristics
3. **Validate Continuously**: Track which rules prove helpful vs harmful
4. **Promote the Best**: Elevate proven heuristics to golden rules
5. **Stay Humble**: All knowledge is provisional and subject to revision

## The Learning Loop

``````
Try → Break → Analyze → Extract → Validate → Promote
``````

Every cycle adds to our collective intelligence.
"@
    Set-Content -Path $ReadmePath -Value $readme -Encoding UTF8
    Write-Host "✓ README created" -ForegroundColor Green
} else {
    Write-Host "✓ README already exists" -ForegroundColor Green
}

# Initial git commit
Write-Host ""
Write-Host "Creating initial git commit..."
Push-Location $BaseDir
try {
    git add .
    git commit -m "init: Initialize Emergent Learning Framework" -m "Created directory structure, database, and golden rules" 2>&1 | Out-Null
    Write-Host "✓ Initial commit created" -ForegroundColor Green
} catch {
    Write-Host "Already committed or no changes" -ForegroundColor Yellow
} finally {
    Pop-Location
}

Write-Host ""
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "✓ Framework initialized successfully!" -ForegroundColor Green
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:"
Write-Host "  1. Review golden rules: memory\golden-rules.md"
Write-Host "  2. Record your first failure: .\scripts\record-failure.ps1"
Write-Host "  3. Start an experiment: .\scripts\start-experiment.ps1"
Write-Host ""
Write-Host "Happy learning!"
