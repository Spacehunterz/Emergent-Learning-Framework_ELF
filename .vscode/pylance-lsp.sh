#!/bin/bash
# Start Pyright LSP server for Claude Code
# This script starts Pyright in language server protocol (LSP) mode

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

# Activate venv if it exists
if [ -d ".venv" ]; then
    source .venv/Scripts/activate 2>/dev/null || . .venv/Scripts/activate
fi

# Start Pyright in LSP mode on stdio
# This allows Claude Code to communicate with the server via stdin/stdout
exec python -m pyright --outputjson --verbose
