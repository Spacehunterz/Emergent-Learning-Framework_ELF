# Emergent Learning Framework - Windows Installer
# Run with: PowerShell -ExecutionPolicy Bypass -File install.ps1 [options]

param(
    [switch]$CoreOnly,
    [switch]$NoDashboard,
    [switch]$NoSwarm,
    [switch]$All,
    [switch]$Help
)

$ErrorActionPreference = "Stop"

if ($Help) {
    Write-Host "Usage: install.ps1 [OPTIONS]"
    Write-Host ""
    Write-Host "Options:"
    Write-Host "  -CoreOnly      Install only core (query system, hooks, golden rules)"
    Write-Host "  -NoDashboard   Skip dashboard installation"
    Write-Host "  -NoSwarm       Skip swarm/conductor installation"
    Write-Host "  -All           Install everything (default)"
    Write-Host "  -Help          Show this help"
    Write-Host ""
    Write-Host "Components:"
    Write-Host "  Core:      Query system, learning hooks, golden rules, CLAUDE.md"
    Write-Host "  Dashboard: React UI for monitoring (localhost:3000)"
    Write-Host "  Swarm:     Multi-agent conductor, agent personas"
    exit 0
}

# Default: install all
$InstallCore = $true
$InstallDashboard = -not $NoDashboard -and -not $CoreOnly
$InstallSwarm = -not $NoSwarm -and -not $CoreOnly

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  Emergent Learning Framework Installer" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "Installation mode:"
Write-Host "  Core:      " -NoNewline; Write-Host "Yes" -ForegroundColor Green
Write-Host "  Dashboard: " -NoNewline
if ($InstallDashboard) { Write-Host "Yes" -ForegroundColor Green } else { Write-Host "No" -ForegroundColor Yellow }
Write-Host "  Swarm:     " -NoNewline
if ($InstallSwarm) { Write-Host "Yes" -ForegroundColor Green } else { Write-Host "No" -ForegroundColor Yellow }
Write-Host ""

# Get paths
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ClaudeDir = Join-Path $env:USERPROFILE ".claude"
$EmergentLearningDir = Join-Path $ClaudeDir "emergent-learning"
$HooksDir = Join-Path $ClaudeDir "hooks"
$SettingsFile = Join-Path $ClaudeDir "settings.json"

# Check prerequisites
Write-Host "[Checking] Prerequisites..." -ForegroundColor Yellow

# Check Python - prefer python3 if available
$pythonCmd = "python"
if (Get-Command python3 -ErrorAction SilentlyContinue) {
    $pythonCmd = "python3"
    $pythonVersion = python3 --version 2>&1
    Write-Host "  Python: $pythonVersion" -ForegroundColor Green
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    $pythonCmd = "python"
    $pythonVersion = python --version 2>&1
    Write-Host "  Python: $pythonVersion" -ForegroundColor Green
} else {
    Write-Host "  ERROR: Python not found. Please install Python 3.8+" -ForegroundColor Red
    exit 1
}

# Check Bun/Node (only if installing dashboard)
$hasBun = $false
if ($InstallDashboard) {
    try {
        $bunVersion = bun --version 2>&1
        Write-Host "  Bun: $bunVersion" -ForegroundColor Green
        $hasBun = $true
    } catch {
        try {
            $nodeVersion = node --version 2>&1
            Write-Host "  Node: $nodeVersion" -ForegroundColor Green
        } catch {
            Write-Host "  ERROR: Neither Bun nor Node.js found (needed for dashboard)" -ForegroundColor Red
            Write-Host "  Run with -NoDashboard to skip, or install Node.js/Bun" -ForegroundColor Yellow
            exit 1
        }
    }
}

Write-Host ""
Write-Host "[Creating] Directory structure..." -ForegroundColor Yellow

# Create directories
$MemoryDir = Join-Path $EmergentLearningDir "memory"
$directories = @(
    $ClaudeDir,
    $EmergentLearningDir,
    $MemoryDir,
    (Join-Path $MemoryDir "failures"),
    (Join-Path $MemoryDir "successes"),
    (Join-Path $EmergentLearningDir "query"),
    (Join-Path $EmergentLearningDir "ceo-inbox"),
    $HooksDir,
    (Join-Path $HooksDir "learning-loop")
)

if ($InstallSwarm) {
    $AgentsDir = Join-Path $EmergentLearningDir "agents"
    $directories += @(
        $AgentsDir,
        (Join-Path $AgentsDir "researcher"),
        (Join-Path $AgentsDir "architect"),
        (Join-Path $AgentsDir "skeptic"),
        (Join-Path $AgentsDir "creative"),
        (Join-Path $EmergentLearningDir "conductor")
    )
}

