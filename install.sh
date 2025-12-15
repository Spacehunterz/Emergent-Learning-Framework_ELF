#!/bin/bash
# Emergent Learning Framework - Unix/Mac Installer
# Run with: chmod +x install.sh && ./install.sh

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${CYAN}============================================${NC}"
echo -e "${CYAN}  Emergent Learning Framework Installer${NC}"
echo -e "${CYAN}============================================${NC}"
echo ""
echo -e "${CYAN}Estimated installation time: ~2 minutes${NC}"
echo ""

# Get paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLAUDE_DIR="$HOME/.claude"
EMERGENT_LEARNING_DIR="$CLAUDE_DIR/emergent-learning"
HOOKS_DIR="$CLAUDE_DIR/hooks"
SETTINGS_FILE="$CLAUDE_DIR/settings.json"

# Default: install all
INSTALL_CORE=true
INSTALL_DASHBOARD=true
INSTALL_SWARM=true

# Parse arguments
show_help() {
    echo "Usage: ./install.sh [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --core-only      Install only core (query system, hooks, golden rules)"
    echo "  --no-dashboard   Skip dashboard installation (skips visual UI at localhost:3000)"
    echo "  --no-swarm       Skip swarm/conductor installation"
    echo "  --all            Install everything (default)"
    echo "  --help           Show this help"
    echo ""
    echo "Components:"
    echo "  Core:      Query system, learning hooks, golden rules, CLAUDE.md"
    echo "  Dashboard: React UI for monitoring (localhost:3000)"
    echo "  Swarm:     Multi-agent conductor, agent personas"
    echo ""
}

for arg in "$@"; do
    case $arg in
        --core-only)
            INSTALL_DASHBOARD=false
            INSTALL_SWARM=false
            ;;
        --no-dashboard)
            INSTALL_DASHBOARD=false
            ;;
        --no-swarm)
            INSTALL_SWARM=false
            ;;
        --all)
            INSTALL_CORE=true
            INSTALL_DASHBOARD=true
            INSTALL_SWARM=true
            ;;
        --help)
            show_help
            exit 0
            ;;
    esac
done

echo "Installation mode:"
echo -e "  Core:      ${GREEN}Yes${NC}"
echo -e "  Dashboard: $([ "$INSTALL_DASHBOARD" = true ] && echo -e "${GREEN}Yes${NC}" || echo -e "${YELLOW}No${NC}")"
echo -e "  Swarm:     $([ "$INSTALL_SWARM" = true ] && echo -e "${GREEN}Yes${NC}" || echo -e "${YELLOW}No${NC}")"
echo ""

# Check prerequisites
echo -e "${YELLOW}[Step 1/5]${NC} Checking prerequisites..."

# Check Python
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
    echo -e "  Python: ${GREEN}$(python3 --version)${NC}"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
    echo -e "  Python: ${GREEN}$(python --version)${NC}"
else
    echo -e "  ${RED}ERROR: Python not found. Please install Python 3.8+${NC}"
    echo -e "  ${YELLOW}Fix: Install Python from https://python.org${NC}"
    echo -e "  ${YELLOW}Then: Run this installer again${NC}"
    exit 1
fi

# Check Bun/Node (only if installing dashboard)
HAS_BUN=false
if [ "$INSTALL_DASHBOARD" = true ]; then
    if command -v bun &> /dev/null; then
        echo -e "  Bun: ${GREEN}$(bun --version)${NC}"
        HAS_BUN=true
    elif command -v node &> /dev/null; then
        echo -e "  Node: ${GREEN}$(node --version)${NC}"
    else
        echo -e "  ${RED}ERROR: Neither Bun nor Node.js found (needed for dashboard)${NC}"
        echo -e "  ${YELLOW}Fix option 1: Run with --no-dashboard to skip dashboard${NC}"
        echo -e "  ${YELLOW}Fix option 2: Install Bun (https://bun.sh) or Node.js (https://nodejs.org)${NC}"
        echo -e "  ${YELLOW}Then: Run this installer again${NC}"
        exit 1
    fi
fi

