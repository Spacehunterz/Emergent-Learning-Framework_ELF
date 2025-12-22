#!/usr/bin/env python3
"""
Emergent Learning Dashboard - Backend API

FastAPI backend providing:
- REST API for dashboard data
- WebSocket for real-time updates
- Action endpoints (promote, retry, open in editor)
- Natural language query interface
- Workflow management

Run: uvicorn main:app --reload --port 8888
"""

import asyncio
import logging
import sys 
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from starlette.middleware.base import BaseHTTPMiddleware

# Import utilities
from utils import get_db, dict_from_row, ConnectionManager, auto_capture, init_project_context

# Import routers
from routers import (
    analytics_router,
    heuristics_router,
    runs_router,
    knowledge_router,
    queries_router,
    sessions_router,
    admin_router,
    fraud_router,
    workflows_router,
    context_router,
    auth_router,
    game_router,
    setup_router
)

# Import router setup functions
from routers.heuristics import set_manager as set_heuristics_manager
from routers.knowledge import set_manager as set_knowledge_manager
from routers.sessions import set_session_index
from routers.admin import set_paths as set_admin_paths
from routers.fraud import set_paths as set_fraud_paths
from routers.workflows import set_paths as set_workflows_paths

# Paths
EMERGENT_LEARNING_PATH = Path.home() / ".claude" / "emergent-learning"
FRONTEND_PATH = Path(__file__).parent.parent / "frontend" / "dist"

# Import database initialization (must come after EMERGENT_LEARNING_PATH is defined)
# Import from the query system, not the local models.py (which is Pydantic models)
import sys
sys.path.insert(0, str(EMERGENT_LEARNING_PATH))
from query.models import initialize_database, create_tables

# Import session indexing
from session_index import SessionIndex

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Emergent Learning Dashboard",
    description="Interactive dashboard for AI agent orchestration and learning",
    version="1.0.0"
)

# ==============================================================================
# Background Task: Auto-Summarizer
# ==============================================================================

async def run_auto_summarizer():
    """Background task to automatically summarize completed sessions."""
    logger.info("Auto-summarizer background task started")
    
    # Path to summarizer script
    summarizer_script = EMERGENT_LEARNING_PATH / "scripts" / "summarize-session.py"
    
    while True:
        try:
            # Wait 5 minutes before first run and between runs
            # This allows the system to startup and sessions to complete
            await asyncio.sleep(300) 
            
            logger.info("Running scheduled batch summarization...")
            
            # Check if script exists
            if not summarizer_script.exists():
                logger.warning(f"Summarizer script not found at {summarizer_script}")
                continue

            # Run batch summarization for sessions older than 30 minutes
            # Limit 5 per batch to avoid overloading
            cmd = [
                sys.executable, str(summarizer_script),
                "--batch",
                "--older-than", "30m",
                "--limit", "5"
            ]
            
            # Run using asyncio subprocess
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                logger.error(f"Auto-summarizer failed: {stderr.decode()}")
            else:
                output = stdout.decode().strip()
                if "Summarized" in output:
                    logger.info(f"Auto-summarizer: {output}")
                
        except Exception as e:
            logger.error(f"Auto-summarizer error: {e}")
            
        # Run every 10 minutes (600s) + execution time
        await asyncio.sleep(600)

# CORS - restricted to local development origins only
# SECURITY: Since backend is localhost-only, this primarily prevents
# malicious websites from making requests if user visits them
ALLOWED_ORIGINS = [
    "http://localhost:3001",   # Vite dev server
    "http://localhost:8888",   # Backend serving frontend
    "http://127.0.0.1:3001",
    "http://127.0.0.1:8888",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type", "Authorization"],
)


