#!/bin/bash
#
# Emergent Learning Framework - Setup Script
# Supports: --mode fresh|merge|replace|skip
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLAUDE_DIR="$HOME/.claude"
MODE="${1#--mode=}"
MODE="${MODE:-interactive}"

# If called with --mode flag, extract it
if [ "$1" = "--mode" ]; then
    MODE="$2"
fi

# Create directories
mkdir -p "$CLAUDE_DIR/commands"
mkdir -p "$CLAUDE_DIR/hooks/SessionStart"

install_commands() {
    for file in "$SCRIPT_DIR/commands/"*; do
        [ -f "$file" ] || continue
        filename=$(basename "$file")
        if [ ! -f "$CLAUDE_DIR/commands/$filename" ]; then
            cp "$file" "$CLAUDE_DIR/commands/$filename"
        fi
    done
}

install_hooks() {
    if [ -f "$SCRIPT_DIR/hooks/golden-rule-enforcer.py" ]; then
        if [ ! -f "$CLAUDE_DIR/hooks/golden-rule-enforcer.py" ]; then
            cp "$SCRIPT_DIR/hooks/golden-rule-enforcer.py" "$CLAUDE_DIR/hooks/"
        fi
    fi
    for file in "$SCRIPT_DIR/hooks/SessionStart/"*; do
        [ -f "$file" ] || continue
        filename=$(basename "$file")
        if [ ! -f "$CLAUDE_DIR/hooks/SessionStart/$filename" ]; then
            cp "$file" "$CLAUDE_DIR/hooks/SessionStart/$filename"
        fi
    done
}

case "$MODE" in
    fresh)
        # New user - install everything
        cp "$SCRIPT_DIR/CLAUDE.md.template" "$CLAUDE_DIR/CLAUDE.md"
        install_commands
        install_hooks
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
        install_hooks
        ;;
    
    replace)
        # Replace: backup theirs, use ELF only
        if [ -f "$CLAUDE_DIR/CLAUDE.md" ]; then
            cp "$CLAUDE_DIR/CLAUDE.md" "$CLAUDE_DIR/CLAUDE.md.backup"
        fi
        cp "$SCRIPT_DIR/CLAUDE.md.template" "$CLAUDE_DIR/CLAUDE.md"
        install_commands
        install_hooks
        echo "[ELF] Replaced config (backup: CLAUDE.md.backup)"
        ;;
    
    skip)
        # Skip CLAUDE.md but install commands/hooks
        echo "[ELF] Skipping CLAUDE.md modification"
        echo "[ELF] Warning: ELF may not function correctly without CLAUDE.md instructions"
        install_commands
        install_hooks
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
        install_hooks
        echo ""
        echo "Setup complete!"
        ;;
esac
