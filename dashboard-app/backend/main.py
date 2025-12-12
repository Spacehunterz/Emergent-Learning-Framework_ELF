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
import json
import logging
import os
import re
import sqlite3
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Any
from contextlib import contextmanager
from collections import defaultdict

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from starlette.middleware.base import BaseHTTPMiddleware

# Paths
EMERGENT_LEARNING_PATH = Path.home() / ".claude" / "emergent-learning"
DB_PATH = EMERGENT_LEARNING_PATH / "memory" / "index.db"
FRONTEND_PATH = Path(__file__).parent.parent / "frontend" / "dist"

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
# SQL Security
# ==============================================================================

def escape_like(s: str) -> str:
    """
    Escape SQL LIKE wildcards to prevent wildcard injection.

    Args:
        s: String to escape

    Returns:
        String with SQL LIKE wildcards escaped
    """
    return s.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')


# ==============================================================================
# Database Connection
# ==============================================================================

@contextmanager
def get_db():
    """Get database connection with row factory."""
    conn = sqlite3.connect(str(DB_PATH), timeout=10.0)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def dict_from_row(row) -> dict:
    """Convert sqlite3.Row to dict."""
    return dict(row) if row else None


# ==============================================================================
# Pydantic Models
# ==============================================================================

class HeuristicUpdate(BaseModel):
    rule: Optional[str] = None
    explanation: Optional[str] = None
    domain: Optional[str] = None
    is_golden: Optional[bool] = None


class WorkflowCreate(BaseModel):
    name: str
    description: str
    nodes: List[Dict[str, Any]]
    edges: List[Dict[str, Any]]


class QueryRequest(BaseModel):
    query: str
    limit: int = 20


class ActionResult(BaseModel):
    success: bool
    message: str
    data: Optional[Dict] = None


# ==============================================================================
# WebSocket Manager for Real-Time Updates
# ==============================================================================

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.last_state_hash = None

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        dead_connections = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.warning(f"Failed to broadcast to client: {e}")
                dead_connections.append(connection)

        # Remove dead connections
        for conn in dead_connections:
            self.active_connections.remove(conn)

    async def broadcast_update(self, update_type: str, data: dict):
        await self.broadcast({
            "type": update_type,
            "timestamp": datetime.now().isoformat(),
            "data": data
        })


manager = ConnectionManager()


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

                # Broadcast if changes detected
                if metrics_count > last_metrics_count:
                    # Get recent metrics
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

        except Exception as e:
            logger.error(f"Monitor error: {e}", exc_info=True)

        await asyncio.sleep(2)  # Check every 2 seconds


@app.on_event("startup")
async def startup_event():
    asyncio.create_task(monitor_changes())


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
# REST API: Dashboard Data
# ==============================================================================

@app.get("/api/stats")
async def get_stats():
    """Get overall statistics."""
    with get_db() as conn:
        cursor = conn.cursor()

        stats = {}

        # Counts
        cursor.execute("SELECT COUNT(*) FROM workflow_runs")
        stats["total_runs"] = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM node_executions")
        stats["total_executions"] = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM trails")
        stats["total_trails"] = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM heuristics")
        stats["total_heuristics"] = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM heuristics WHERE is_golden = 1")
        stats["golden_rules"] = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM learnings")
        stats["total_learnings"] = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM learnings WHERE type = 'failure'")
        stats["failures"] = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM learnings WHERE type = 'success'")
        stats["successes"] = cursor.fetchone()[0]

        # Get actual run success/failure counts from workflow_runs status
        cursor.execute("SELECT COUNT(*) FROM workflow_runs WHERE status = 'completed'")
        stats["successful_runs"] = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM workflow_runs WHERE status IN ('failed', 'cancelled')")
        stats["failed_runs"] = cursor.fetchone()[0]

        # Averages
        cursor.execute("SELECT AVG(confidence) FROM heuristics")
        stats["avg_confidence"] = cursor.fetchone()[0] or 0

        cursor.execute("SELECT SUM(times_validated) FROM heuristics")
        stats["total_validations"] = cursor.fetchone()[0] or 0

        cursor.execute("SELECT SUM(times_violated) FROM heuristics")
        stats["total_violations"] = cursor.fetchone()[0] or 0

        # Recent activity
        cursor.execute("""
            SELECT COUNT(*) FROM metrics
            WHERE timestamp > datetime('now', '-1 hour')
        """)
        stats["metrics_last_hour"] = cursor.fetchone()[0]

        # Runs today (actual workflow runs in last 24 hours)
        cursor.execute("""
            SELECT COUNT(*) FROM workflow_runs
            WHERE created_at > datetime('now', '-24 hours')
        """)
        stats["runs_today"] = cursor.fetchone()[0]

        # Query statistics
        cursor.execute("SELECT COUNT(*) FROM building_queries")
        stats["total_queries"] = cursor.fetchone()[0]

        cursor.execute("""
            SELECT COUNT(*) FROM building_queries
            WHERE created_at > datetime('now', '-24 hours')
        """)
        stats["queries_today"] = cursor.fetchone()[0]

        cursor.execute("""
            SELECT AVG(duration_ms) FROM building_queries
            WHERE duration_ms IS NOT NULL
        """)
        stats["avg_query_duration_ms"] = cursor.fetchone()[0] or 0

        return stats


@app.get("/api/heuristics")
async def get_heuristics(
    domain: Optional[str] = None,
    golden_only: bool = False,
    sort_by: str = "confidence",
    limit: int = 50
):
    """Get heuristics with optional filtering."""
    with get_db() as conn:
        cursor = conn.cursor()

        query = """
            SELECT id, domain, rule, explanation, confidence,
                   times_validated, times_violated, is_golden,
                   source_type, created_at, updated_at
            FROM heuristics
            WHERE 1=1
        """
        params = []

        if domain:
            query += " AND domain = ?"
            params.append(domain)

        if golden_only:
            query += " AND is_golden = 1"

        sort_map = {
            "confidence": "confidence DESC",
            "validated": "times_validated DESC",
            "violated": "times_violated DESC",
            "recent": "created_at DESC"
        }
        query += f" ORDER BY {sort_map.get(sort_by, 'confidence DESC')}"
        query += " LIMIT ?"
        params.append(limit)

        cursor.execute(query, params)
        return [dict_from_row(r) for r in cursor.fetchall()]