echo ""
echo -e "${GREEN}[OK] Prerequisites met${NC}"
echo ""
echo -e "${YELLOW}[Step 2/5]${NC} Creating directory structure..."

# Create directories
mkdir -p "$CLAUDE_DIR"
mkdir -p "$EMERGENT_LEARNING_DIR/memory/failures"
mkdir -p "$EMERGENT_LEARNING_DIR/memory/successes"
mkdir -p "$EMERGENT_LEARNING_DIR/query"
mkdir -p "$EMERGENT_LEARNING_DIR/ceo-inbox"
mkdir -p "$HOOKS_DIR/learning-loop"

if [ "$INSTALL_SWARM" = true ]; then
    mkdir -p "$EMERGENT_LEARNING_DIR/agents/researcher"
    mkdir -p "$EMERGENT_LEARNING_DIR/agents/architect"
    mkdir -p "$EMERGENT_LEARNING_DIR/agents/skeptic"
    mkdir -p "$EMERGENT_LEARNING_DIR/agents/creative"
    mkdir -p "$EMERGENT_LEARNING_DIR/conductor"
fi

echo -e "  ${GREEN}Created directory structure (7 directories for core)${NC}"

# === CORE INSTALLATION ===
echo ""
echo -e "${YELLOW}[Step 3/5]${NC} Installing core components..."

SRC_DIR="$SCRIPT_DIR"

# Copy core files
cp "$SRC_DIR/query/query.py" "$EMERGENT_LEARNING_DIR/query/query.py"
cp "$SRC_DIR/templates/golden-rules.md" "$EMERGENT_LEARNING_DIR/memory/golden-rules.md"
cp "$SRC_DIR/templates/init_db.sql" "$EMERGENT_LEARNING_DIR/memory/init_db.sql"
echo -e "  ${GREEN}Copied query system${NC}"

# Copy hooks
cp "$SCRIPT_DIR/hooks/learning-loop/"*.py "$HOOKS_DIR/learning-loop/"
echo -e "  ${GREEN}Copied learning hooks${NC}"

# Copy scripts
mkdir -p "$EMERGENT_LEARNING_DIR/scripts"
cp "$SRC_DIR/scripts/"*.sh "$EMERGENT_LEARNING_DIR/scripts/" 2>&1 || echo -e "  ${YELLOW}Warning: Some scripts not copied (may not exist)${NC}"
chmod +x "$EMERGENT_LEARNING_DIR/scripts/"*.sh 2>&1 || echo -e "  ${YELLOW}Warning: Could not set execute permissions on some scripts${NC}"
echo -e "  ${GREEN}Copied recording scripts${NC}"

# Initialize database
DB_PATH="$EMERGENT_LEARNING_DIR/memory/index.db"
SQL_FILE="$EMERGENT_LEARNING_DIR/memory/init_db.sql"

if [ ! -f "$DB_PATH" ]; then
    if command -v sqlite3 &> /dev/null; then
        sqlite3 "$DB_PATH" < "$SQL_FILE"
    else
        $PYTHON_CMD "$EMERGENT_LEARNING_DIR/query/query.py" --validate > /dev/null 2>&1 || true
    fi
    echo -e "  ${GREEN}Initialized database${NC}"
else
    echo -e "  ${YELLOW}Database already exists (kept existing)${NC}"
fi

