#!/bin/bash
#
# Emergent Learning Framework - Setup Script
# Supports: --mode fresh|merge|replace|skip
#
# Cross-platform: Works on Windows (Git Bash/MSYS2), Linux, and macOS
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLAUDE_DIR="$HOME/.claude"
ELF_DIR="$CLAUDE_DIR/emergent-learning"
MODE="${1#--mode=}"
MODE="${MODE:-interactive}"

# If called with --mode flag, extract it
if [ "$1" = "--mode" ]; then
    MODE="$2"
fi

# Create directories
mkdir -p "$CLAUDE_DIR/commands"

# Detect Python command (python3 or python)
detect_python() {
    if command -v python3 &> /dev/null; then
        echo "python3"
    elif command -v python &> /dev/null; then
        echo "python"
    else
        echo ""
    fi
}

PYTHON_CMD=$(detect_python)

install_venv() {
    local venv_dir="$ELF_DIR/.venv"
    local requirements="$ELF_DIR/requirements.txt"

    if [ -z "$PYTHON_CMD" ]; then
        echo "[ELF] Warning: Python not found. Skipping venv setup."
        echo "[ELF] Install Python 3.8+ and re-run setup for full functionality."
        return 1
    fi

    # Create venv if it doesn't exist
    if [ ! -d "$venv_dir" ]; then
        echo "[ELF] Creating Python virtual environment..."
        if ! $PYTHON_CMD -m venv "$venv_dir" 2>/dev/null; then
            echo "[ELF] Warning: Failed to create venv. Using system Python."
            return 1
        fi
    fi

    # Determine venv python path based on OS
    if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" || "$OSTYPE" == "win32" ]]; then
        VENV_PYTHON="$venv_dir/Scripts/python.exe"
    else
        VENV_PYTHON="$venv_dir/bin/python"
    fi

    # Verify venv python exists
    if [ ! -f "$VENV_PYTHON" ]; then
        echo "[ELF] Warning: Venv python not found at $VENV_PYTHON"
        VENV_PYTHON=""
        return 1
    fi

    # Install requirements if they exist
    if [ -f "$requirements" ]; then
        echo "[ELF] Installing Python dependencies..."
        "$VENV_PYTHON" -m pip install --quiet --upgrade pip 2>/dev/null || true
        if ! "$VENV_PYTHON" -m pip install --quiet -r "$requirements" 2>/dev/null; then
            echo "[ELF] Warning: Some dependencies failed to install. Core features should still work."
        fi
    fi

    echo "[ELF] Virtual environment ready at: $venv_dir"
    return 0
}

# Global variable for venv python path (set by install_venv)
VENV_PYTHON=""

install_commands() {
    for file in "$SCRIPT_DIR/commands/"*; do
        [ -f "$file" ] || continue
        filename=$(basename "$file")
        if [ ! -f "$CLAUDE_DIR/commands/$filename" ]; then
            cp "$file" "$CLAUDE_DIR/commands/$filename"
        fi
    done
}

install_settings() {
    # Generate settings.json with hooks pointing to emergent-learning directory
    # Uses Python for cross-platform path handling
    # Pass VENV_PYTHON as environment variable for the script to use
    VENV_PYTHON_PATH="$VENV_PYTHON" $PYTHON_CMD << 'PYTHON_SCRIPT'
import json
import os
import sys
from pathlib import Path

claude_dir = Path.home() / ".claude"
elf_dir = claude_dir / "emergent-learning"
elf_hooks = elf_dir / "hooks" / "learning-loop"
settings_file = claude_dir / "settings.json"

# Get venv python path from environment, or detect it
venv_python = os.environ.get("VENV_PYTHON_PATH", "")

# If no venv python provided, try to detect it
if not venv_python:
    venv_dir = elf_dir / ".venv"
    if sys.platform == "win32":
        candidate = venv_dir / "Scripts" / "python.exe"
    else:
        candidate = venv_dir / "bin" / "python"
    if candidate.exists():
        venv_python = str(candidate)

# Determine the python command to use in hooks
if venv_python and Path(venv_python).exists():
    python_cmd = f'"{venv_python}"'
else:
    # Fallback to system python3
    python_cmd = "python3"

# Detect platform and format paths appropriately
if sys.platform == "win32":
    # Windows: use escaped backslashes in JSON
    pre_hook = str(elf_hooks / "pre_tool_learning.py").replace("\\", "\\\\")
    post_hook = str(elf_hooks / "post_tool_learning.py").replace("\\", "\\\\")
    if venv_python:
        python_cmd = f'"{venv_python.replace(chr(92), chr(92)+chr(92))}"'
else:
    # Unix: forward slashes
    pre_hook = str(elf_hooks / "pre_tool_learning.py")
    post_hook = str(elf_hooks / "post_tool_learning.py")

settings = {
    "hooks": {
        "PreToolUse": [
            {
                "hooks": [
                    {
                        "command": f'{python_cmd} "{pre_hook}"',
                        "type": "command"
                    }
                ],
                "matcher": "Task"
            }
        ],
        "PostToolUse": [
            {
                "hooks": [
                    {
                        "command": f'{python_cmd} "{post_hook}"',
                        "type": "command"
                    }
                ],
                "matcher": "Task"
            }
        ]
    }
}

# Merge with existing settings if present
if settings_file.exists():
    try:
        with open(settings_file) as f:
            existing = json.load(f)
        # Only update hooks section, preserve other settings
        existing["hooks"] = settings["hooks"]
        settings = existing
    except (json.JSONDecodeError, KeyError):
        pass  # Use fresh settings if existing is corrupt

with open(settings_file, "w") as f:
    json.dump(settings, f, indent=4)

print(f"[ELF] settings.json configured with hooks at: {elf_hooks}")
PYTHON_SCRIPT
}