foreach ($dir in $directories) {
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }
}
Write-Host "  Created directory structure" -ForegroundColor Green

# === CORE INSTALLATION ===
Write-Host ""
Write-Host "[Installing] Core components..." -ForegroundColor Yellow

$srcDir = Join-Path (Join-Path $ScriptDir "src") "emergent-learning"
$srcQueryDir = Join-Path $srcDir "query"
$srcMemoryDir = Join-Path $srcDir "memory"
$dstQueryDir = Join-Path $EmergentLearningDir "query"

# Copy core files
Copy-Item -Path (Join-Path $srcQueryDir "query.py") -Destination (Join-Path $dstQueryDir "query.py") -Force
Copy-Item -Path (Join-Path $srcMemoryDir "golden-rules.md") -Destination (Join-Path $MemoryDir "golden-rules.md") -Force
Copy-Item -Path (Join-Path $srcMemoryDir "init_db.sql") -Destination (Join-Path $MemoryDir "init_db.sql") -Force
Write-Host "  Copied query system" -ForegroundColor Green

# Copy hooks
$srcHooksDir = Join-Path $ScriptDir "src"
$hooksSource = Join-Path (Join-Path $srcHooksDir "hooks") "learning-loop"
$learningLoopDir = Join-Path $HooksDir "learning-loop"
Copy-Item -Path (Join-Path $hooksSource "*.py") -Destination $learningLoopDir -Force
Write-Host "  Copied learning hooks" -ForegroundColor Green

# Copy scripts
$scriptsDst = Join-Path $EmergentLearningDir "scripts"
New-Item -ItemType Directory -Path $scriptsDst -Force | Out-Null
$scriptsSource = Join-Path $srcDir "scripts"
if (Test-Path $scriptsSource) {
    Get-ChildItem -Path $scriptsSource -Filter "*.sh" -ErrorAction SilentlyContinue | ForEach-Object {
        Copy-Item -Path $_.FullName -Destination $scriptsDst -Force
    }
}
Write-Host "  Copied recording scripts" -ForegroundColor Green

# Initialize database
$dbPath = Join-Path $MemoryDir "index.db"
$sqlFile = Join-Path $MemoryDir "init_db.sql"

if (-not (Test-Path $dbPath)) {
    try {
        sqlite3 $dbPath ".read $sqlFile" 2>&1 | Out-Null
        Write-Host "  Initialized database" -ForegroundColor Green
    } catch {
        & $pythonCmd (Join-Path $dstQueryDir "query.py") --validate 2>&1 | Out-Null
        Write-Host "  Initialized database via Python" -ForegroundColor Green
    }
} else {
    Write-Host "  Database already exists (kept existing)" -ForegroundColor Yellow
}