# === SWARM INSTALLATION ===
if [ "$INSTALL_SWARM" = true ]; then
    echo ""
    echo -e "${YELLOW}[Installing]${NC} Swarm components..."

    # Copy conductor
    cp "$SRC_DIR/conductor/"*.py "$EMERGENT_LEARNING_DIR/conductor/" 2>&1 || echo -e "  ${YELLOW}Warning: Some conductor .py files not copied${NC}"
    cp "$SRC_DIR/conductor/"*.sql "$EMERGENT_LEARNING_DIR/conductor/" 2>&1 || echo -e "  ${YELLOW}Warning: Some conductor .sql files not copied${NC}"
    echo -e "  ${GREEN}Copied conductor module${NC}"

    # Copy agent personas
    for agent in researcher architect skeptic creative; do
        if [ -d "$SRC_DIR/agents/$agent" ]; then
            cp "$SRC_DIR/agents/$agent/"* "$EMERGENT_LEARNING_DIR/agents/$agent/" 2>&1 || echo -e "  ${YELLOW}Warning: Some $agent files not copied${NC}"
        fi
    done
    echo -e "  ${GREEN}Copied agent personas${NC}"

    # Copy swarm command
    mkdir -p "$CLAUDE_DIR/commands"
    cp "$SCRIPT_DIR/commands/swarm.md" "$CLAUDE_DIR/commands/" 2>&1 || echo -e "  ${YELLOW}Warning: swarm.md not copied${NC}"
    echo -e "  ${GREEN}Copied /swarm command${NC}"

    # Copy agent coordination plugin
    mkdir -p "$CLAUDE_DIR/plugins/agent-coordination/utils"
    mkdir -p "$CLAUDE_DIR/plugins/agent-coordination/hooks"
    cp "$SCRIPT_DIR/plugins/agent-coordination/utils/"*.py "$CLAUDE_DIR/plugins/agent-coordination/utils/" 2>&1 || echo -e "  ${YELLOW}Warning: Some plugin utils not copied${NC}"
    cp "$SCRIPT_DIR/plugins/agent-coordination/hooks/"*.py "$CLAUDE_DIR/plugins/agent-coordination/hooks/" 2>&1 || echo -e "  ${YELLOW}Warning: Some plugin hooks .py not copied${NC}"
    cp "$SCRIPT_DIR/plugins/agent-coordination/hooks/"*.json "$CLAUDE_DIR/plugins/agent-coordination/hooks/" 2>&1 || echo -e "  ${YELLOW}Warning: Some plugin hooks .json not copied${NC}"
    echo -e "  ${GREEN}Copied agent coordination plugin${NC}"
fi

# === DASHBOARD INSTALLATION ===
if [ "$INSTALL_DASHBOARD" = true ]; then
    echo ""
    echo -e "${YELLOW}[Installing]${NC} Dashboard..."

    DASHBOARD_SRC="$SRC_DIR/dashboard-app"
    DASHBOARD_DST="$EMERGENT_LEARNING_DIR/dashboard-app"

    if [ -d "$DASHBOARD_SRC" ]; then
        rm -rf "$DASHBOARD_DST"
        cp -r "$DASHBOARD_SRC" "$DASHBOARD_DST"
        echo -e "  ${GREEN}Copied dashboard${NC}"

        # Install dependencies
        FRONTEND_DIR="$DASHBOARD_DST/frontend"
        if [ -d "$FRONTEND_DIR" ]; then
            cd "$FRONTEND_DIR"
            if [ "$HAS_BUN" = true ]; then
                bun install > /dev/null 2>&1
            else
                npm install > /dev/null 2>&1
            fi
            echo -e "  ${GREEN}Installed frontend dependencies${NC}"
        fi

        BACKEND_DIR="$DASHBOARD_DST/backend"
        if [ -d "$BACKEND_DIR" ]; then
            pip install -q fastapi uvicorn aiofiles websockets 2>&1 || pip3 install -q fastapi uvicorn aiofiles websockets 2>&1
            echo -e "  ${GREEN}Installed backend dependencies${NC}"
        fi

        # Make dashboard scripts executable
        chmod +x "$DASHBOARD_DST/run-dashboard.sh" 2>/dev/null || true
        chmod +x "$DASHBOARD_DST/"*.sh 2>/dev/null || true
        echo -e "  ${GREEN}Made dashboard scripts executable${NC}"

        cd "$SCRIPT_DIR"
    fi
fi

# === CHECK CLAUDE CODE ===
echo ""
echo -e "${YELLOW}[Step 5/5]${NC} Checking optional components..."
if command -v claude &> /dev/null; then
    echo -e "  Claude Code: ${GREEN}$(claude --version 2>/dev/null || echo 'installed')${NC}"
else
    echo -e "  ${YELLOW}WARNING: Claude Code not found (optional for now)${NC}"
    echo -e "  ${YELLOW}Note: ELF requires Claude Code to work. Install from: https://claude.ai/download${NC}"
    echo -e "  ${YELLOW}Installation will continue, but ELF won't be functional until you install Claude Code.${NC}"