@app.get("/api/heuristics/{heuristic_id}")
async def get_heuristic(heuristic_id: int):
    """Get single heuristic with full details."""
    with get_db() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM heuristics WHERE id = ?
        """, (heuristic_id,))
        heuristic = dict_from_row(cursor.fetchone())

        if not heuristic:
            raise HTTPException(status_code=404, detail="Heuristic not found")

        # Get validation/violation history from metrics
        cursor.execute("""
            SELECT metric_type, timestamp, context
            FROM metrics
            WHERE tags LIKE ?
            ORDER BY timestamp DESC
            LIMIT 20
        """, (f"%heuristic_id:{heuristic_id}%",))
        heuristic["history"] = [dict_from_row(r) for r in cursor.fetchall()]

        # Get related heuristics (same domain)
        cursor.execute("""
            SELECT id, rule, confidence
            FROM heuristics
            WHERE domain = ? AND id != ?
            ORDER BY confidence DESC
            LIMIT 5
        """, (heuristic["domain"], heuristic_id))
        heuristic["related"] = [dict_from_row(r) for r in cursor.fetchall()]

        return heuristic


@app.get("/api/heuristic-graph")
async def get_heuristic_graph():
    """Get heuristic graph data for force-directed visualization.

    Returns nodes (heuristics) and edges (relationships based on domain similarity
    and concept overlap).
    """
    with get_db() as conn:
        cursor = conn.cursor()

        # Get all heuristics with their key properties
        cursor.execute("""
            SELECT id, domain, rule, explanation, confidence,
                   times_validated, times_violated, is_golden,
                   created_at
            FROM heuristics
            ORDER BY confidence DESC
        """)

        heuristics = [dict_from_row(r) for r in cursor.fetchall()]

        # Create nodes
        nodes = []
        for h in heuristics:
            nodes.append({
                "id": h["id"],
                "label": h["rule"][:50] + ("..." if len(h["rule"]) > 50 else ""),
                "fullText": h["rule"],
                "domain": h["domain"],
                "confidence": h["confidence"],
                "is_golden": bool(h["is_golden"]),
                "times_validated": h["times_validated"],
                "times_violated": h["times_violated"],
                "explanation": h["explanation"],
                "created_at": h["created_at"]
            })

        # Create edges based on:
        # 1. Same domain (strong connection)
        # 2. Keyword overlap (weaker connection)
        edges = []
        edge_id = 0

        # Group heuristics by domain for same-domain connections
        domain_map = defaultdict(list)
        for h in heuristics:
            domain_map[h["domain"]].append(h["id"])

        # Create edges for same domain
        for domain, ids in domain_map.items():
            for i, id1 in enumerate(ids):
                for id2 in ids[i+1:]:
                    edges.append({
                        "id": edge_id,
                        "source": id1,
                        "target": id2,
                        "strength": 1.0,
                        "type": "same_domain",
                        "label": domain
                    })
                    edge_id += 1

        # Create edges for keyword similarity (limit to avoid too many edges)
        # Extract keywords from rules
        def extract_keywords(text):
            """Extract significant words from rule text."""
            if not text:
                return set()
            # Remove common words and extract significant terms
            stopwords = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'should', 'could', 'may', 'might', 'must', 'can'}
            words = re.findall(r'\w+', text.lower())
            return {w for w in words if len(w) > 3 and w not in stopwords}

        # Build keyword map
        heuristic_keywords = {}
        for h in heuristics:
            keywords = extract_keywords(h["rule"])
            if h["explanation"]:
                keywords.update(extract_keywords(h["explanation"]))
            heuristic_keywords[h["id"]] = keywords

        # Find keyword-based connections (only strong overlaps)
        for i, h1 in enumerate(heuristics):
            for h2 in heuristics[i+1:]:
                # Skip if same domain (already connected)
                if h1["domain"] == h2["domain"]:
                    continue

                keywords1 = heuristic_keywords[h1["id"]]
                keywords2 = heuristic_keywords[h2["id"]]

                # Calculate overlap
                overlap = keywords1 & keywords2
                if len(overlap) >= 2:  # At least 2 common keywords
                    strength = len(overlap) / max(len(keywords1), len(keywords2))
                    if strength > 0.2:  # Only strong connections
                        edges.append({
                            "id": edge_id,
                            "source": h1["id"],
                            "target": h2["id"],
                            "strength": strength,
                            "type": "keyword_similarity",
                            "label": ", ".join(list(overlap)[:3])
                        })
                        edge_id += 1

        # Limit edges per node to avoid clutter (keep strongest connections)
        MAX_EDGES_PER_NODE = 10
        node_edge_counts = defaultdict(list)
        for edge in edges:
            node_edge_counts[edge["source"]].append(edge)
            node_edge_counts[edge["target"]].append(edge)

        # Keep only top edges per node
        edges_to_keep = set()
        for node_id, node_edges in node_edge_counts.items():
            # Sort by strength and keep top N
            sorted_edges = sorted(node_edges, key=lambda e: e["strength"], reverse=True)
            for edge in sorted_edges[:MAX_EDGES_PER_NODE]:
                edges_to_keep.add(edge["id"])

        filtered_edges = [e for e in edges if e["id"] in edges_to_keep]

        return {
            "nodes": nodes,
            "edges": filtered_edges,
            "stats": {
                "total_nodes": len(nodes),
                "total_edges": len(filtered_edges),
                "golden_rules": sum(1 for n in nodes if n["is_golden"]),
                "domains": len(domain_map)
            }
        }


@app.get("/api/hotspots")
async def get_hotspots(days: int = 7, limit: int = 50):
    """Get trail hot spots aggregated by location."""
    with get_db() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                location,
                COUNT(*) as trail_count,
                SUM(strength) as total_strength,
                GROUP_CONCAT(DISTINCT scent) as scents,
                GROUP_CONCAT(DISTINCT agent_id) as agents,
                MAX(created_at) as last_activity,
                MIN(created_at) as first_activity
            FROM trails
            WHERE created_at > datetime('now', ?)
            GROUP BY location
            ORDER BY total_strength DESC
            LIMIT ?
        """, (f'-{days} days', limit))

        hotspots = []
        for row in cursor.fetchall():
            hs = dict_from_row(row)
            hs["scents"] = hs["scents"].split(",") if hs["scents"] else []
            hs["agents"] = hs["agents"].split(",") if hs["agents"] else []
            hs["agent_count"] = len(set(hs["agents"]))

            # Get related heuristics
            location_lower = hs["location"].lower()
            filename = location_lower.split("/")[-1].split("\\")[-1]
            base_name = filename.rsplit(".", 1)[0] if "." in filename else filename

            # Escape SQL wildcards to prevent wildcard injection
            base_name_escaped = escape_like(base_name)
            cursor.execute("""
                SELECT id, rule, confidence, domain
                FROM heuristics
                WHERE LOWER(rule) LIKE ? OR LOWER(domain) LIKE ?
                ORDER BY confidence DESC
                LIMIT 3
            """, (f'%{base_name_escaped}%', f'%{base_name_escaped}%'))
            hs["related_heuristics"] = [dict_from_row(r) for r in cursor.fetchall()]

            hotspots.append(hs)

        return hotspots


