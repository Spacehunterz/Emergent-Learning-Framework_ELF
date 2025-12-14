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

# Helper function: Copy only if source and destination are different paths
# Fixes issue #12 where cloning directly to target directory causes Copy-Item to fail
function Copy-IfDifferent {
    param(
        [string]$Source,
        [string]$Destination,
        [switch]$Recurse
    )

    # Check if source exists
    if (-not (Test-Path $Source)) {
        return $false
    }

    # Resolve source to absolute path
    $resolvedSrc = (Resolve-Path $Source).Path

    # For destination, we need to handle both existing and non-existing paths
    # If destination is a directory and source is a file, append the filename
    if ((Test-Path $Destination) -and (Test-Path $Destination -PathType Container) -and (Test-Path $Source -PathType Leaf)) {
        $resolvedDst = Join-Path (Resolve-Path $Destination).Path (Split-Path $Source -Leaf)
    } elseif (Test-Path $Destination) {
        $resolvedDst = (Resolve-Path $Destination).Path
    } else {
        # Destination doesn't exist - normalize the path
        $resolvedDst = [System.IO.Path]::GetFullPath($Destination)
    }

    # Normalize paths for comparison (handle trailing slashes, case-insensitivity on Windows)
    $normalizedSrc = $resolvedSrc.TrimEnd('\', '/').ToLower()
    $normalizedDst = $resolvedDst.TrimEnd('\', '/').ToLower()

    if ($normalizedSrc -eq $normalizedDst) {
        # Source and destination are the same - skip copy
        return $false
    }

    if ($Recurse) {
        Copy-Item -Path $Source -Destination $Destination -Recurse -Force
    } else {
        Copy-Item -Path $Source -Destination $Destination -Force
    }
    return $true
}

# Helper to check if we're running from the target directory (in-place install)
function Test-InPlaceInstall {
    param(
        [string]$ScriptDir,
        [string]$TargetDir
    )

    $normalizedScript = $ScriptDir.TrimEnd('\', '/').ToLower()
    $normalizedTarget = $TargetDir.TrimEnd('\', '/').ToLower()

    return $normalizedScript -eq $normalizedTarget
}

if ($Help) {
    Write-Host "Usage: install.ps1 [OPTIONS]"
    Write-Host ""
    Write-Host "Options:"
    Write-Host "  -CoreOnly      Install only core (query system, hooks, golden rules)"
    Write-Host "  -NoDashboard   Skip dashboard installation (skips visual UI at localhost:3000)"
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
Write-Host "Estimated installation time: ~2 minutes" -ForegroundColor Cyan
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

# Detect in-place installation (cloned directly to target)
$InPlaceInstall = Test-InPlaceInstall -ScriptDir $ScriptDir -TargetDir $EmergentLearningDir
if ($InPlaceInstall) {
    Write-Host "  Detected: In-place installation (repo cloned to target directory)" -ForegroundColor Cyan
    Write-Host "  Note: Skipping self-copy operations" -ForegroundColor Cyan
    Write-Host ""
}

# Check prerequisites
Write-Host "[Step 1/5] Checking prerequisites..." -ForegroundColor Yellow

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
    Write-Host "  Fix: Install Python from https://python.org" -ForegroundColor Yellow
    Write-Host "  Then: Run this installer again" -ForegroundColor Yellow
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
            Write-Host "  Fix option 1: Run with -NoDashboard to skip dashboard" -ForegroundColor Yellow
            Write-Host "  Fix option 2: Install Bun (https://bun.sh) or Node.js (https://nodejs.org)" -ForegroundColor Yellow
            Write-Host "  Then: Run this installer again" -ForegroundColor Yellow
            exit 1
        }
    }
}

Write-Host ""
Write-Host "[OK] Prerequisites met" -ForegroundColor Green
Write-Host ""
Write-Host "[Step 2/5] Creating directory structure..." -ForegroundColor Yellow

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
Write-Host "  Created directory structure (7 directories for core)" -ForegroundColor Green

# === CORE INSTALLATION ===
Write-Host ""
Write-Host "[Step 3/5] Installing core components..." -ForegroundColor Yellow

$srcDir = $ScriptDir
$srcQueryDir = Join-Path $srcDir "query"
$srcTemplatesDir = Join-Path $srcDir "templates"
$dstQueryDir = Join-Path $EmergentLearningDir "query"

# Copy core files (using safe copy that skips if src=dst)
Copy-IfDifferent -Source (Join-Path $srcQueryDir "query.py") -Destination (Join-Path $dstQueryDir "query.py") | Out-Null
Copy-IfDifferent -Source (Join-Path $srcTemplatesDir "golden-rules.md") -Destination (Join-Path $MemoryDir "golden-rules.md") | Out-Null
Copy-IfDifferent -Source (Join-Path $srcTemplatesDir "init_db.sql") -Destination (Join-Path $MemoryDir "init_db.sql") | Out-Null
Write-Host "  Copied query system" -ForegroundColor Green

# Copy hooks (these go to a different location, so always safe)
$srcHooksDir = $ScriptDir
$hooksSource = Join-Path (Join-Path $srcHooksDir "hooks") "learning-loop"
$learningLoopDir = Join-Path $HooksDir "learning-loop"
Copy-Item -Path (Join-Path $hooksSource "*.py") -Destination $learningLoopDir -Force
Write-Host "  Copied learning hooks" -ForegroundColor Green

# Copy scripts (using safe copy)
$scriptsDst = Join-Path $EmergentLearningDir "scripts"
New-Item -ItemType Directory -Path $scriptsDst -Force | Out-Null
$scriptsSource = Join-Path $srcDir "scripts"
if (Test-Path $scriptsSource) {
    Get-ChildItem -Path $scriptsSource -Filter "*.sh" -ErrorAction SilentlyContinue | ForEach-Object {
        Copy-IfDifferent -Source $_.FullName -Destination $scriptsDst | Out-Null
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

    # Copy conductor (using safe copy)
    $conductorSrc = Join-Path $srcDir "conductor"
    $conductorDst = Join-Path $EmergentLearningDir "conductor"
    Get-ChildItem -Path $conductorSrc -Filter "*.py" | ForEach-Object {
        Copy-IfDifferent -Source $_.FullName -Destination $conductorDst | Out-Null
    }
    Get-ChildItem -Path $conductorSrc -Filter "*.sql" -ErrorAction SilentlyContinue | ForEach-Object {
        Copy-IfDifferent -Source $_.FullName -Destination $conductorDst | Out-Null
    }
    Write-Host "  Copied conductor module" -ForegroundColor Green

    # Copy agent personas (using safe copy)
    $srcAgentsDir = Join-Path $srcDir "agents"
    $dstAgentsDir = Join-Path $EmergentLearningDir "agents"
    $agents = @("researcher", "architect", "skeptic", "creative")
    foreach ($agent in $agents) {
        $agentSrc = Join-Path $srcAgentsDir $agent
        $agentDst = Join-Path $dstAgentsDir $agent
        if (Test-Path $agentSrc) {
            Get-ChildItem -Path $agentSrc | ForEach-Object {
                Copy-IfDifferent -Source $_.FullName -Destination $agentDst | Out-Null
            }
        }
    }
    Write-Host "  Copied agent personas" -ForegroundColor Green

    # Copy swarm command (goes to different location, always safe)
    $commandsDir = Join-Path $ClaudeDir "commands"
    New-Item -ItemType Directory -Path $commandsDir -Force | Out-Null
    $srcCommandsDir = Join-Path $ScriptDir "commands"
    $swarmCmd = Join-Path $srcCommandsDir "swarm.md"
    if (Test-Path $swarmCmd) {
        Copy-Item -Path $swarmCmd -Destination $commandsDir -Force
    }
    Write-Host "  Copied /swarm command" -ForegroundColor Green

    # Copy agent coordination plugin (goes to different location, always safe)
    $claudePluginsDir = Join-Path $ClaudeDir "plugins"
    $pluginsDir = Join-Path $claudePluginsDir "agent-coordination"
    $pluginsUtilsDir = Join-Path $pluginsDir "utils"
    $pluginsHooksDir = Join-Path $pluginsDir "hooks"
    New-Item -ItemType Directory -Path $pluginsUtilsDir -Force | Out-Null
    New-Item -ItemType Directory -Path $pluginsHooksDir -Force | Out-Null

    $srcPluginsDir = Join-Path $ScriptDir "plugins"
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
        # For in-place install, skip the copy entirely
        if (-not $InPlaceInstall) {
            if (Test-Path $dashboardDst) {
                Remove-Item -Path $dashboardDst -Recurse -Force
            }
            Copy-Item -Path $dashboardSrc -Destination $dashboardDst -Recurse
            Write-Host "  Copied dashboard" -ForegroundColor Green
        } else {
            Write-Host "  Dashboard already in place (in-place install)" -ForegroundColor Cyan
        }

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
Write-Host "[Step 5/5] Checking optional components..." -ForegroundColor Yellow
try {
    $claudeVersion = claude --version 2>&1
    Write-Host "  Claude Code: $claudeVersion" -ForegroundColor Green
} catch {
    Write-Host "  WARNING: Claude Code not found (optional for now)" -ForegroundColor Yellow
    Write-Host "  Note: ELF requires Claude Code to work. Install from: https://claude.ai/download" -ForegroundColor Yellow
    Write-Host "  Installation will continue, but ELF won't be functional until you install Claude Code." -ForegroundColor Yellow
}

# === CONFIGURE SETTINGS.JSON ===
Write-Host ""
Write-Host "[Step 4/5] Configuring Claude Code settings..." -ForegroundColor Yellow
Write-Host ""
Write-Host "  About to modify settings.json:" -ForegroundColor Cyan
Write-Host "  - Adding PreToolUse hook (runs before each task)"
Write-Host "  - Adding PostToolUse hook (runs after each task)"
Write-Host "  - Preserving your existing hooks (if any)"
Write-Host "  - Creating backup at settings.json.backup"
Write-Host ""

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

# Validate settings.json
try {
    Get-Content $SettingsFile -Raw | ConvertFrom-Json | Out-Null
    Write-Host "  [OK] settings.json validated" -ForegroundColor Green
} catch {
    Write-Host "  [ERROR] settings.json validation failed!" -ForegroundColor Red
    Write-Host "  Fix: Restore from backup: Copy-Item $ClaudeDir\settings.json.backup $SettingsFile" -ForegroundColor Yellow
    Write-Host "  Then: Run installer again" -ForegroundColor Yellow
    exit 1
}

# === CLAUDE.MD SETUP (Issue #13: Interactive prompts) ===
$claudeMdDst = Join-Path $ClaudeDir "CLAUDE.md"
$templatesDir = Join-Path $ScriptDir "templates"
$claudeMdSrc = Join-Path $templatesDir "CLAUDE.md.template"

if (-not (Test-Path $claudeMdDst)) {
    # No existing CLAUDE.md - fresh install
    if (Test-Path $claudeMdSrc) {
        Copy-Item -Path $claudeMdSrc -Destination $claudeMdDst
        Write-Host "  Created CLAUDE.md" -ForegroundColor Green
    }
} else {
    # Existing CLAUDE.md found - check if ELF already configured
    $existingContent = Get-Content $claudeMdDst -Raw
    if ($existingContent -match "Emergent Learning Framework") {
        Write-Host "  CLAUDE.md already contains ELF configuration (skipped)" -ForegroundColor Green
    } else {
        # Existing config without ELF - prompt user for action
        Write-Host ""
        Write-Host "  Existing CLAUDE.md detected!" -ForegroundColor Yellow
        Write-Host ""
        Write-Host "  How would you like to add ELF configuration?" -ForegroundColor Cyan
        Write-Host "    [1] Merge    - Keep your config, add ELF below (Recommended)" -ForegroundColor White
        Write-Host "    [2] Replace  - Use ELF only (your config backed up)" -ForegroundColor White
        Write-Host "    [3] Skip     - Don't modify CLAUDE.md" -ForegroundColor White
        Write-Host ""

        $choice = Read-Host "  Enter choice (1/2/3)"

        switch ($choice) {
            "1" {
                # Merge: Keep existing + append ELF
                $backupFile = Join-Path $ClaudeDir "CLAUDE.md.backup"
                Copy-Item -Path $claudeMdDst -Destination $backupFile -Force

                $elfContent = Get-Content $claudeMdSrc -Raw
                $mergedContent = @"
$existingContent


# ==============================================
# EMERGENT LEARNING FRAMEWORK - AUTO-APPENDED
# ==============================================

$elfContent
"@
                [System.IO.File]::WriteAllText($claudeMdDst, $mergedContent, [System.Text.UTF8Encoding]::new($false))
                Write-Host "  Merged ELF with your config (backup: CLAUDE.md.backup)" -ForegroundColor Green
            }
            "2" {
                # Replace: Backup existing, use ELF only
                $backupFile = Join-Path $ClaudeDir "CLAUDE.md.backup"
                Copy-Item -Path $claudeMdDst -Destination $backupFile -Force
                Copy-Item -Path $claudeMdSrc -Destination $claudeMdDst -Force
                Write-Host "  Replaced with ELF config (your config backed up to CLAUDE.md.backup)" -ForegroundColor Green
            }
            "3" {
                # Skip: Don't modify
                Write-Host "  Skipped CLAUDE.md modification" -ForegroundColor Yellow
                Write-Host "  Note: ELF may not function correctly without CLAUDE.md instructions" -ForegroundColor Yellow
            }
            default {
                Write-Host "  Invalid choice. Skipping CLAUDE.md modification." -ForegroundColor Yellow
                Write-Host "  Run installer again to configure CLAUDE.md" -ForegroundColor Yellow
            }
        }
    }
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
Write-Host "Next steps (copy-paste ready):"
Write-Host ""
Write-Host "  # 1. Review your configuration:"
Write-Host "  cat ~/.claude/CLAUDE.md"
Write-Host ""
if ($InstallDashboard) {
    Write-Host "  # 2. Start the dashboard:"
    Write-Host "  cd ~/.claude/emergent-learning/dashboard-app; ./run-dashboard.ps1"
    Write-Host ""
}
Write-Host "  # 3. Test the query system:"
Write-Host "  python3 ~/.claude/emergent-learning/query/query.py --context"
Write-Host ""
Write-Host "  # 4. Start using Claude Code (it will now query the building automatically!)"
Write-Host "  claude"
Write-Host ""