fi

# === CONFIGURE SETTINGS.JSON ===
echo ""
echo -e "${YELLOW}[Step 4/5]${NC} Configuring Claude Code settings..."
echo ""
echo -e "  ${CYAN}About to modify settings.json:${NC}"
echo -e "  - Adding PreToolUse hook (runs before each task)"
echo -e "  - Adding PostToolUse hook (runs after each task)"
echo -e "  - Preserving your existing hooks (if any)"
echo -e "  - Creating backup at settings.json.backup${NC}"
echo ""

PRE_HOOK="$HOOKS_DIR/learning-loop/pre_tool_learning.py"
POST_HOOK="$HOOKS_DIR/learning-loop/post_tool_learning.py"

# Backup existing settings if present
if [ -f "$SETTINGS_FILE" ]; then
    cp "$SETTINGS_FILE" "$CLAUDE_DIR/settings.json.backup"
    echo -e "  ${GREEN}Backed up existing settings to settings.json.backup${NC}"
fi

# Pass variables as environment variables to avoid shell expansion issues
SETTINGS_FILE="$SETTINGS_FILE" PRE_HOOK="$PRE_HOOK" POST_HOOK="$POST_HOOK" $PYTHON_CMD << 'PYEOF'
import json
import os

settings_file = os.environ['SETTINGS_FILE']
pre_hook = os.environ['PRE_HOOK']
post_hook = os.environ['POST_HOOK']

try:
    with open(settings_file, 'r', encoding='utf-8') as f:
        settings = json.load(f)
except:
    settings = {}

if 'hooks' not in settings:
    settings['hooks'] = {}

# Ensure hook arrays exist
if 'PreToolUse' not in settings['hooks']:
    settings['hooks']['PreToolUse'] = []
if 'PostToolUse' not in settings['hooks']:
    settings['hooks']['PostToolUse'] = []

# Remove any existing ELF hooks (to avoid duplicates on reinstall)
# Only remove hooks where matcher="Task" AND command contains "learning-loop"
settings['hooks']['PreToolUse'] = [
    h for h in settings['hooks']['PreToolUse']
    if not (h.get('matcher') == 'Task' and any('learning-loop' in hook.get('command', '') for hook in h.get('hooks', [])))
]
settings['hooks']['PostToolUse'] = [
    h for h in settings['hooks']['PostToolUse']
    if not (h.get('matcher') == 'Task' and any('learning-loop' in hook.get('command', '') for hook in h.get('hooks', [])))
]

# Add ELF hooks - use python on Windows, python3 on Unix
# Check for Windows by looking at path style (contains backslash or drive letter)
is_windows = os.name == 'nt' or (len(pre_hook) > 1 and pre_hook[1] == ':')
if is_windows:
    python_cmd = "python"
else:
    # On Unix, prefer python3 if available
    python_cmd = "python3" if os.path.exists("/usr/bin/python3") or os.system("which python3 > /dev/null 2>&1") == 0 else "python"
settings['hooks']['PreToolUse'].append({
    "matcher": "Task",
    "hooks": [{"type": "command", "command": f"{python_cmd} \"{pre_hook}\""}]
})

settings['hooks']['PostToolUse'].append({
    "matcher": "Task",
    "hooks": [{"type": "command", "command": f"{python_cmd} \"{post_hook}\""}]
})

with open(settings_file, 'w', encoding='utf-8') as f:
    json.dump(settings, f, indent=2, ensure_ascii=False)
PYEOF

echo -e "  ${GREEN}Configured hooks (preserved existing hooks)${NC}"

# Validate settings.json (use env var to handle MSYS/Windows path conversion)
if SETTINGS_FILE="$SETTINGS_FILE" $PYTHON_CMD -c "import json, os; json.load(open(os.environ['SETTINGS_FILE']))" 2>/dev/null; then
    echo -e "  ${GREEN}[OK] settings.json validated${NC}"