# === SWARM INSTALLATION ===
if ($InstallSwarm) {
    Write-Host ""
    Write-Host "[Installing] Swarm components..." -ForegroundColor Yellow

    # Copy conductor
    $conductorSrc = Join-Path $srcDir "conductor"
    $conductorDst = Join-Path $EmergentLearningDir "conductor"
    Get-ChildItem -Path $conductorSrc -Filter "*.py" | ForEach-Object {
        Copy-Item -Path $_.FullName -Destination $conductorDst -Force
    }
    Get-ChildItem -Path $conductorSrc -Filter "*.sql" -ErrorAction SilentlyContinue | ForEach-Object {
        Copy-Item -Path $_.FullName -Destination $conductorDst -Force
    }
    Write-Host "  Copied conductor module" -ForegroundColor Green

    # Copy agent personas
    $srcAgentsDir = Join-Path $srcDir "agents"
    $dstAgentsDir = Join-Path $EmergentLearningDir "agents"
    $agents = @("researcher", "architect", "skeptic", "creative")
    foreach ($agent in $agents) {
        $agentSrc = Join-Path $srcAgentsDir $agent
        $agentDst = Join-Path $dstAgentsDir $agent
        if (Test-Path $agentSrc) {
            Get-ChildItem -Path $agentSrc | ForEach-Object {
                Copy-Item -Path $_.FullName -Destination $agentDst -Force
            }
        }
    }
    Write-Host "  Copied agent personas" -ForegroundColor Green

    # Copy swarm command
    $commandsDir = Join-Path $ClaudeDir "commands"
    New-Item -ItemType Directory -Path $commandsDir -Force | Out-Null
    $srcCommandsDir = Join-Path (Join-Path $ScriptDir "src") "commands"
    $swarmCmd = Join-Path $srcCommandsDir "swarm.md"
    if (Test-Path $swarmCmd) {
        Copy-Item -Path $swarmCmd -Destination $commandsDir -Force
    }
    Write-Host "  Copied /swarm command" -ForegroundColor Green

    # Copy agent coordination plugin
    $claudePluginsDir = Join-Path $ClaudeDir "plugins"
    $pluginsDir = Join-Path $claudePluginsDir "agent-coordination"
    $pluginsUtilsDir = Join-Path $pluginsDir "utils"
    $pluginsHooksDir = Join-Path $pluginsDir "hooks"
    New-Item -ItemType Directory -Path $pluginsUtilsDir -Force | Out-Null
    New-Item -ItemType Directory -Path $pluginsHooksDir -Force | Out-Null

    $srcPluginsDir = Join-Path (Join-Path $ScriptDir "src") "plugins"
    $pluginSrc = Join-Path $srcPluginsDir "agent-coordination"
    $pluginSrcUtils = Join-Path $pluginSrc "utils"
    $pluginSrcHooks = Join-Path $pluginSrc "hooks"
    if (Test-Path $pluginSrc) {
        Get-ChildItem -Path $pluginSrcUtils -Filter "*.py" -ErrorAction SilentlyContinue | ForEach-Object {
            Copy-Item -Path $_.FullName -Destination $pluginsUtilsDir -Force
        }
        Get-ChildItem -Path $pluginSrcHooks -Filter "*.py" -ErrorAction SilentlyContinue | ForEach-Object {
            Copy-Item -Path $_.FullName -Destination $pluginsHooksDir -Force
        }
        Get-ChildItem -Path $pluginSrcHooks -Filter "*.json" -ErrorAction SilentlyContinue | ForEach-Object {
            Copy-Item -Path $_.FullName -Destination $pluginsHooksDir -Force
        }
    }
    Write-Host "  Copied agent coordination plugin" -ForegroundColor Green
}

# === DASHBOARD INSTALLATION ===
if ($InstallDashboard) {
    Write-Host ""
    Write-Host "[Installing] Dashboard..." -ForegroundColor Yellow

    $dashboardSrc = Join-Path $srcDir "dashboard-app"
    $dashboardDst = Join-Path $EmergentLearningDir "dashboard-app"

    if (Test-Path $dashboardSrc) {
        if (Test-Path $dashboardDst) {
            Remove-Item -Path $dashboardDst -Recurse -Force
        }
        Copy-Item -Path $dashboardSrc -Destination $dashboardDst -Recurse
        Write-Host "  Copied dashboard" -ForegroundColor Green

        # Install frontend dependencies
        $frontendDir = Join-Path $dashboardDst "frontend"
        if (Test-Path $frontendDir) {
            Set-Location $frontendDir
            if ($hasBun) {
                bun install 2>&1 | Out-Null
            } else {
                npm install 2>&1 | Out-Null
            }
            Write-Host "  Installed frontend dependencies" -ForegroundColor Green
        }

        # Install backend dependencies
        $backendDir = Join-Path $dashboardDst "backend"
        if (Test-Path $backendDir) {
            pip install -q fastapi uvicorn aiofiles websockets 2>&1 | Out-Null
            Write-Host "  Installed backend dependencies" -ForegroundColor Green
        }

        Set-Location $ScriptDir
    }
}

# === CHECK CLAUDE CODE ===
Write-Host ""
Write-Host "[Checking] Claude Code installation..." -ForegroundColor Yellow
try {
    $claudeVersion = claude --version 2>&1
    Write-Host "  Claude Code: $claudeVersion" -ForegroundColor Green
} catch {
    Write-Host "  WARNING: Claude Code not found in PATH" -ForegroundColor Yellow
    Write-Host "  ELF requires Claude Code to work. Install from: https://claude.ai/download" -ForegroundColor Yellow
    Write-Host "  Continuing anyway (you can install Claude Code later)..." -ForegroundColor Yellow
}

# === CONFIGURE SETTINGS.JSON ===
Write-Host ""
Write-Host "[Configuring] Claude Code settings..." -ForegroundColor Yellow

$hookLearningLoop = Join-Path $HooksDir "learning-loop"
$preToolHook = Join-Path $hookLearningLoop "pre_tool_learning.py"
$postToolHook = Join-Path $hookLearningLoop "post_tool_learning.py"