install_git_hooks() {
    # Install git pre-commit hook for invariant enforcement
    local git_hooks_dir="$ELF_DIR/.git/hooks"

    if [ -d "$git_hooks_dir" ]; then
        if [ -f "$SCRIPT_DIR/git-hooks/pre-commit" ]; then
            cp "$SCRIPT_DIR/git-hooks/pre-commit" "$git_hooks_dir/pre-commit"
            chmod +x "$git_hooks_dir/pre-commit"
            echo "[ELF] Git pre-commit hook installed (invariant enforcement)"
        fi
    fi
}

case "$MODE" in
    fresh)
        # New user - install everything
        cp "$SCRIPT_DIR/CLAUDE.md.template" "$CLAUDE_DIR/CLAUDE.md"
        install_commands
        install_venv
        install_settings
        install_git_hooks
        echo "[ELF] Fresh install complete"
        ;;

    merge)
        # Merge: their config + ELF
        if [ -f "$CLAUDE_DIR/CLAUDE.md" ]; then
            cp "$CLAUDE_DIR/CLAUDE.md" "$CLAUDE_DIR/CLAUDE.md.backup"
            {
                cat "$CLAUDE_DIR/CLAUDE.md"
                echo ""
                echo ""
                echo "# =============================================="
                echo "# EMERGENT LEARNING FRAMEWORK - AUTO-APPENDED"
                echo "# =============================================="
                echo ""
                cat "$SCRIPT_DIR/CLAUDE.md.template"
            } > "$CLAUDE_DIR/CLAUDE.md.new"
            mv "$CLAUDE_DIR/CLAUDE.md.new" "$CLAUDE_DIR/CLAUDE.md"
            echo "[ELF] Merged with existing config (backup: CLAUDE.md.backup)"
        fi
        install_commands
        install_venv
        install_settings
        install_git_hooks
        ;;

    replace)
        # Replace: backup theirs, use ELF only
        if [ -f "$CLAUDE_DIR/CLAUDE.md" ]; then
            cp "$CLAUDE_DIR/CLAUDE.md" "$CLAUDE_DIR/CLAUDE.md.backup"
        fi
        cp "$SCRIPT_DIR/CLAUDE.md.template" "$CLAUDE_DIR/CLAUDE.md"
        install_commands
        install_venv
        install_settings
        install_git_hooks
        echo "[ELF] Replaced config (backup: CLAUDE.md.backup)"
        ;;

    skip)
        # Skip CLAUDE.md but install commands/hooks
        echo "[ELF] Skipping CLAUDE.md modification"
        echo "[ELF] Warning: ELF may not function correctly without CLAUDE.md instructions"
        install_commands
        install_venv
        install_settings
        install_git_hooks
        ;;

    interactive|*)
        # Interactive mode - show menu
        echo "========================================"
        echo "Emergent Learning Framework - Setup"
        echo "========================================"
        echo ""

        if [ -f "$CLAUDE_DIR/CLAUDE.md" ]; then
            if grep -q "Emergent Learning Framework" "$CLAUDE_DIR/CLAUDE.md" 2>/dev/null; then
                echo "ELF already configured in CLAUDE.md"
            else
                echo "Existing CLAUDE.md found."
                echo ""
                echo "Options:"
                echo "  1) Merge - Keep yours, add ELF below"
                echo "  2) Replace - Use ELF only (yours backed up)"
                echo "  3) Skip - Don't modify CLAUDE.md"
                echo ""
                read -p "Choice [1/2/3]: " choice
                case "$choice" in
                    1) bash "$0" --mode merge ;;
                    2) bash "$0" --mode replace ;;
                    3) bash "$0" --mode skip ;;
                    *) echo "Invalid choice"; exit 1 ;;
                esac
                exit 0
            fi
        else
            bash "$0" --mode fresh
            exit 0
        fi

        install_commands
        install_venv
        install_settings
        install_git_hooks
        echo ""
        echo "Setup complete!"
        ;;
esac
