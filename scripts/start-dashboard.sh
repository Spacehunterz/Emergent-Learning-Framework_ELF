#!/bin/bash
# Smart dashboard startup - checks if running, opens correct port

ELF_DIR="$HOME/.claude/emergent-learning"
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
