#!/usr/bin/env python3
"""
Query Conductor: Query interface for workflow executions and trails.

This extends the existing query.py with conductor-specific queries:
- --workflows: List all workflow runs
- --workflow <id>: Show detailed graph state
- --failures: Show failed nodes with prompts
- --trails: Show hot spots from swarm phases
- --executions: Show recent node executions

Usage:
    python query_conductor.py --workflows
    python query_conductor.py --workflow 123
    python query_conductor.py --failures --limit 10
    python query_conductor.py --trails --scent blocker
    python query_conductor.py --hotspots --limit 20
"""

import sqlite3
import os
import sys
import io
import argparse
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
from contextlib import contextmanager

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')


class ConductorQuery:
    """Query interface for conductor data."""

    def __init__(self, base_path: Optional[str] = None):
        if base_path is None:
            home = Path.home()
            self.base_path = home / ".claude" / "emergent-learning"
        else:
            self.base_path = Path(base_path)

        self.db_path = self.base_path / "memory" / "index.db"

    @contextmanager
    def _get_connection(self):
        """Get a database connection."""
        if not self.db_path.exists():
            raise FileNotFoundError(f"Database not found: {self.db_path}")

        conn = sqlite3.connect(str(self.db_path), timeout=10.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA busy_timeout=10000")
        try:
            yield conn
        finally:
            conn.close()

    # =========================================================================
    # Workflow Queries
    # =========================================================================

    def list_workflows(self, limit: int = 20) -> List[Dict]:
        """List all workflow runs with summary."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT
                    id, workflow_name, status, phase,
                    total_nodes, completed_nodes, failed_nodes,
                    started_at, completed_at, created_at
                FROM workflow_runs
                ORDER BY created_at DESC
                LIMIT ?
            """, (limit,))
            return [dict(row) for row in cursor.fetchall()]

    def get_workflow_run(self, run_id: int) -> Optional[Dict]:
        """Get detailed workflow run with all executions."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Get run info
            cursor.execute("SELECT * FROM workflow_runs WHERE id = ?", (run_id,))
            row = cursor.fetchone()
            if not row:
                return None

            run = dict(row)
            run["input"] = json.loads(run.get("input_json", "{}"))
            run["output"] = json.loads(run.get("output_json", "{}"))
            run["context"] = json.loads(run.get("context_json", "{}"))

            # Get node executions
            cursor.execute("""
                SELECT * FROM node_executions
                WHERE run_id = ?
                ORDER BY created_at
            """, (run_id,))
            executions = []
            for exec_row in cursor.fetchall():
                exec_dict = dict(exec_row)
                exec_dict["findings"] = json.loads(exec_dict.get("findings_json", "[]"))
                exec_dict["files_modified"] = json.loads(exec_dict.get("files_modified", "[]"))
                executions.append(exec_dict)
            run["executions"] = executions

            # Get decisions
            cursor.execute("""
                SELECT * FROM conductor_decisions
                WHERE run_id = ?
                ORDER BY created_at
            """, (run_id,))
            decisions = []
            for dec_row in cursor.fetchall():
                dec_dict = dict(dec_row)
                dec_dict["data"] = json.loads(dec_dict.get("decision_data", "{}"))
                decisions.append(dec_dict)
            run["decisions"] = decisions

            return run

    def get_active_runs(self) -> List[Dict]:
        """Get currently running workflows."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM workflow_runs
                WHERE status = 'running'
                ORDER BY started_at DESC
            """)
            return [dict(row) for row in cursor.fetchall()]

    # =========================================================================
    # Failure Queries
    # =========================================================================

    def get_failed_nodes(self, limit: int = 20, run_id: int = None) -> List[Dict]:
        """Get failed node executions with prompts."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            if run_id:
                cursor.execute("""
                    SELECT
                        ne.id, ne.run_id, ne.node_id, ne.node_name,
                        ne.agent_id, ne.status, ne.error_message, ne.error_type,
                        ne.prompt, ne.duration_ms, ne.created_at,
                        wr.workflow_name
                    FROM node_executions ne
                    LEFT JOIN workflow_runs wr ON ne.run_id = wr.id
                    WHERE ne.status = 'failed' AND ne.run_id = ?
                    ORDER BY ne.created_at DESC
                    LIMIT ?
                """, (run_id, limit))
            else:
                cursor.execute("""
                    SELECT
                        ne.id, ne.run_id, ne.node_id, ne.node_name,
                        ne.agent_id, ne.status, ne.error_message, ne.error_type,
                        ne.prompt, ne.duration_ms, ne.created_at,
                        wr.workflow_name
                    FROM node_executions ne
                    LEFT JOIN workflow_runs wr ON ne.run_id = wr.id
                    WHERE ne.status = 'failed'
                    ORDER BY ne.created_at DESC
                    LIMIT ?
                """, (limit,))

            return [dict(row) for row in cursor.fetchall()]

    def get_blockers(self, limit: int = 20) -> List[Dict]:
        """Get blocker trails and findings."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT
                    t.id, t.run_id, t.location, t.scent,
                    t.agent_id, t.message, t.created_at,
                    wr.workflow_name
                FROM trails t
                LEFT JOIN workflow_runs wr ON t.run_id = wr.id
                WHERE t.scent = 'blocker'
                ORDER BY t.created_at DESC
                LIMIT ?
            """, (limit,))
            return [dict(row) for row in cursor.fetchall()]

    # =========================================================================
    # Trail Queries
    # =========================================================================

    def get_trails(self, scent: str = None, location: str = None,
                   run_id: int = None, limit: int = 50) -> List[Dict]:
        """Get trails with optional filtering."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            conditions = []
            params = []

            if scent:
                conditions.append("t.scent = ?")
                params.append(scent)

            if location:
                conditions.append("t.location LIKE ?")
                params.append(f"%{location}%")

            if run_id:
                conditions.append("t.run_id = ?")
                params.append(run_id)

            where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
            params.append(limit)

            cursor.execute(f"""
                SELECT
                    t.id, t.run_id, t.location, t.location_type,
                    t.scent, t.strength, t.agent_id, t.message,
                    t.tags, t.created_at, t.expires_at,
                    wr.workflow_name
                FROM trails t
                LEFT JOIN workflow_runs wr ON t.run_id = wr.id
                {where_clause}
                ORDER BY t.strength DESC, t.created_at DESC
                LIMIT ?
            """, params)

            return [dict(row) for row in cursor.fetchall()]

    def get_hotspots(self, run_id: int = None, limit: int = 20) -> List[Dict]:
        """Get locations with most trail activity."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            run_filter = "WHERE run_id = ?" if run_id else ""
            params = [run_id] if run_id else []

            cursor.execute(f"""
                SELECT
                    location,
                    location_type,
                    COUNT(*) as trail_count,
                    MAX(strength) as max_strength,
                    SUM(strength) as total_strength,
                    GROUP_CONCAT(DISTINCT scent) as scents,
                    GROUP_CONCAT(DISTINCT agent_id) as agents,
                    MAX(created_at) as last_activity
                FROM trails
                {run_filter}
                GROUP BY location
                ORDER BY total_strength DESC
                LIMIT ?
            """, params + [limit])

            return [dict(row) for row in cursor.fetchall()]

    # =========================================================================
    # Execution Queries
    # =========================================================================

    def get_recent_executions(self, limit: int = 20, status: str = None) -> List[Dict]:
        """Get recent node executions."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            if status:
                cursor.execute("""
                    SELECT
                        ne.id, ne.run_id, ne.node_id, ne.node_name, ne.node_type,
                        ne.agent_id, ne.status, ne.duration_ms,
                        ne.created_at, ne.completed_at,
                        wr.workflow_name
                    FROM node_executions ne
                    LEFT JOIN workflow_runs wr ON ne.run_id = wr.id
                    WHERE ne.status = ?
                    ORDER BY ne.created_at DESC
                    LIMIT ?
                """, (status, limit))
            else:
                cursor.execute("""
                    SELECT
                        ne.id, ne.run_id, ne.node_id, ne.node_name, ne.node_type,
                        ne.agent_id, ne.status, ne.duration_ms,
                        ne.created_at, ne.completed_at,
                        wr.workflow_name
                    FROM node_executions ne
                    LEFT JOIN workflow_runs wr ON ne.run_id = wr.id
                    ORDER BY ne.created_at DESC
                    LIMIT ?
                """, (limit,))

            return [dict(row) for row in cursor.fetchall()]

    def get_execution_details(self, exec_id: int) -> Optional[Dict]:
        """Get full details of a node execution including prompt and result."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM node_executions WHERE id = ?", (exec_id,))
            row = cursor.fetchone()
            if row:
                result = dict(row)
                result["findings"] = json.loads(result.get("findings_json", "[]"))
                result["files_modified"] = json.loads(result.get("files_modified", "[]"))
                return result
            return None

    # =========================================================================
    # Statistics
    # =========================================================================

    def get_statistics(self) -> Dict:
        """Get conductor statistics."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            stats = {}

            # Workflow run counts by status
            cursor.execute("""
                SELECT status, COUNT(*) as count
                FROM workflow_runs
                GROUP BY status
            """)
            stats["runs_by_status"] = dict(cursor.fetchall())

            # Node execution counts by status
            cursor.execute("""
                SELECT status, COUNT(*) as count
                FROM node_executions
                GROUP BY status
            """)
            stats["executions_by_status"] = dict(cursor.fetchall())

            # Trail counts by scent
            cursor.execute("""
                SELECT scent, COUNT(*) as count
                FROM trails
                GROUP BY scent
            """)
            stats["trails_by_scent"] = dict(cursor.fetchall())

            # Total counts
            cursor.execute("SELECT COUNT(*) FROM workflow_runs")
            stats["total_runs"] = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM node_executions")
            stats["total_executions"] = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM trails")
            stats["total_trails"] = cursor.fetchone()[0]

            # Average execution duration
            cursor.execute("""
                SELECT AVG(duration_ms) FROM node_executions
                WHERE duration_ms IS NOT NULL
            """)
            avg = cursor.fetchone()[0]
            stats["avg_execution_ms"] = round(avg, 2) if avg else 0

            return stats


def format_output(data: Any, format_type: str = 'text') -> str:
    """Format query results for display."""
    if format_type == 'json':
        return json.dumps(data, indent=2, default=str)

    # Text formatting
    if isinstance(data, list):
        if not data:
            return "No results found."

        lines = []
        for i, item in enumerate(data, 1):
            lines.append(f"\n--- {i} ---")
            if isinstance(item, dict):
                for key, value in item.items():
                    if value is not None and value != "" and value != []:
                        # Truncate long values
                        val_str = str(value)
                        if len(val_str) > 100:
                            val_str = val_str[:100] + "..."
                        lines.append(f"  {key}: {val_str}")
            else:
                lines.append(f"  {item}")
        return "\n".join(lines)

    elif isinstance(data, dict):
        lines = []
        for key, value in data.items():
            if isinstance(value, (dict, list)):
                lines.append(f"\n{key}:")
                lines.append(format_output(value, format_type))
            else:
                lines.append(f"{key}: {value}")
        return "\n".join(lines)

    else:
        return str(data)


def main():
    parser = argparse.ArgumentParser(
        description="Query Conductor - Workflow execution queries",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # List recent workflow runs
    python query_conductor.py --workflows

    # Show details for a specific run
    python query_conductor.py --workflow 123

    # Show failed executions
    python query_conductor.py --failures --limit 10

    # Show blocker trails
    python query_conductor.py --blockers

    # Show hot spots (most active locations)
    python query_conductor.py --hotspots --limit 20

    # Show trails for a specific file
    python query_conductor.py --trails --location main.py

    # Show statistics
    python query_conductor.py --stats
        """
    )

    # Query options
    parser.add_argument("--workflows", action="store_true", help="List workflow runs")
    parser.add_argument("--workflow", type=int, metavar="ID", help="Show workflow run details")
    parser.add_argument("--active", action="store_true", help="Show active/running workflows")
    parser.add_argument("--failures", action="store_true", help="Show failed node executions")
    parser.add_argument("--blockers", action="store_true", help="Show blocker trails")
    parser.add_argument("--trails", action="store_true", help="Show trails")
    parser.add_argument("--hotspots", action="store_true", help="Show trail hot spots")
    parser.add_argument("--executions", action="store_true", help="Show recent executions")
    parser.add_argument("--execution", type=int, metavar="ID", help="Show execution details")
    parser.add_argument("--stats", action="store_true", help="Show statistics")

    # Filters
    parser.add_argument("--run-id", type=int, help="Filter by workflow run ID")
    parser.add_argument("--scent", type=str, help="Filter trails by scent (discovery, warning, blocker)")
    parser.add_argument("--location", type=str, help="Filter trails by location")
    parser.add_argument("--status", type=str, help="Filter by status")
    parser.add_argument("--limit", type=int, default=20, help="Limit results (default: 20)")

    # Output options
    parser.add_argument("--format", choices=["text", "json"], default="text", help="Output format")

    args = parser.parse_args()

    try:
        query = ConductorQuery()
        result = None

        if args.workflows:
            result = query.list_workflows(args.limit)

        elif args.workflow:
            result = query.get_workflow_run(args.workflow)
            if not result:
                print(f"Workflow run {args.workflow} not found")
                return 1

        elif args.active:
            result = query.get_active_runs()

        elif args.failures:
            result = query.get_failed_nodes(args.limit, args.run_id)

        elif args.blockers:
            result = query.get_blockers(args.limit)

        elif args.trails:
            result = query.get_trails(args.scent, args.location, args.run_id, args.limit)

        elif args.hotspots:
            result = query.get_hotspots(args.run_id, args.limit)

        elif args.executions:
            result = query.get_recent_executions(args.limit, args.status)

        elif args.execution:
            result = query.get_execution_details(args.execution)
            if not result:
                print(f"Execution {args.execution} not found")
                return 1

        elif args.stats:
            result = query.get_statistics()

        else:
            parser.print_help()
            return 0

        if result is not None:
            print(format_output(result, args.format))

    except FileNotFoundError as e:
        print(f"Error: {e}")
        return 1
    except Exception as e:
        print(f"Error: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