@app.get("/api/hotspots/treemap")
async def get_hotspots_treemap(days: int = 7):
    """Get hot spots formatted for treemap visualization."""
    with get_db() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                location,
                SUM(strength) as value,
                GROUP_CONCAT(DISTINCT scent) as scents,
                COUNT(*) as count
            FROM trails
            WHERE created_at > datetime('now', ?)
            GROUP BY location
        """, (f'-{days} days',))

        # Build tree structure
        root = {"name": "root", "children": []}
        dir_map = {}

        for row in cursor.fetchall():
            location = row["location"]
            value = row["value"] or 0
            scents = (row["scents"] or "").split(",")

            # Determine color based on scent
            color = "#60a5fa"  # default blue
            if "blocker" in scents:
                color = "#f85149"
            elif "warning" in scents:
                color = "#d29922"
            elif "discovery" in scents:
                color = "#3fb950"

            # Parse path
            parts = location.replace("\\", "/").split("/")
            current = root

            for i, part in enumerate(parts[:-1]):
                path = "/".join(parts[:i+1])
                if path not in dir_map:
                    new_node = {"name": part, "children": [], "path": path}
                    dir_map[path] = new_node
                    current["children"].append(new_node)
                current = dir_map[path]

            # Add leaf node
            current["children"].append({
                "name": parts[-1],
                "value": value,
                "color": color,
                "scents": scents,
                "count": row["count"],
                "path": location
            })

        return root


@app.get("/api/runs")
async def get_runs(days: int = 7, limit: int = 50, status: Optional[str] = None):
    """Get workflow runs."""
    with get_db() as conn:
        cursor = conn.cursor()

        query = """
            SELECT id, workflow_id, workflow_name, status, phase,
                   total_nodes, completed_nodes, failed_nodes,
                   started_at, completed_at, created_at
            FROM workflow_runs
            WHERE created_at > datetime('now', ?)
        """
        params = [f'-{days} days']

        if status:
            query += " AND status = ?"
            params.append(status)

        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        cursor.execute(query, params)
        return [dict_from_row(r) for r in cursor.fetchall()]


@app.get("/api/runs/{run_id}")
async def get_run(run_id: int):
    """Get single run with full details."""
    with get_db() as conn:
        cursor = conn.cursor()

        # Get run
        cursor.execute("SELECT * FROM workflow_runs WHERE id = ?", (run_id,))
        run = dict_from_row(cursor.fetchone())

        if not run:
            raise HTTPException(status_code=404, detail="Run not found")

        # Get executions
        cursor.execute("""
            SELECT * FROM node_executions
            WHERE run_id = ?
            ORDER BY created_at
        """, (run_id,))
        run["executions"] = [dict_from_row(r) for r in cursor.fetchall()]

        # Get trails
        cursor.execute("""
            SELECT * FROM trails
            WHERE run_id = ?
            ORDER BY created_at
        """, (run_id,))
        run["trails"] = [dict_from_row(r) for r in cursor.fetchall()]

        # Get decisions
        cursor.execute("""
            SELECT * FROM conductor_decisions
            WHERE run_id = ?
            ORDER BY created_at
        """, (run_id,))
        run["decisions"] = [dict_from_row(r) for r in cursor.fetchall()]

        # Get workflow edges if available
        if run.get("workflow_id"):
            cursor.execute("""
                SELECT * FROM workflow_edges
                WHERE workflow_id = ?
            """, (run["workflow_id"],))
            run["edges"] = [dict_from_row(r) for r in cursor.fetchall()]

        return run


@app.get("/api/runs/{run_id}/diff")
async def get_run_diff(run_id: int):
    """
    Get file changes (diff) for a run.

    NOTE: This currently returns mock/example data as the system doesn't yet
    track actual file content changes. In production, this would integrate with
    git or file system monitoring to show actual diffs.

    Future implementation: Track file snapshots before/after each run, or
    integrate with git to show actual diffs between commits.
    """
    with get_db() as conn:
        cursor = conn.cursor()

        # Verify run exists
        cursor.execute("SELECT * FROM workflow_runs WHERE id = ?", (run_id,))
        run = cursor.fetchone()

        if not run:
            raise HTTPException(status_code=404, detail="Run not found")

        # Get trails (file locations touched) for this run
        cursor.execute("""
            SELECT DISTINCT location, scent, message
            FROM trails
            WHERE run_id = ? AND location_type = 'file'
            ORDER BY location
        """, (run_id,))
        trails = cursor.fetchall()

        # Generate mock diffs based on trails
        # TODO: Replace with actual file content tracking
        diffs = []
        for trail in trails:
            location = trail["location"]
            scent = trail["scent"]
            message = trail["message"] or "Modified file"

            # Create a realistic-looking mock diff
            if scent == "blocker":
                # Show a fix
                changes = [
                    {"type": "context", "lineNumber": 1, "oldLineNumber": 10, "newLineNumber": 10, "content": "def process_data(data):"},
                    {"type": "context", "lineNumber": 2, "oldLineNumber": 11, "newLineNumber": 11, "content": "    if not data:"},
                    {"type": "remove", "lineNumber": 3, "oldLineNumber": 12, "content": "        raise ValueError('Data is empty')"},
                    {"type": "add", "lineNumber": 4, "newLineNumber": 12, "content": "        logger.warning('Empty data received, using defaults')"},
                    {"type": "add", "lineNumber": 5, "newLineNumber": 13, "content": "        return get_default_data()"},
                    {"type": "context", "lineNumber": 6, "oldLineNumber": 13, "newLineNumber": 14, "content": "    return data"},
                ]
                diffs.append({
                    "path": location,
                    "changes": changes,
                    "additions": 2,
                    "deletions": 1
                })
            elif scent == "discovery":
                # Show new feature
                changes = [
                    {"type": "context", "lineNumber": 1, "oldLineNumber": 45, "newLineNumber": 45, "content": "class DataProcessor:"},
                    {"type": "add", "lineNumber": 2, "newLineNumber": 46, "content": "    def validate_input(self, data):"},
                    {"type": "add", "lineNumber": 3, "newLineNumber": 47, "content": "        \"\"\"Validate input data before processing.\"\"\""},
                    {"type": "add", "lineNumber": 4, "newLineNumber": 48, "content": "        if not isinstance(data, dict):"},
                    {"type": "add", "lineNumber": 5, "newLineNumber": 49, "content": "            raise TypeError('Data must be a dictionary')"},
                    {"type": "add", "lineNumber": 6, "newLineNumber": 50, "content": "        return True"},
                    {"type": "add", "lineNumber": 7, "newLineNumber": 51, "content": ""},
                    {"type": "context", "lineNumber": 8, "oldLineNumber": 46, "newLineNumber": 52, "content": "    def process(self, data):"},
                ]
                diffs.append({
                    "path": location,
                    "changes": changes,
                    "additions": 6,
                    "deletions": 0
                })
            else:
                # Generic change
                changes = [
                    {"type": "context", "lineNumber": 1, "oldLineNumber": 20, "newLineNumber": 20, "content": "# Configuration"},
                    {"type": "remove", "lineNumber": 2, "oldLineNumber": 21, "content": "DEBUG = True"},
                    {"type": "add", "lineNumber": 3, "newLineNumber": 21, "content": "DEBUG = False"},
                    {"type": "context", "lineNumber": 4, "oldLineNumber": 22, "newLineNumber": 22, "content": "TIMEOUT = 30"},
                ]
                diffs.append({
                    "path": location,
                    "changes": changes,
                    "additions": 1,
                    "deletions": 1
                })

        # If no trails found, return empty diffs with explanation
        if not diffs:
            # Check node_executions for any output that might indicate changes
            cursor.execute("""
                SELECT node_name, output
                FROM node_executions
                WHERE run_id = ? AND output IS NOT NULL
                LIMIT 5
            """, (run_id,))
            executions = cursor.fetchall()

            if executions:
                # Create synthetic diff from execution output
                for execution in executions:
                    changes = [
                        {"type": "context", "lineNumber": 1, "oldLineNumber": 1, "newLineNumber": 1, "content": f"# Changes from: {execution['node_name']}"},
                        {"type": "add", "lineNumber": 2, "newLineNumber": 2, "content": "# Output:"},
                        {"type": "add", "lineNumber": 3, "newLineNumber": 3, "content": str(execution['output'])[:100] + "..."},
                    ]
                    diffs.append({
                        "path": f"output/{execution['node_name']}.txt",
                        "changes": changes,
                        "additions": 2,
                        "deletions": 0
                    })

        return {
            "run_id": run_id,
            "diffs": diffs,
            "note": "This is mock data. Future versions will track actual file changes."
        }


@app.get("/api/timeline")
async def get_timeline(days: int = 7):
    """Get activity timeline data."""
    with get_db() as conn:
        cursor = conn.cursor()

        # Runs by day
        cursor.execute("""
            SELECT DATE(created_at) as date, COUNT(*) as runs
            FROM workflow_runs
            WHERE created_at > datetime('now', ?)
            GROUP BY DATE(created_at)
            ORDER BY date
        """, (f'-{days} days',))
        runs_by_day = [dict_from_row(r) for r in cursor.fetchall()]

        # Trails by day
        cursor.execute("""
            SELECT DATE(created_at) as date, COUNT(*) as trails, SUM(strength) as strength
            FROM trails
            WHERE created_at > datetime('now', ?)
            GROUP BY DATE(created_at)
            ORDER BY date
        """, (f'-{days} days',))
        trails_by_day = [dict_from_row(r) for r in cursor.fetchall()]

        # Validations by day
        cursor.execute("""
            SELECT DATE(timestamp) as date, COUNT(*) as validations
            FROM metrics
            WHERE metric_type = 'heuristic_validated'
              AND timestamp > datetime('now', ?)
            GROUP BY DATE(timestamp)
            ORDER BY date
        """, (f'-{days} days',))
        validations_by_day = [dict_from_row(r) for r in cursor.fetchall()]

        # Failures by day
        cursor.execute("""
            SELECT DATE(timestamp) as date, COUNT(*) as failures
            FROM metrics
            WHERE metric_type = 'auto_failure_capture'
              AND timestamp > datetime('now', ?)
            GROUP BY DATE(timestamp)
            ORDER BY date
        """, (f'-{days} days',))
        failures_by_day = [dict_from_row(r) for r in cursor.fetchall()]

        return {
            "runs": runs_by_day,
            "trails": trails_by_day,
            "validations": validations_by_day,
            "failures": failures_by_day
        }


@app.get("/api/learning-velocity")
async def get_learning_velocity(days: int = 30):
    """Get learning velocity metrics over time."""
    with get_db() as conn:
        cursor = conn.cursor()

        # Heuristics created per day
        cursor.execute("""
            SELECT DATE(created_at) as date, COUNT(*) as count
            FROM heuristics
            WHERE created_at > datetime('now', ?)
            GROUP BY DATE(created_at)
            ORDER BY date
        """, (f'-{days} days',))
        heuristics_by_day = [dict_from_row(r) for r in cursor.fetchall()]

        # Learnings created per day
        cursor.execute("""
            SELECT DATE(created_at) as date,
                   COUNT(*) as total,
                   SUM(CASE WHEN type = 'failure' THEN 1 ELSE 0 END) as failures,
                   SUM(CASE WHEN type = 'success' THEN 1 ELSE 0 END) as successes
            FROM learnings
            WHERE created_at > datetime('now', ?)
            GROUP BY DATE(created_at)
            ORDER BY date
        """, (f'-{days} days',))
        learnings_by_day = [dict_from_row(r) for r in cursor.fetchall()]

        # Golden rule promotions per day
        cursor.execute("""
            SELECT DATE(updated_at) as date, COUNT(*) as count
            FROM heuristics
            WHERE is_golden = 1
              AND updated_at > datetime('now', ?)
              AND updated_at > created_at
            GROUP BY DATE(updated_at)
            ORDER BY date
        """, (f'-{days} days',))
        promotions_by_day = [dict_from_row(r) for r in cursor.fetchall()]

        # Confidence improvement rate - track average confidence over time
        cursor.execute("""
            SELECT DATE(updated_at) as date, AVG(confidence) as avg_confidence
            FROM heuristics
            WHERE updated_at > datetime('now', ?)
            GROUP BY DATE(updated_at)
            ORDER BY date
        """, (f'-{days} days',))
        confidence_by_day = [dict_from_row(r) for r in cursor.fetchall()]

        # Calculate weekly aggregates for trend analysis
        cursor.execute("""
            SELECT
                strftime('%Y-W%W', created_at) as week,
                COUNT(*) as heuristics_count
            FROM heuristics
            WHERE created_at > datetime('now', ?)
            GROUP BY week
            ORDER BY week
        """, (f'-{days} days',))
        heuristics_by_week = [dict_from_row(r) for r in cursor.fetchall()]

        # Learning streak - consecutive days with new heuristics or learnings
        cursor.execute("""
            WITH RECURSIVE dates(date) AS (
                SELECT DATE('now')
                UNION ALL
                SELECT DATE(date, '-1 day')
                FROM dates
                WHERE date > DATE('now', ?)
            ),
            activity AS (
                SELECT DISTINCT DATE(created_at) as date
                FROM (
                    SELECT created_at FROM heuristics
                    UNION ALL
                    SELECT created_at FROM learnings
                )
            )
            SELECT COUNT(*) as streak
            FROM dates d
            INNER JOIN activity a ON d.date = a.date
            WHERE d.date <= DATE('now')
            ORDER BY d.date DESC
        """, (f'-{days} days',))
        streak_result = cursor.fetchone()
        current_streak = streak_result[0] if streak_result else 0

        # Success/failure trend - ratio over time
        cursor.execute("""
            SELECT DATE(created_at) as date,
                   COUNT(*) as total,
                   CAST(SUM(CASE WHEN type = 'success' THEN 1 ELSE 0 END) AS FLOAT) /
                   CAST(COUNT(*) AS FLOAT) as success_ratio
            FROM learnings
            WHERE created_at > datetime('now', ?)
            GROUP BY DATE(created_at)
            HAVING total > 0
            ORDER BY date
        """, (f'-{days} days',))
        success_trend = [dict_from_row(r) for r in cursor.fetchall()]

        # Calculate velocity trends (% change week over week)
        heuristics_trend = 0.0
        if len(heuristics_by_week) >= 2:
            recent_week = heuristics_by_week[-1]['heuristics_count']
            prev_week = heuristics_by_week[-2]['heuristics_count']
            if prev_week > 0:
                heuristics_trend = ((recent_week - prev_week) / prev_week) * 100

        # Total stats for the period
        total_heuristics_period = sum(d['count'] for d in heuristics_by_day)
        total_learnings_period = sum(d['total'] for d in learnings_by_day)
        total_promotions_period = sum(d['count'] for d in promotions_by_day)

        return {
            "heuristics_by_day": heuristics_by_day,
            "learnings_by_day": learnings_by_day,
            "promotions_by_day": promotions_by_day,
            "confidence_by_day": confidence_by_day,
            "heuristics_by_week": heuristics_by_week,
            "success_trend": success_trend,
            "current_streak": current_streak,
            "heuristics_trend": round(heuristics_trend, 1),
            "totals": {
                "heuristics": total_heuristics_period,
                "learnings": total_learnings_period,
                "promotions": total_promotions_period
            }
        }


@app.get("/api/events")
async def get_events(limit: int = 50):
    """Get recent events feed."""
    with get_db() as conn:
        cursor = conn.cursor()

        events = []

        # Recent metrics (last hour)
        cursor.execute("""
            SELECT metric_type, metric_name, metric_value, tags, context, timestamp
            FROM metrics
            WHERE timestamp > datetime('now', '-1 hour')
            ORDER BY timestamp DESC
            LIMIT ?
        """, (limit,))

        for row in cursor.fetchall():
            r = dict_from_row(row)
            event_type = r["metric_type"]

            # Format event message
            if event_type == "heuristic_validated":
                message = f"Heuristic validated"
            elif event_type == "heuristic_violated":
                message = f"Heuristic violated"
            elif event_type == "auto_failure_capture":
                message = f"Failure auto-captured"
            elif event_type == "golden_rule_promotion":
                message = f"New golden rule promoted!"
            elif event_type == "task_outcome":
                message = f"Task {r['metric_name']}"
            else:
                message = f"{event_type}: {r['metric_name']}"

            events.append({
                "type": event_type,
                "message": message,
                "timestamp": r["timestamp"],
                "tags": r["tags"],
                "context": r["context"]
            })

        return events


@app.get("/api/learnings")
async def get_learnings(
    type: Optional[str] = None,
    domain: Optional[str] = None,
    limit: int = 50
):
    """Get learnings (failures, successes, observations)."""
    with get_db() as conn:
        cursor = conn.cursor()

        query = "SELECT * FROM learnings WHERE 1=1"
        params = []

        if type:
            query += " AND type = ?"
            params.append(type)

        if domain:
            query += " AND domain = ?"
            params.append(domain)

        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        cursor.execute(query, params)
        return [dict_from_row(r) for r in cursor.fetchall()]


@app.get("/api/queries")
async def get_queries(
    limit: int = 50,
    since: Optional[str] = None,
    domain: Optional[str] = None,
    query_type: Optional[str] = None,
    status: Optional[str] = None,
    sort_by: str = "recent"
):
    """Get building queries with optional filtering."""
    with get_db() as conn:
        cursor = conn.cursor()

        query = """
            SELECT id, query_type, session_id, agent_id, domain, tags,
                   limit_requested, max_tokens_requested, results_returned,
                   tokens_approximated, duration_ms, status, error_message,
                   error_code, golden_rules_returned, heuristics_count,
                   learnings_count, experiments_count, ceo_reviews_count,
                   query_summary, created_at, completed_at
            FROM building_queries
            WHERE 1=1
        """
        params = []

        if since:
            query += " AND created_at > ?"
            params.append(since)

        if domain:
            query += " AND domain = ?"
            params.append(domain)

        if query_type:
            query += " AND query_type = ?"
            params.append(query_type)

        if status:
            query += " AND status = ?"
            params.append(status)

        # Apply sorting
        sort_map = {
            "recent": "created_at DESC",
            "oldest": "created_at ASC",
            "slowest": "duration_ms DESC"
        }
        query += f" ORDER BY {sort_map.get(sort_by, 'created_at DESC')}"

        query += " LIMIT ?"
        params.append(limit)

        cursor.execute(query, params)
        return [dict_from_row(r) for r in cursor.fetchall()]


@app.get("/api/ceo-inbox")
async def get_ceo_inbox():
    """Get CEO inbox items (pending decisions)."""
    import re

    ceo_inbox_path = EMERGENT_LEARNING_PATH / "ceo-inbox"
    items = []

    if not ceo_inbox_path.exists():
        return items

    for file_path in ceo_inbox_path.glob("*.md"):
        if file_path.name == "TEMPLATE.md":
            continue

        try:
            content = file_path.read_text(encoding='utf-8')

            # Parse frontmatter-style metadata from content
            title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
            priority_match = re.search(r'\*\*Priority:\*\*\s*(\w+)', content)
            status_match = re.search(r'\*\*Status:\*\*\s*(\w+)', content)
            date_match = re.search(r'\*\*Date:\*\*\s*([\d-]+)', content)

            # Get first paragraph after title as summary
            summary_match = re.search(r'^##\s+Context\s*\n+(.+?)(?=\n\n|\n##)', content, re.MULTILINE | re.DOTALL)
            summary = summary_match.group(1).strip()[:200] if summary_match else ""

            items.append({
                "filename": file_path.name,
                "title": title_match.group(1) if title_match else file_path.stem,
                "priority": priority_match.group(1) if priority_match else "Medium",
                "status": status_match.group(1) if status_match else "Pending",
                "date": date_match.group(1) if date_match else None,
                "summary": summary,
                "path": str(file_path)
            })
        except Exception as e:
            logger.error(f"Error reading CEO inbox item {file_path}: {e}")
            continue

    # Sort by priority (Critical > High > Medium > Low) then by date
    priority_order = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3}
    items.sort(key=lambda x: (priority_order.get(x["priority"], 2), x["date"] or ""))

    return items


@app.get("/api/ceo-inbox/{filename}")
async def get_ceo_inbox_item(filename: str):
    """Get full content of a CEO inbox item."""
    # Security: validate filename
    if not re.match(r'^[\w\-]+\.md$', filename):
        raise HTTPException(status_code=400, detail="Invalid filename")

    file_path = EMERGENT_LEARNING_PATH / "ceo-inbox" / filename

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Item not found")

    try:
        content = file_path.read_text(encoding='utf-8')
        return {"filename": filename, "content": content}
    except Exception as e:
        logger.error(f"Error reading CEO inbox item {filename}: {e}")
        raise HTTPException(status_code=500, detail="Failed to read item")


@app.get("/api/domains")
async def get_domains():
    """Get all domains with counts."""
    with get_db() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT domain, COUNT(*) as heuristic_count, AVG(confidence) as avg_confidence
            FROM heuristics
            GROUP BY domain
            ORDER BY heuristic_count DESC
        """)

        return [dict_from_row(r) for r in cursor.fetchall()]


