#!/bin/bash
# TalkinHead Launcher for Linux
# Uses venv to avoid numpy compatibility issues with system packages

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"

cd "$SCRIPT_DIR"

# Create venv if it doesn't exist
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
    "$VENV_DIR/bin/pip" install --upgrade pip
    "$VENV_DIR/bin/pip" install "numpy<2" opencv-python-headless pygame PyQt5
fi

# Run with venv python
exec "$VENV_DIR/bin/python" main.py "$@"