else
    echo -e "  ${RED}[ERROR] settings.json validation failed!${NC}"
    echo -e "  ${YELLOW}Fix: Restore from backup: cp $CLAUDE_DIR/settings.json.backup $SETTINGS_FILE${NC}"
    echo -e "  ${YELLOW}Then: Run installer again${NC}"
    exit 1
fi

# === CLAUDE.MD ===
CLAUDE_MD_DST="$CLAUDE_DIR/CLAUDE.md"
CLAUDE_MD_SRC="$SCRIPT_DIR/templates/CLAUDE.md.template"

if [ ! -f "$CLAUDE_MD_DST" ]; then
    # No existing CLAUDE.md - create fresh
    if [ -f "$CLAUDE_MD_SRC" ]; then
        cp "$CLAUDE_MD_SRC" "$CLAUDE_MD_DST"
        echo -e "  ${GREEN}Created CLAUDE.md${NC}"
    fi
elif grep -q "Emergent Learning Framework" "$CLAUDE_MD_DST" 2>/dev/null; then
    # Already has ELF instructions
    echo -e "  ${GREEN}CLAUDE.md already has ELF instructions${NC}"
else
    # Has CLAUDE.md but no ELF - prompt user
    echo ""
    echo -e "  ${YELLOW}Existing CLAUDE.md found without ELF instructions.${NC}"
    echo ""
    echo "  How should we proceed?"
    echo "    1) Merge - Add ELF instructions to your existing config (recommended)"
    echo "    2) Replace - Use ELF config only (backs up existing to CLAUDE.md.backup)"
    echo "    3) Skip - Don't modify CLAUDE.md (ELF features may not work)"
    echo ""
    read -p "  Choose [1/2/3]: " choice
    
    case $choice in
        1|"")
            # Merge: append ELF instructions to existing
            echo "" >> "$CLAUDE_MD_DST"
            echo "---" >> "$CLAUDE_MD_DST"
            echo "" >> "$CLAUDE_MD_DST"
            cat "$CLAUDE_MD_SRC" >> "$CLAUDE_MD_DST"
            echo -e "  ${GREEN}Merged ELF instructions into existing CLAUDE.md${NC}"
            ;;
        2)
            # Replace: backup and overwrite
            cp "$CLAUDE_MD_DST" "$CLAUDE_MD_DST.backup"
            cp "$CLAUDE_MD_SRC" "$CLAUDE_MD_DST"
            echo -e "  ${GREEN}Replaced CLAUDE.md (backup saved to CLAUDE.md.backup)${NC}"
            ;;
        3)
            echo -e "  ${YELLOW}Skipped CLAUDE.md modification${NC}"
            echo -e "  ${YELLOW}Warning: ELF features may not work without proper CLAUDE.md setup${NC}"
            ;;
        *)
            echo -e "  ${YELLOW}Invalid choice, skipping CLAUDE.md modification${NC}"
            ;;
    esac
fi

# === DONE ===
echo ""
echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}  Installation Complete!${NC}"
echo -e "${GREEN}============================================${NC}"
echo ""
echo "Installed:"
echo -e "  ${GREEN}✓${NC} Core (query system, hooks, golden rules)"
[ "$INSTALL_DASHBOARD" = true ] && echo -e "  ${GREEN}✓${NC} Dashboard (localhost:3000)"
[ "$INSTALL_SWARM" = true ] && echo -e "  ${GREEN}✓${NC} Swarm (conductor, agent personas)"
echo ""
echo "Next steps (copy-paste ready):"
echo ""
echo "  # 1. Review your configuration:"
echo "  cat ~/.claude/CLAUDE.md"
echo ""
if [ "$INSTALL_DASHBOARD" = true ]; then
    echo "  # 2. Start the dashboard:"
    echo "  cd ~/.claude/emergent-learning/dashboard-app && ./run-dashboard.sh"
    echo ""
fi
echo "  # 3. Test the query system:"
echo "  $PYTHON_CMD ~/.claude/emergent-learning/query/query.py --context"
echo ""
echo "  # 4. Start using Claude Code (it will now query the building automatically!)"
echo "  claude"
echo ""