# Backup existing settings if present
if (Test-Path $SettingsFile) {
    $backupFile = Join-Path $ClaudeDir "settings.json.backup"
    Copy-Item -Path $SettingsFile -Destination $backupFile -Force
    Write-Host "  Backed up existing settings to settings.json.backup" -ForegroundColor Green
}

$settings = @{}
if (Test-Path $SettingsFile) {
    try {
        $settings = Get-Content $SettingsFile -Raw | ConvertFrom-Json -AsHashtable
    } catch {
        $settings = @{}
    }
}

if (-not $settings.ContainsKey("hooks")) {
    $settings["hooks"] = @{}
}

# Create ELF hooks - use detected python command
$elfPreHook = @{
    "matcher" = "Task"
    "hooks" = @(
        @{
            "type" = "command"
            "command" = "$pythonCmd `"$preToolHook`""
        }
    )
}

$elfPostHook = @{
    "matcher" = "Task"
    "hooks" = @(
        @{
            "type" = "command"
            "command" = "$pythonCmd `"$postToolHook`""
        }
    )
}

# Merge with existing hooks (don't overwrite user's other hooks)
if (-not $settings["hooks"].ContainsKey("PreToolUse")) {
    $settings["hooks"]["PreToolUse"] = @()
}
if (-not $settings["hooks"].ContainsKey("PostToolUse")) {
    $settings["hooks"]["PostToolUse"] = @()
}

# Remove any existing ELF hooks (to avoid duplicates on reinstall)
# Only remove hooks where matcher="Task" AND command contains "learning-loop"
$settings["hooks"]["PreToolUse"] = @($settings["hooks"]["PreToolUse"] | Where-Object {
    -not ($_.matcher -eq "Task" -and $_.hooks -and ($_.hooks | Where-Object { $_.command -like "*learning-loop*" }))
})
$settings["hooks"]["PostToolUse"] = @($settings["hooks"]["PostToolUse"] | Where-Object {
    -not ($_.matcher -eq "Task" -and $_.hooks -and ($_.hooks | Where-Object { $_.command -like "*learning-loop*" }))
})

# Add ELF hooks using ArrayList to avoid nested array issues
[System.Collections.ArrayList]$preHooks = @($settings["hooks"]["PreToolUse"])
$preHooks.Add($elfPreHook) | Out-Null
$settings["hooks"]["PreToolUse"] = $preHooks

[System.Collections.ArrayList]$postHooks = @($settings["hooks"]["PostToolUse"])
$postHooks.Add($elfPostHook) | Out-Null
$settings["hooks"]["PostToolUse"] = $postHooks

# Write without BOM (UTF8 BOM can break JSON parsers)
$jsonContent = $settings | ConvertTo-Json -Depth 10
[System.IO.File]::WriteAllText($SettingsFile, $jsonContent, [System.Text.UTF8Encoding]::new($false))
Write-Host "  Configured hooks (preserved existing hooks)" -ForegroundColor Green

# === CLAUDE.MD ===
$claudeMdDst = Join-Path $ClaudeDir "CLAUDE.md"
$templatesDir = Join-Path $ScriptDir "templates"
$claudeMdSrc = Join-Path $templatesDir "CLAUDE.md.template"

if (-not (Test-Path $claudeMdDst)) {
    if (Test-Path $claudeMdSrc) {
        Copy-Item -Path $claudeMdSrc -Destination $claudeMdDst
        Write-Host "  Created CLAUDE.md" -ForegroundColor Green
    }
} else {
    Write-Host "  CLAUDE.md exists (not overwritten)" -ForegroundColor Yellow
}

# === DONE ===
Write-Host ""
Write-Host "============================================" -ForegroundColor Green
Write-Host "  Installation Complete!" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Green
Write-Host ""
Write-Host "Installed:"
Write-Host "  [+] Core (query system, hooks, golden rules)" -ForegroundColor Green
if ($InstallDashboard) {
    Write-Host "  [+] Dashboard (localhost:3000)" -ForegroundColor Green
}
if ($InstallSwarm) {
    Write-Host "  [+] Swarm (conductor, agent personas)" -ForegroundColor Green
}
Write-Host ""
Write-Host "Next steps:"
Write-Host "  1. Review ~/.claude/CLAUDE.md"
if ($InstallDashboard) {
    Write-Host "  2. Start dashboard: cd ~/.claude/emergent-learning/dashboard-app && ./run-dashboard.ps1"
}
Write-Host "  3. Use Claude Code normally - it will now query the building!"
Write-Host ""