# ==============================================================================
# Security Headers Middleware
# ==============================================================================

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all HTTP responses."""

    async def dispatch(self, request, call_next):
        response = await call_next(request)

        # Prevent clickjacking attacks
        response.headers["X-Frame-Options"] = "DENY"

        # Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Enable XSS protection
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Control referrer information
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Restrict browser features
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"

        return response


app.add_middleware(SecurityHeadersMiddleware)


# ==============================================================================
# Initialize Managers
# ==============================================================================

manager = ConnectionManager()
session_index = SessionIndex()

# Inject dependencies into routers
set_heuristics_manager(manager)
set_knowledge_manager(manager)
set_session_index(session_index)
set_admin_paths(EMERGENT_LEARNING_PATH)
set_fraud_paths(EMERGENT_LEARNING_PATH)
set_workflows_paths(EMERGENT_LEARNING_PATH)


# ==============================================================================
# Mount Routers
# ==============================================================================

app.include_router(analytics_router)
app.include_router(heuristics_router)
app.include_router(runs_router)
app.include_router(knowledge_router)
app.include_router(queries_router)
app.include_router(sessions_router)
app.include_router(admin_router)
app.include_router(fraud_router)
app.include_router(workflows_router)
app.include_router(context_router)
app.include_router(auth_router)
app.include_router(game_router)
app.include_router(setup_router)


# ==============================================================================
# Background Task: Monitor for Changes
# ==============================================================================

async def monitor_changes():
    """Monitor database for changes and broadcast updates."""
    last_metrics_count = 0
    last_trail_count = 0
    last_run_count = 0
    last_heuristics_count = 0
    last_learnings_count = 0
    last_decisions_count = 0
    last_invariants_count = 0
    last_session_scan = None

    while True:
        try:
            with get_db() as conn:
                cursor = conn.cursor()

                # Check for new metrics
                cursor.execute("SELECT COUNT(*) FROM metrics")
                metrics_count = cursor.fetchone()[0]

                cursor.execute("SELECT COUNT(*) FROM trails")
                trail_count = cursor.fetchone()[0]

                cursor.execute("SELECT COUNT(*) FROM workflow_runs")
                run_count = cursor.fetchone()[0]

                cursor.execute("SELECT COUNT(*) FROM heuristics")
                heuristics_count = cursor.fetchone()[0]

                cursor.execute("SELECT COUNT(*) FROM learnings")
                learnings_count = cursor.fetchone()[0]

                cursor.execute("SELECT COUNT(*) FROM decisions")
                decisions_count = cursor.fetchone()[0]

                cursor.execute("SELECT COUNT(*) FROM invariants")
                invariants_count = cursor.fetchone()[0]

                # Broadcast if changes detected
                if metrics_count > last_metrics_count:
                    cursor.execute("""
                        SELECT metric_type, metric_name, metric_value, timestamp
                        FROM metrics
                        ORDER BY timestamp DESC
                        LIMIT 5
                    """)
                    recent = [dict_from_row(r) for r in cursor.fetchall()]
                    await manager.broadcast_update("metrics", {"recent": recent})
                    last_metrics_count = metrics_count

                if trail_count > last_trail_count:
                    cursor.execute("""
                        SELECT location, scent, strength, agent_id, message, created_at
                        FROM trails
                        ORDER BY created_at DESC
                        LIMIT 5
                    """)
                    recent = [dict_from_row(r) for r in cursor.fetchall()]
                    await manager.broadcast_update("trails", {"recent": recent})
                    last_trail_count = trail_count

                if run_count > last_run_count:
                    cursor.execute("""
                        SELECT id, workflow_name, status, phase, created_at
                        FROM workflow_runs
                        ORDER BY created_at DESC
                        LIMIT 1
                    """)
                    recent = dict_from_row(cursor.fetchone())
                    await manager.broadcast_update("runs", {"latest": recent})
                    last_run_count = run_count

                if heuristics_count > last_heuristics_count:
                    cursor.execute("""
                        SELECT id, domain, rule, confidence, is_golden, updated_at
                        FROM heuristics
                        ORDER BY updated_at DESC
                        LIMIT 5
                    """)
                    recent = [dict_from_row(r) for r in cursor.fetchall()]
                    await manager.broadcast_update("heuristics", {"recent": recent})
                    last_heuristics_count = heuristics_count

                if learnings_count > last_learnings_count:
                    cursor.execute("""
                        SELECT id, type, title, summary, domain, created_at
                        FROM learnings
                        ORDER BY created_at DESC
                        LIMIT 5
                    """)
                    recent = [dict_from_row(r) for r in cursor.fetchall()]
                    await manager.broadcast_update("learnings", {"recent": recent})
                    last_learnings_count = learnings_count

                if decisions_count > last_decisions_count:
                    cursor.execute("""
                        SELECT id, title, status, domain, created_at
                        FROM decisions
                        ORDER BY created_at DESC
                        LIMIT 5
                    """)
                    recent = [dict_from_row(r) for r in cursor.fetchall()]
                    await manager.broadcast_update("decisions", {"recent": recent})
                    last_decisions_count = decisions_count

                if invariants_count > last_invariants_count:
                    cursor.execute("""
                        SELECT id, statement, status, severity, domain, violation_count, created_at
                        FROM invariants
                        ORDER BY created_at DESC
                        LIMIT 5
                    """)
                    recent = [dict_from_row(r) for r in cursor.fetchall()]
                    await manager.broadcast_update("invariants", {"recent": recent})
                    last_invariants_count = invariants_count

            # Rescan session index every 5 minutes
            current_time = datetime.now()
            if last_session_scan is None or (current_time - last_session_scan).total_seconds() > 300:
                try:
                    session_count = session_index.scan()
                    logger.info(f"Session index refreshed: {session_count} sessions")
                    last_session_scan = current_time
                except Exception as e:
                    logger.error(f"Session index scan error: {e}", exc_info=True)

        except Exception as e:
            logger.error(f"Monitor error: {e}", exc_info=True)

        await asyncio.sleep(2)  # Check every 2 seconds


@app.on_event("startup")
async def startup_event():
    # Initialize project context
    ctx = init_project_context()
    if ctx.has_project:
        logger.info(f"Project context detected: {ctx.project_name} at {ctx.project_root}")
    else:
        logger.info("No project context - using global scope only")

    # Initialize Peewee database and create tables
    # MUST happen before monitor_changes() tries to query metrics table
    try:
        await initialize_database()
        logger.info("Peewee database initialized")

        await create_tables()
        logger.info("All database tables created/verified")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}", exc_info=True)
        raise

    # Initial session index scan
    try:
        session_count = session_index.scan()
        logger.info(f"Initial session index scan: {session_count} sessions")
    except Exception as e:
        logger.error(f"Failed to scan session index on startup: {e}", exc_info=True)

    # Start background monitoring
    asyncio.create_task(monitor_changes())
    asyncio.create_task(run_auto_summarizer())

    # Start auto-capture background job
    asyncio.create_task(auto_capture.start())
    logger.info("Auto-capture background job started")


@app.on_event("shutdown")
async def shutdown_event():
    # Stop auto-capture gracefully
    auto_capture.stop()
    logger.info("Auto-capture background job stopped")


# ==============================================================================
# WebSocket Endpoint
# ==============================================================================

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        # Send initial state
        await websocket.send_json({
            "type": "connected",
            "timestamp": datetime.now().isoformat(),
            "message": "Connected to Emergent Learning Dashboard"
        })

        while True:
            # Keep connection alive, handle any incoming messages
            try:
                data = await websocket.receive_text()
                if data == "ping":
                    await websocket.send_json({"type": "pong"})
            except Exception as e:
                logger.warning(f"WebSocket receive error: {e}")
                break

    except WebSocketDisconnect:
        logger.info("Client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        manager.disconnect(websocket)


# ==============================================================================
# Serve Frontend (Production)
# ==============================================================================

if FRONTEND_PATH.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_PATH / "assets"), name="assets")

    @app.get("/{path:path}")
    async def serve_frontend(path: str):
        # Don't serve frontend for API paths
        if path.startswith("api/"):
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Not found")

        file_path = FRONTEND_PATH / path
        if file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(FRONTEND_PATH / "index.html")


# ==============================================================================
# Main
# ==============================================================================

if __name__ == "__main__":
    import uvicorn
    # SECURITY: Bind to localhost only - prevents exposure on public networks
    uvicorn.run(app, host="127.0.0.1", port=8888, reload=True)
