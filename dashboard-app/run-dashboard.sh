#!/bin/bash
# Emergent Learning Dashboard Launcher
# Run from dashboard-app/ directory or double-click

# Find the ELF directory (handles both running from dashboard-app/ or elsewhere)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ELF_DIR="$(dirname "$SCRIPT_DIR")"

# Detect Python command
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
else
    echo "Error: Python not found. Install from https://python.org"
    exit 1
fi

# Issue #11: Detect Git Bash + npm platform mismatch on Windows
if [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "mingw"* ]] || [[ -n "$MSYSTEM" ]]; then
    FRONTEND_DIR="$SCRIPT_DIR/frontend"
    if [ -d "$FRONTEND_DIR/node_modules/@rollup" ]; then
        if ls "$FRONTEND_DIR/node_modules/@rollup/"*linux* >/dev/null 2>&1 && \
           ! ls "$FRONTEND_DIR/node_modules/@rollup/"*win32* >/dev/null 2>&1; then
            echo ""
            echo "WARNING: Git Bash npm platform mismatch detected!"
            echo "=========================================="
            echo "npm installed Linux binaries instead of Windows binaries."
            echo ""
            echo "To fix, run these commands in PowerShell or CMD (not Git Bash):"
            echo ""
            echo "  cd $FRONTEND_DIR"
            echo "  rm -rf node_modules package-lock.json"
            echo "  npm install"
            echo ""
            echo "Or use Bun instead (works correctly everywhere):"
            echo "  bun install"
            echo ""
            echo "=========================================="
            echo ""
            read -p "Try to continue anyway? (may fail) [y/N]: " choice
            if [[ ! "$choice" =~ ^[Yy]$ ]]; then
                exit 1
            fi
        fi
    fi
fi

BACKEND_PORT=8888
FRONTEND_PORT=3001
BACKEND_PATH="$SCRIPT_DIR/backend"
FRONTEND_PATH="$SCRIPT_DIR/frontend"

echo "========================================================"
echo "        EMERGENT LEARNING DASHBOARD                     "
echo "        Agent Intelligence System                       "
echo "========================================================"
echo ""

# Track if we started any servers
STARTED_SERVERS=false

# Check if backend already running
if curl -s "http://localhost:$BACKEND_PORT/api/stats" >/dev/null 2>&1; then
    echo "[OK] Backend already running on port $BACKEND_PORT"
else
    echo "[Starting] Backend API server..."
    cd "$BACKEND_PATH" && $PYTHON_CMD -m uvicorn main:app --host 0.0.0.0 --port $BACKEND_PORT &
    STARTED_SERVERS=true
    sleep 3
fi

# Detect package manager
if command -v bun &> /dev/null; then
    PKG_MGR="bun"
elif command -v npm &> /dev/null; then
    PKG_MGR="npm"
else
    echo "Error: Neither bun nor npm found. Install from https://bun.sh or https://nodejs.org"
    exit 1
fi

# Check if frontend already running
if curl -s "http://localhost:$FRONTEND_PORT" >/dev/null 2>&1; then
    echo "[OK] Frontend already running on port $FRONTEND_PORT"
else
    echo "[Starting] Frontend dev server (using $PKG_MGR)..."
    cd "$FRONTEND_PATH" && $PKG_MGR run dev &
    STARTED_SERVERS=true
    sleep 4
fi

# Open browser
echo "[Opening] Browser..."
if command -v xdg-open >/dev/null 2>&1; then
    xdg-open "http://localhost:$FRONTEND_PORT"
elif command -v open >/dev/null 2>&1; then
    open "http://localhost:$FRONTEND_PORT"
else
    start "http://localhost:$FRONTEND_PORT" 2>/dev/null || echo "Open http://localhost:$FRONTEND_PORT in your browser"
fi

echo ""
echo "========================================================"
echo "  Dashboard is running!"
echo ""
echo "  Frontend:  http://localhost:$FRONTEND_PORT"
echo "  Backend:   http://localhost:$BACKEND_PORT"
echo "  API Docs:  http://localhost:$BACKEND_PORT/docs"
echo ""
echo "  Press Ctrl+C to stop servers"
echo "========================================================"
echo ""

# If both servers were already running, exit cleanly
if [ "$STARTED_SERVERS" = false ]; then
    exit 0
fi

# Keep script running to allow Ctrl+C to kill background jobs
trap "echo 'Shutting down...'; kill 0" EXIT
wait
