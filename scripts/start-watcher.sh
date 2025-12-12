#!/bin/bash
#
# Start the Tiered Watcher System
#
# Usage:
#   ./start-watcher.sh              # Start normally
#   ./start-watcher.sh --daemon     # Start in background
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
WATCHER_DIR="$PROJECT_DIR/watcher"
LAUNCHER_SCRIPT="$WATCHER_DIR/launcher.py"

# Check if launcher exists
if [ ! -f "$LAUNCHER_SCRIPT" ]; then
    echo "Error: Launcher script not found at $LAUNCHER_SCRIPT"
    exit 1
fi

# Check for ANTHROPIC_API_KEY
if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo "Error: ANTHROPIC_API_KEY environment variable is not set"
    echo "Please set it with: export ANTHROPIC_API_KEY='your-key-here'"
    exit 1
fi

# Change to project directory
cd "$PROJECT_DIR"

# Parse arguments
DAEMON=false
if [ "$1" = "--daemon" ] || [ "$1" = "-d" ]; then
    DAEMON=true
fi

# Start launcher
if [ "$DAEMON" = true ]; then
    echo "Starting watcher in daemon mode..."
    nohup python3 "$LAUNCHER_SCRIPT" > /dev/null 2>&1 &
    PID=$!
    echo "Watcher started with PID: $PID"
    echo "Monitor logs at: $PROJECT_DIR/.coordination/launcher.log"
    echo "Stop with: kill $PID"
else
    echo "Starting watcher (Ctrl+C to stop)..."
    python3 "$LAUNCHER_SCRIPT"
fi
