#!/bin/bash
#
# start-work.sh: One-command work session start
#
# Automatically initializes Ralph Loop PRD if needed, then starts execution
# Usage: bash start-work.sh
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
PRD_FILE="$REPO_ROOT/prd.json"
PROGRESS_FILE="$REPO_ROOT/progress.txt"

echo "═══════════════════════════════════════════════════════════"
echo "START-WORK: Autonomous Work Session"
echo "═══════════════════════════════════════════════════════════"
echo ""

if [ ! -f "$PRD_FILE" ]; then
    echo "📋 No PRD found. Initializing Ralph Loop..."
    echo ""

    bash "$SCRIPT_DIR/init-ralph.sh" --project "Project"

    echo ""
    echo "✓ Ralph Loop initialized"
    echo ""
else
    echo "📋 PRD loaded: $PRD_FILE"

    if [ ! -f "$PROGRESS_FILE" ]; then
        touch "$PROGRESS_FILE"
        echo "Created progress.txt"
    fi

    echo ""
fi

echo "🚀 Starting Ralph Loop..."
echo ""

bash "$SCRIPT_DIR/ralph.sh"
