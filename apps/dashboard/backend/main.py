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
import os
from datetime import datetime
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

# Load environment variables from .env.local (development) or .env (production)
from pathlib import Path
env_local = Path(__file__).parent / ".env.local"
env_file = env_local if env_local.exists() else Path(__file__).parent / ".env"
load_dotenv(env_file)

# Path import helpers
def _import_get_base_path() -> Optional[callable]:
    env_path = os.environ.get("ELF_BASE_PATH")
    candidates = []
    if env_path:
        candidates.append(Path(env_path))

    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / "src" / "elf_paths.py").exists():
            candidates.append(parent)
            break

    for base in candidates:
        sys.path.insert(0, str(base / "src"))
        try:
            from elf_paths import get_base_path
            return get_base_path
        except ImportError:
            continue
    return None

def get_base_path() -> Path:
    imported = _import_get_base_path()
    if imported is not None:
        return imported(Path(__file__))

    env_path = os.environ.get('ELF_BASE_PATH')
    if env_path:
        return Path(env_path)

    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / '.coordination').exists() or (parent / '.git').exists():
            return parent
    return Path.home() / ".claude" / "emergent-learning"

# Ensure src is in python path for models and utils
current_dir = Path(__file__).resolve().parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

EMERGENT_LEARNING_PATH = get_base_path()
FRONTEND_PATH = current_dir.parent / "frontend" / "dist"

# Internal imports
from utils import (
    get_db, dict_from_row,
    ConnectionManager,
    ProjectContext, init_project_context,
    AutoCapture, auto_capture
)
from utils.database import initialize_database, create_tables
from session_index import SessionIndex

# Routers
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
    setup_router,
)
from routers.auth import init_redis

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

# ==============================================================================
# Request Size Limit Middleware
# ==============================================================================

class LimitUploadSize(BaseHTTPMiddleware):
    """Limit request body size to prevent DoS"""

    def __init__(self, app, max_upload_size: int = 10 * 1024 * 1024):
        super().__init__(app)
        self.max_upload_size = max_upload_size

    async def dispatch(self, request, call_next):
        if request.method in ["POST", "PUT", "PATCH"]:
            if "content-length" in request.headers:
                content_length = int(request.headers["content-length"])
                if content_length > self.max_upload_size:
                    from fastapi.responses import JSONResponse
                    return JSONResponse(
                        {"error": "Request body too large"},
                        status_code=413
                    )
        response = await call_next(request)
        return response


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


app.add_middleware(LimitUploadSize, max_upload_size=10 * 1024 * 1024)

app.add_middleware(SecurityHeadersMiddleware)


# ==============================================================================
# Initialize Managers
# ==============================================================================

manager = ConnectionManager()
session_index = SessionIndex()

# Inject dependencies into routers
from routers.heuristics import set_manager as set_heuristics_manager
from routers.knowledge import set_manager as set_knowledge_manager
from routers.sessions import set_session_index
from routers.admin import set_paths as set_admin_paths
from routers.fraud import set_paths as set_fraud_paths
from routers.workflows import set_paths as set_workflows_paths

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
# SQL Query Whitelist (Defense-in-Depth for SQL Injection Prevention)
# ==============================================================================

ALLOWED_TABLE_CONFIGS = {
    'metrics': {
        'columns': frozenset(['id', 'metric_type', 'metric_name', 'metric_value', 'timestamp']),
        'order_by': frozenset(['timestamp', 'id', 'metric_type']),
    },
    'trails': {
        'columns': frozenset(['id', 'location', 'scent', 'strength', 'agent_id', 'message', 'created_at']),
        'order_by': frozenset(['created_at', 'id', 'strength']),
    },
    'workflow_runs': {
        'columns': frozenset(['id', 'workflow_name', 'status', 'phase', 'created_at']),
        'order_by': frozenset(['created_at', 'id']),
    },
    'heuristics': {
        'columns': frozenset(['id', 'domain', 'rule', 'confidence', 'is_golden', 'updated_at', 'created_at']),
        'order_by': frozenset(['updated_at', 'created_at', 'confidence', 'id']),
    },
    'learnings': {
        'columns': frozenset(['id', 'type', 'title', 'summary', 'domain', 'created_at']),
        'order_by': frozenset(['created_at', 'id']),
    },
    'decisions': {
        'columns': frozenset(['id', 'title', 'status', 'domain', 'created_at']),
        'order_by': frozenset(['created_at', 'id', 'status']),
    },
    'invariants': {
        'columns': frozenset(['id', 'statement', 'status', 'severity', 'domain', 'violation_count', 'created_at']),
        'order_by': frozenset(['created_at', 'id', 'violation_count', 'severity']),
    },
}

MAX_QUERY_LIMIT = 1000