@app.get("/api/anomalies")
async def get_anomalies():
    """Detect and return current anomalies."""
    anomalies = []

    with get_db() as conn:
        cursor = conn.cursor()

        # Repeated failures (same node failing multiple times)
        cursor.execute("""
            SELECT node_name, COUNT(*) as fail_count
            FROM node_executions
            WHERE status = 'failed'
              AND created_at > datetime('now', '-1 day')
            GROUP BY node_name
            HAVING fail_count >= 3
        """)
        for row in cursor.fetchall():
            anomalies.append({
                "type": "repeated_failure",
                "severity": "error",
                "message": f"Node '{row['node_name']}' failed {row['fail_count']} times in 24h",
                "data": {"node_name": row["node_name"], "count": row["fail_count"]}
            })

        # Sudden hot spots
        cursor.execute("""
            SELECT location, SUM(strength) as strength, COUNT(*) as count
            FROM trails
            WHERE created_at > datetime('now', '-1 day')
              AND location NOT IN (
                  SELECT DISTINCT location FROM trails
                  WHERE created_at <= datetime('now', '-1 day')
                    AND created_at > datetime('now', '-7 days')
              )
            GROUP BY location
            HAVING strength > 1.0
            ORDER BY strength DESC
            LIMIT 5
        """)
        for row in cursor.fetchall():
            anomalies.append({
                "type": "new_hotspot",
                "severity": "info",
                "message": f"New hot spot: {row['location']} ({row['count']} trails)",
                "data": {"location": row["location"], "strength": row["strength"]}
            })

        # Heuristics being violated frequently
        cursor.execute("""
            SELECT id, rule, times_violated, confidence
            FROM heuristics
            WHERE times_violated > 3 AND confidence > 0.5
            ORDER BY times_violated DESC
            LIMIT 5
        """)
        for row in cursor.fetchall():
            anomalies.append({
                "type": "heuristic_violations",
                "severity": "warning",
                "message": f"Heuristic violated {row['times_violated']}x: {row['rule'][:50]}...",
                "data": {"heuristic_id": row["id"], "violations": row["times_violated"]}
            })

        # Stale runs (running for too long)
        cursor.execute("""
            SELECT id, workflow_name, started_at
            FROM workflow_runs
            WHERE status = 'running'
              AND started_at < datetime('now', '-1 hour')
        """)
        for row in cursor.fetchall():
            anomalies.append({
                "type": "stale_run",
                "severity": "warning",
                "message": f"Run #{row['id']} ({row['workflow_name']}) has been running for >1 hour",
                "data": {"run_id": row["id"]}
            })

    return anomalies


