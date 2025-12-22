"""
Runs Router - Workflow runs, hotspots, diffs, retry.
"""

from typing import Optional

from fastapi import APIRouter, HTTPException

from models import ActionResult
from utils import get_db, dict_from_row, escape_like

router = APIRouter(prefix="/api", tags=["runs"])


@router.get("/runs")
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


@router.get("/runs/{run_id}")
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


@router.get("/runs/{run_id}/diff")
async def get_run_diff(run_id: int):
    """
    Get file changes (diff) for a run.

    NOTE: This currently returns mock/example data as the system doesn't yet
    track actual file content changes. In production, this would integrate with
    git or file system monitoring to show actual diffs.
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
        diffs = []
        for trail in trails:
            location = trail["location"]
            scent = trail["scent"]
            message = trail["message"] or "Modified file"

            # Create a realistic-looking mock diff
            if scent == "blocker":
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
            cursor.execute("""
                SELECT node_name, output
                FROM node_executions
                WHERE run_id = ? AND output IS NOT NULL
                LIMIT 5
            """, (run_id,))
            executions = cursor.fetchall()

            if executions:
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


@router.post("/runs/{run_id}/retry")
async def retry_run(run_id: int) -> ActionResult:
    """Retry a failed run."""
    with get_db() as conn:
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM workflow_runs WHERE id = ?", (run_id,))
        run = cursor.fetchone()

        if not run:
            raise HTTPException(status_code=404, detail="Run not found")

        if run["status"] not in ("failed", "cancelled"):
            return ActionResult(success=False, message="Can only retry failed or cancelled runs")

        # For now, just log the retry request
        # In production, this would trigger re-execution
        return ActionResult(
            success=True,
            message=f"Retry requested for run #{run_id}",
            data={"original_run_id": run_id}
        )


@router.get("/hotspots")
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


@router.get("/hotspots/treemap")
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
