#!/bin/bash
# Launch Simple Dashboard
echo "Starting simple dashboard..."

# Detect OS
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" ]]; then
    powershell -ExecutionPolicy Bypass -File "$(dirname "$0")/../../apps/dashboard/run-dashboard.ps1"
else
    "$(dirname "$0")/../../apps/dashboard/run-dashboard.sh"
fi