# ==============================================================================
# REST API: Actions
# ==============================================================================

@app.post("/api/heuristics/{heuristic_id}/promote")
async def promote_to_golden(heuristic_id: int) -> ActionResult:
    """Promote a heuristic to golden rule."""
    with get_db() as conn:
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM heuristics WHERE id = ?", (heuristic_id,))
        heuristic = cursor.fetchone()

        if not heuristic:
            raise HTTPException(status_code=404, detail="Heuristic not found")

        if heuristic["is_golden"]:
            return ActionResult(success=False, message="Already a golden rule")

        cursor.execute("""
            UPDATE heuristics
            SET is_golden = 1, updated_at = ?
            WHERE id = ?
        """, (datetime.now().isoformat(), heuristic_id))

        # Log the promotion
        cursor.execute("""
            INSERT INTO metrics (metric_type, metric_name, metric_value, context, timestamp)
            VALUES ('golden_rule_promotion', 'manual_promotion', ?, ?, ?)
        """, (heuristic_id, heuristic["rule"][:100], datetime.now().isoformat()))

        conn.commit()

        await manager.broadcast_update("heuristic_promoted", {
            "heuristic_id": heuristic_id,
            "rule": heuristic["rule"]
        })

        return ActionResult(success=True, message=f"Promoted to golden rule")