def _validate_query_params(table: str, columns: str, order_by: str, limit: int) -> tuple:
    """
    Validate query parameters against whitelist to prevent SQL injection.

    Returns validated (table, columns, order_by, limit) tuple.
    Raises ValueError if validation fails.
    """
    if table not in ALLOWED_TABLE_CONFIGS:
        logger.warning(f"SQL injection blocked: invalid table '{table}'")
        raise ValueError(f"Invalid table: {table}")

    config = ALLOWED_TABLE_CONFIGS[table]

    col_list = [c.strip() for c in columns.split(',')]
    for col in col_list:
        if not col or not col.replace('_', '').isalnum():
            logger.warning(f"SQL injection blocked: invalid column format '{col}'")
            raise ValueError(f"Invalid column format: {col}")
        if col not in config['columns']:
            logger.warning(f"SQL injection blocked: column '{col}' not allowed for {table}")
            raise ValueError(f"Column '{col}' not allowed for table '{table}'")

    order_by = order_by.strip()
    if not order_by.replace('_', '').isalnum():
        logger.warning(f"SQL injection blocked: invalid order_by format '{order_by}'")
        raise ValueError(f"Invalid order_by format: {order_by}")
    if order_by not in config['order_by']:
        logger.warning(f"SQL injection blocked: order_by '{order_by}' not allowed for {table}")
        raise ValueError(f"Order by '{order_by}' not allowed for table '{table}'")

    if not isinstance(limit, int) or limit < 1:
        raise ValueError(f"Limit must be positive integer, got {limit}")
    limit = min(limit, MAX_QUERY_LIMIT)

    return table, columns, order_by, limit


# ==============================================================================
# Background Task: Monitor for Changes
# ==============================================================================

def _get_db_change_counts():
    """Synchronous DB operations for monitor_changes (runs in dedicated thread)."""
    with get_db() as conn:
        cursor = conn.cursor()

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

        return {
            'metrics': metrics_count,
            'trails': trail_count,
            'runs': run_count,
            'heuristics': heuristics_count,
            'learnings': learnings_count,
            'decisions': decisions_count,
            'invariants': invariants_count,
        }


def _get_recent_data(table: str, columns: str, order_by: str, limit: int = 5):
    """
    Fetch recent data from a table with SQL injection protection.

    All parameters are validated against whitelist before query execution.
    Runs in dedicated thread via asyncio.to_thread().
    """
    table, columns, order_by, limit = _validate_query_params(table, columns, order_by, limit)

    with get_db() as conn:
        cursor = conn.cursor()
        query = f"SELECT {columns} FROM {table} ORDER BY {order_by} DESC LIMIT ?"
        cursor.execute(query, (limit,))
        return [dict_from_row(r) for r in cursor.fetchall()]


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
            # Wrap blocking DB operations in thread to prevent blocking event loop
            counts = await asyncio.to_thread(_get_db_change_counts)

            metrics_count = counts['metrics']
            trail_count = counts['trails']
            run_count = counts['runs']
            heuristics_count = counts['heuristics']
            learnings_count = counts['learnings']
            decisions_count = counts['decisions']
            invariants_count = counts['invariants']

            # Broadcast if changes detected
            if metrics_count > last_metrics_count:
                recent = await asyncio.to_thread(
                    _get_recent_data, "metrics", "metric_type, metric_name, metric_value, timestamp", "timestamp"
                )
                await manager.broadcast_update("metrics", {"recent": recent})
                last_metrics_count = metrics_count

            if trail_count > last_trail_count:
                recent = await asyncio.to_thread(
                    _get_recent_data, "trails", "location, scent, strength, agent_id, message, created_at", "created_at"
                )
                await manager.broadcast_update("trails", {"recent": recent})
                last_trail_count = trail_count

            if run_count > last_run_count:
                recent = await asyncio.to_thread(
                    _get_recent_data, "workflow_runs", "id, workflow_name, status, phase, created_at", "created_at", 1
                )
                await manager.broadcast_update("runs", {"latest": recent[0] if recent else None})
                last_run_count = run_count

            if heuristics_count > last_heuristics_count:
                recent = await asyncio.to_thread(
                    _get_recent_data, "heuristics", "id, domain, rule, confidence, is_golden, updated_at", "updated_at"
                )
                await manager.broadcast_update("heuristics", {"recent": recent})
                last_heuristics_count = heuristics_count

            if learnings_count > last_learnings_count:
                recent = await asyncio.to_thread(
                    _get_recent_data, "learnings", "id, type, title, summary, domain, created_at", "created_at"
                )
                await manager.broadcast_update("learnings", {"recent": recent})
                last_learnings_count = learnings_count

            if decisions_count > last_decisions_count:
                recent = await asyncio.to_thread(
                    _get_recent_data, "decisions", "id, title, status, domain, created_at", "created_at"
                )
                await manager.broadcast_update("decisions", {"recent": recent})
                last_decisions_count = decisions_count

            if invariants_count > last_invariants_count:
                recent = await asyncio.to_thread(
                    _get_recent_data, "invariants", "id, statement, status, severity, domain, violation_count, created_at", "created_at"
                )
                await manager.broadcast_update("invariants", {"recent": recent})
                last_invariants_count = invariants_count

            # Rescan session index every 5 minutes
            current_time = datetime.now()
            if last_session_scan is None or (current_time - last_session_scan).total_seconds() > 300:
                try:
                    session_count = await asyncio.to_thread(session_index.scan)
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

    # Initialize async Redis for session storage
    await init_redis()

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
        await manager.disconnect(websocket)


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
