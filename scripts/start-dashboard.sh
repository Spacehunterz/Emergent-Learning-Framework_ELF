#!/bin/bash
# Smart dashboard startup - checks if running, opens correct port

ELF_DIR="$HOME/.claude/emergent-learning"

# Issue #11: Detect Git Bash + npm platform mismatch on Windows
# Git Bash makes npm think it's Linux, installing wrong native binaries
if [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "mingw"* ]] || [[ -n "$MSYSTEM" ]]; then
    FRONTEND_DIR="$ELF_DIR/dashboard-app/frontend"
    if [ -d "$FRONTEND_DIR/node_modules/@rollup" ]; then
        # Check if we have Linux binaries instead of Windows
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
FRONTEND_OUTPUT="/tmp/claude-dashboard-frontend.log"

# Check if backend already running
if curl -s "http://127.0.0.1:$BACKEND_PORT/health" >/dev/null 2>&1; then
    echo "Backend already running on port $BACKEND_PORT"
    BACKEND_RUNNING=true
else
    echo "Starting backend..."
    cd "$ELF_DIR/dashboard-app/backend" && python3 -m uvicorn main:app --host 127.0.0.1 --port $BACKEND_PORT &
    BACKEND_RUNNING=false
fi

# Check if frontend already running by checking common ports
for port in 3001 3002 3003 3004 3005; do
    if curl -s "http://localhost:$port" >/dev/null 2>&1; then
        echo "Frontend already running on port $port"
        FRONTEND_PORT=$port
        FRONTEND_RUNNING=true
        break
    fi
done

if [ -z "$FRONTEND_RUNNING" ]; then
    echo "Starting frontend..."
    cd "$ELF_DIR/dashboard-app/frontend"

    # Start frontend and capture output to find actual port
    bun run dev > "$FRONTEND_OUTPUT" 2>&1 &
    FRONTEND_PID=$!

    # Wait for Vite to report the port (max 10 seconds)
    for i in {1..20}; do
        if [ -f "$FRONTEND_OUTPUT" ]; then
            FRONTEND_PORT=$(grep -o 'localhost:[0-9]*' "$FRONTEND_OUTPUT" | head -1 | cut -d: -f2)
            if [ -n "$FRONTEND_PORT" ]; then
                echo "Frontend started on port $FRONTEND_PORT"
                break
            fi
        fi
        sleep 0.5
    done

    if [ -z "$FRONTEND_PORT" ]; then
        echo "Warning: Could not detect frontend port, defaulting to 3001"
        FRONTEND_PORT=3001
    fi
fi

# Open browser with correct port (only once!)
echo "Opening browser at http://localhost:$FRONTEND_PORT"
if command -v xdg-open >/dev/null 2>&1; then
    xdg-open "http://localhost:$FRONTEND_PORT"
elif command -v open >/dev/null 2>&1; then
    open "http://localhost:$FRONTEND_PORT"
else
    start "http://localhost:$FRONTEND_PORT"
fi

echo "Dashboard ready!"
echo "  Backend:  http://127.0.0.1:$BACKEND_PORT"
echo "  Frontend: http://localhost:$FRONTEND_PORT"
