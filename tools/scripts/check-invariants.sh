#!/bin/bash
# ELF Invariant Checker
# Validates code invariants defined in the ELF database before commits
#
# Usage: check-invariants.sh [--project <path>]

# Get script directory and derive paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_PATH="$(dirname "$SCRIPT_DIR")"

# Parse arguments (override if provided)
while [[ $# -gt 0 ]]; do
    case $1 in
        --project)
            PROJECT_PATH="$2"
            shift 2
            ;;
        *)
            shift
            ;;
    esac
done

# Run Python script for cross-platform path handling
python3 "${SCRIPT_DIR}/check-invariants.py" --project "$PROJECT_PATH"
exit $?
