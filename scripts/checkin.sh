#!/bin/bash
# ELF Checkin - Wrapper for Python checkin orchestrator
#
# This script delegates to the Python-based checkin orchestrator which handles:
# - 8-step workflow with proper state tracking
# - Banner display
# - Context loading
# - Dashboard prompting (first checkin only)
# - Model selection with persistence
# - CEO decision checking

set -e

# Find the Python script
ELF_HOME="${HOME}/.claude/emergent-learning"
CHECKIN_PY="${ELF_HOME}/src/query/checkin.py"

# Fallback location if standard location doesn't exist
if [ ! -f "$CHECKIN_PY" ]; then
    # Try project-relative location
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
    CHECKIN_PY="${PROJECT_ROOT}/src/query/checkin.py"
fi

# Ensure we can find Python
if ! command -v python3 &> /dev/null && ! command -v python &> /dev/null; then
    echo "❌ Python not found. Please install Python 3."
    exit 1
fi

# Run the orchestrator
if [ -f "$CHECKIN_PY" ]; then
    python3 "$CHECKIN_PY"
else
    echo "❌ Checkin script not found at $CHECKIN_PY"
    exit 1
fi
