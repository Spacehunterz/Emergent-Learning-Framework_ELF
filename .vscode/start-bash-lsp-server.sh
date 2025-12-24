#!/bin/bash
# Start Bash Language Server for Claude Code
# This script launches bash-language-server on stdio

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

echo "Starting Bash Language Server..."
echo "Configuration: ${PROJECT_ROOT}/.shellcheckrc (if available)"
echo ""

# Start bash-language-server in stdio mode
# This allows Claude Code to communicate with the server via stdin/stdout
exec bash-language-server start