@app.post("/api/heuristics/{heuristic_id}/demote")
async def demote_from_golden(heuristic_id: int) -> ActionResult:
    """Demote a golden rule back to regular heuristic."""
    with get_db() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE heuristics
            SET is_golden = 0, updated_at = ?
            WHERE id = ?
        """, (datetime.now().isoformat(), heuristic_id))

        conn.commit()

        return ActionResult(success=True, message="Demoted from golden rule")


@app.put("/api/heuristics/{heuristic_id}")
async def update_heuristic(heuristic_id: int, update: HeuristicUpdate) -> ActionResult:
    """Update a heuristic."""
    with get_db() as conn:
        cursor = conn.cursor()

        updates = []
        params = []

        if update.rule is not None:
            updates.append("rule = ?")
            params.append(update.rule)

        if update.explanation is not None:
            updates.append("explanation = ?")
            params.append(update.explanation)

        if update.domain is not None:
            updates.append("domain = ?")
            params.append(update.domain)

        if update.is_golden is not None:
            updates.append("is_golden = ?")
            params.append(1 if update.is_golden else 0)

        if not updates:
            return ActionResult(success=False, message="No updates provided")

        updates.append("updated_at = ?")
        params.append(datetime.now().isoformat())
        params.append(heuristic_id)

        cursor.execute(f"""
            UPDATE heuristics
            SET {", ".join(updates)}
            WHERE id = ?
        """, params)

        conn.commit()

        return ActionResult(success=True, message="Heuristic updated")


@app.delete("/api/heuristics/{heuristic_id}")
async def delete_heuristic(heuristic_id: int) -> ActionResult:
    """Delete a heuristic."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM heuristics WHERE id = ?", (heuristic_id,))
        conn.commit()

        return ActionResult(success=True, message="Heuristic deleted")


@app.post("/api/runs/{run_id}/retry")
async def retry_run(run_id: int) -> ActionResult:
    """Retry a failed run."""
    # This would integrate with the replay.py functionality
    try:
        sys.path.insert(0, str(EMERGENT_LEARNING_PATH / "conductor"))
        from replay import ReplayManager

        replay = ReplayManager()
        new_run_id = replay.create_replay_run(run_id)

        return ActionResult(
            success=True,
            message=f"Created retry run #{new_run_id}",
            data={"new_run_id": new_run_id}
        )
    except Exception as e:
        logger.error(f"Error retrying run {run_id}: {e}", exc_info=True)
        return ActionResult(success=False, message="Failed to retry workflow run. Please try again.")


@app.post("/api/open-in-editor")
async def open_in_editor(path: str = Query(...)):
    """Open a file in VS Code."""
    try:
        # Normalize path
        file_path = Path(path).resolve()

        # SECURITY: Only allow opening files within emergent-learning directory
        allowed_root = EMERGENT_LEARNING_PATH.resolve()
        if not str(file_path).startswith(str(allowed_root)):
            return ActionResult(success=False, message="Access denied: path outside allowed directory")

        if not file_path.exists():
            return ActionResult(success=False, message="File not found")

        # SECURITY: Removed shell=True to prevent command injection
        subprocess.Popen(["code", "-g", str(file_path)])

        return ActionResult(success=True, message=f"Opened {path} in VS Code")
    except Exception as e:
        logger.error(f"Error opening file in editor: {e}", exc_info=True)
        return ActionResult(success=False, message="Failed to open file in editor. Please try again.")


# ==============================================================================
# REST API: Natural Language Query
# ==============================================================================

@app.post("/api/query")
async def natural_language_query(request: QueryRequest):
    """Natural language query interface."""
    query = request.query.lower()
    results = {
        "query": request.query,
        "heuristics": [],
        "learnings": [],
        "hotspots": [],
        "runs": [],
        "summary": ""
    }

    with get_db() as conn:
        cursor = conn.cursor()

        # Extract keywords
        keywords = re.findall(r'\b\w{3,}\b', query)
        # Escape each keyword individually before joining to prevent wildcard injection
        escaped_keywords = [escape_like(kw) for kw in keywords]
        keyword_pattern = "%".join(escaped_keywords) if escaped_keywords else "%"

        # Search heuristics
        cursor.execute("""
            SELECT id, domain, rule, confidence, times_validated
            FROM heuristics
            WHERE LOWER(rule) LIKE ? OR LOWER(domain) LIKE ? OR LOWER(explanation) LIKE ?
            ORDER BY confidence DESC
            LIMIT ?
        """, (f'%{keyword_pattern}%', f'%{keyword_pattern}%', f'%{keyword_pattern}%', request.limit))
        results["heuristics"] = [dict_from_row(r) for r in cursor.fetchall()]

        # Search learnings
        cursor.execute("""
            SELECT id, type, title, summary, domain
            FROM learnings
            WHERE LOWER(title) LIKE ? OR LOWER(summary) LIKE ? OR LOWER(domain) LIKE ?
            ORDER BY created_at DESC
            LIMIT ?
        """, (f'%{keyword_pattern}%', f'%{keyword_pattern}%', f'%{keyword_pattern}%', request.limit))
        results["learnings"] = [dict_from_row(r) for r in cursor.fetchall()]

        # Search hot spots
        cursor.execute("""
            SELECT location, SUM(strength) as strength, COUNT(*) as count
            FROM trails
            WHERE LOWER(location) LIKE ?
            GROUP BY location
            ORDER BY strength DESC
            LIMIT ?
        """, (f'%{keyword_pattern}%', request.limit))
        results["hotspots"] = [dict_from_row(r) for r in cursor.fetchall()]

        # Generate summary
        h_count = len(results["heuristics"])
        l_count = len(results["learnings"])
        hs_count = len(results["hotspots"])

        results["summary"] = f"Found {h_count} heuristics, {l_count} learnings, and {hs_count} hot spots matching '{request.query}'"

    return results


# ==============================================================================
# REST API: Export
# ==============================================================================

@app.get("/api/export/{export_type}")
async def export_data(export_type: str, format: str = "json"):
    """Export data in various formats."""
    with get_db() as conn:
        cursor = conn.cursor()

        if export_type == "heuristics":
            cursor.execute("""
                SELECT id, domain, rule, explanation, confidence,
                       times_validated, times_violated, is_golden,
                       source_type, created_at, updated_at
                FROM heuristics
                ORDER BY confidence DESC
            """)
            data = [dict_from_row(r) for r in cursor.fetchall()]

        elif export_type == "runs":
            cursor.execute("""
                SELECT id, workflow_id, workflow_name, status, phase,
                       total_nodes, completed_nodes, failed_nodes,
                       started_at, completed_at, created_at
                FROM workflow_runs
                ORDER BY created_at DESC
            """)
            data = [dict_from_row(r) for r in cursor.fetchall()]

        elif export_type == "learnings":
            cursor.execute("""
                SELECT id, type, filepath, title, summary, domain, severity, created_at
                FROM learnings
                ORDER BY created_at DESC
            """)
            data = [dict_from_row(r) for r in cursor.fetchall()]

        elif export_type == "full":
            # Full export includes everything
            data = {
                "exported_at": datetime.now().isoformat(),
                "heuristics": [],
                "learnings": [],
                "runs": [],
                "trails": [],
                "metrics_summary": {}
            }

            cursor.execute("SELECT * FROM heuristics ORDER BY confidence DESC")
            data["heuristics"] = [dict_from_row(r) for r in cursor.fetchall()]

            cursor.execute("SELECT * FROM learnings ORDER BY created_at DESC")
            data["learnings"] = [dict_from_row(r) for r in cursor.fetchall()]

            cursor.execute("SELECT * FROM workflow_runs ORDER BY created_at DESC LIMIT 100")
            data["runs"] = [dict_from_row(r) for r in cursor.fetchall()]

            cursor.execute("""
                SELECT location, SUM(strength) as total_strength, COUNT(*) as count
                FROM trails
                GROUP BY location
                ORDER BY total_strength DESC
                LIMIT 100
            """)
            data["trails"] = [dict_from_row(r) for r in cursor.fetchall()]

            cursor.execute("""
                SELECT metric_type, COUNT(*) as count
                FROM metrics
                GROUP BY metric_type
            """)
            data["metrics_summary"] = {r["metric_type"]: r["count"] for r in cursor.fetchall()}
        else:
            raise HTTPException(status_code=400, detail=f"Unknown export type: {export_type}")

        return data


# ==============================================================================
# REST API: Workflow Management
# ==============================================================================

@app.get("/api/workflows")
async def get_workflows():
    """Get all workflow definitions."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT w.*, COUNT(DISTINCT we.id) as edge_count
            FROM workflows w
            LEFT JOIN workflow_edges we ON w.id = we.workflow_id
            GROUP BY w.id
            ORDER BY w.created_at DESC
        """)
        return [dict_from_row(r) for r in cursor.fetchall()]


@app.post("/api/workflows")
async def create_workflow(workflow: WorkflowCreate) -> ActionResult:
    """Create a new workflow."""
    try:
        sys.path.insert(0, str(EMERGENT_LEARNING_PATH / "conductor"))
        from conductor import Conductor

        conductor = Conductor()
        workflow_id = conductor.create_workflow(
            name=workflow.name,
            description=workflow.description,
            nodes=workflow.nodes,
            edges=workflow.edges
        )

        return ActionResult(
            success=True,
            message=f"Created workflow '{workflow.name}'",
            data={"workflow_id": workflow_id}
        )
    except Exception as e:
        logger.error(f"Error creating workflow '{workflow.name}': {e}", exc_info=True)
        return ActionResult(success=False, message="Failed to create workflow. Please check workflow configuration.")


# ==============================================================================
# Serve Frontend (Production)
# ==============================================================================

if FRONTEND_PATH.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_PATH / "assets"), name="assets")

    @app.get("/{path:path}")
    async def serve_frontend(path: str):
        # Don't serve frontend for API paths
        if path.startswith("api/"):
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
