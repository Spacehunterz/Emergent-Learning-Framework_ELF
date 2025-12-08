#!/usr/bin/env python3
"""
Replay: Re-run workflows from specific nodes.

This module provides replay functionality for conductor workflows:
- Re-run from a specific node
- Retry failed nodes
- Clone and modify workflows
- Dry-run to preview execution plan

USAGE:
    python replay.py --run-id 123 --from-node "analyze"
    python replay.py --run-id 123 --retry-failed
    python replay.py --run-id 123 --dry-run
"""

import json
import sqlite3
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
from contextlib import contextmanager
import argparse


class ReplayManager:
    """Manage workflow replay and retry operations."""

    def __init__(self, base_path: Optional[str] = None):
        if base_path is None:
            home = Path.home()
            self.base_path = home / ".claude" / "emergent-learning"
        else:
            self.base_path = Path(base_path)

        self.db_path = self.base_path / "memory" / "index.db"

    @contextmanager
    def _get_connection(self):
        """Get database connection."""
        conn = sqlite3.connect(str(self.db_path), timeout=10.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA busy_timeout=10000")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def get_run_info(self, run_id: int) -> Optional[Dict]:
        """Get full information about a workflow run."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Get run
            cursor.execute("SELECT * FROM workflow_runs WHERE id = ?", (run_id,))
            row = cursor.fetchone()
            if not row:
                return None

            run = dict(row)
            run["input"] = json.loads(run.get("input_json", "{}"))
            run["output"] = json.loads(run.get("output_json", "{}"))
            run["context"] = json.loads(run.get("context_json", "{}"))

            # Get executions
            cursor.execute("""
                SELECT * FROM node_executions
                WHERE run_id = ?
                ORDER BY created_at
            """, (run_id,))
            run["executions"] = [dict(r) for r in cursor.fetchall()]

            return run

    def get_failed_nodes(self, run_id: int) -> List[Dict]:
        """Get all failed nodes from a run."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM node_executions
                WHERE run_id = ? AND status = 'failed'
                ORDER BY created_at
            """, (run_id,))
            return [dict(r) for r in cursor.fetchall()]

    def get_node_by_id(self, run_id: int, node_id: str) -> Optional[Dict]:
        """Get a specific node execution."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM node_executions
                WHERE run_id = ? AND node_id = ?
                ORDER BY created_at DESC
                LIMIT 1
            """, (run_id, node_id))
            row = cursor.fetchone()
            return dict(row) if row else None

    def create_replay_run(self, original_run_id: int, from_node: str = None,
                          include_context: bool = True) -> int:
        """
        Create a new run that replays from a specific point.

        Args:
            original_run_id: Original run to replay from
            from_node: Node ID to start from (None = beginning)
            include_context: Include context built up to that node

        Returns:
            New run ID
        """
        original = self.get_run_info(original_run_id)
        if not original:
            raise ValueError(f"Run {original_run_id} not found")

        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Build context up to from_node if requested
            replay_context = original.get("input", {}).copy()
            if include_context and from_node:
                for exec_record in original["executions"]:
                    if exec_record["node_id"] == from_node:
                        break
                    if exec_record["status"] == "completed":
                        try:
                            result = json.loads(exec_record.get("result_json", "{}"))
                            replay_context.update(result)
                        except json.JSONDecodeError:
                            pass

            # Create new run
            cursor.execute("""
                INSERT INTO workflow_runs
                (workflow_id, workflow_name, status, phase, input_json, started_at)
                VALUES (?, ?, 'pending', 'replay', ?, ?)
            """, (
                original.get("workflow_id"),
                f"replay-{original.get('workflow_name', 'unknown')}-from-{from_node or 'start'}",
                json.dumps(replay_context),
                datetime.now().isoformat()
            ))

            new_run_id = cursor.lastrowid

            # Log the replay decision
            cursor.execute("""
                INSERT INTO conductor_decisions
                (run_id, decision_type, decision_data, reason)
                VALUES (?, 'replay', ?, ?)
            """, (
                new_run_id,
                json.dumps({
                    "original_run_id": original_run_id,
                    "from_node": from_node,
                    "include_context": include_context
                }),
                f"Replay of run {original_run_id} from {from_node or 'start'}"
            ))

            return new_run_id

    def retry_failed_nodes(self, run_id: int, dry_run: bool = False) -> Dict:
        """
        Retry all failed nodes from a run.

        Args:
            run_id: Run to retry failed nodes from
            dry_run: If True, just return what would be retried

        Returns:
            Dict with retry information
        """
        failed = self.get_failed_nodes(run_id)

        if not failed:
            return {"message": "No failed nodes to retry", "nodes": []}

        result = {
            "original_run_id": run_id,
            "failed_nodes": len(failed),
            "nodes": []
        }

        for node in failed:
            node_info = {
                "node_id": node["node_id"],
                "node_name": node["node_name"],
                "error_message": node.get("error_message"),
                "original_prompt": node.get("prompt", "")[:200] + "..."
            }
            result["nodes"].append(node_info)

        if dry_run:
            result["dry_run"] = True
            return result

        # Create retry run
        new_run_id = self.create_replay_run(run_id, include_context=True)
        result["new_run_id"] = new_run_id

        # Mark which nodes to retry
        with self._get_connection() as conn:
            cursor = conn.cursor()
            for node in failed:
                cursor.execute("""
                    INSERT INTO node_executions
                    (run_id, node_id, node_name, node_type, prompt, status)
                    VALUES (?, ?, ?, ?, ?, 'pending')
                """, (
                    new_run_id,
                    node["node_id"],
                    node["node_name"],
                    node.get("node_type", "single"),
                    node.get("prompt", "")
                ))

        return result

    def clone_run(self, run_id: int, modifications: Dict = None) -> int:
        """
        Clone a run with optional modifications.

        Args:
            run_id: Run to clone
            modifications: Dict of modifications to apply:
                - input: Override input data
                - context: Override context
                - skip_nodes: List of node IDs to skip

        Returns:
            New run ID
        """
        original = self.get_run_info(run_id)
        if not original:
            raise ValueError(f"Run {run_id} not found")

        modifications = modifications or {}

        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Merge modifications
            new_input = original.get("input", {}).copy()
            new_input.update(modifications.get("input", {}))

            # Create cloned run
            cursor.execute("""
                INSERT INTO workflow_runs
                (workflow_id, workflow_name, status, phase, input_json, started_at)
                VALUES (?, ?, 'pending', 'init', ?, ?)
            """, (
                original.get("workflow_id"),
                f"clone-{original.get('workflow_name', 'unknown')}",
                json.dumps(new_input),
                datetime.now().isoformat()
            ))

            new_run_id = cursor.lastrowid

            # Log the clone
            cursor.execute("""
                INSERT INTO conductor_decisions
                (run_id, decision_type, decision_data, reason)
                VALUES (?, 'clone', ?, ?)
            """, (
                new_run_id,
                json.dumps({
                    "original_run_id": run_id,
                    "modifications": modifications
                }),
                f"Clone of run {run_id}"
            ))

            return new_run_id

    def get_replay_plan(self, run_id: int, from_node: str = None) -> Dict:
        """
        Get a preview of what would be replayed.

        Returns execution plan without actually executing.
        """
        original = self.get_run_info(run_id)
        if not original:
            raise ValueError(f"Run {run_id} not found")

        plan = {
            "original_run_id": run_id,
            "from_node": from_node,
            "total_nodes": len(original.get("executions", [])),
            "nodes_to_skip": [],
            "nodes_to_replay": [],
            "context_at_start": {}
        }

        found_start = from_node is None
        context = original.get("input", {}).copy()

        for exec_record in original.get("executions", []):
            node_info = {
                "node_id": exec_record["node_id"],
                "node_name": exec_record["node_name"],
                "original_status": exec_record["status"],
                "duration_ms": exec_record.get("duration_ms")
            }

            if not found_start:
                if exec_record["node_id"] == from_node:
                    found_start = True
                    plan["context_at_start"] = context.copy()
                    plan["nodes_to_replay"].append(node_info)
                else:
                    # Build up context from completed nodes
                    if exec_record["status"] == "completed":
                        try:
                            result = json.loads(exec_record.get("result_json", "{}"))
                            context.update(result)
                        except json.JSONDecodeError:
                            pass
                    plan["nodes_to_skip"].append(node_info)
            else:
                plan["nodes_to_replay"].append(node_info)

        return plan

    def reset_node(self, run_id: int, node_id: str) -> bool:
        """
        Reset a node to pending status for re-execution.

        Args:
            run_id: Workflow run ID
            node_id: Node to reset

        Returns:
            True if node was reset
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                UPDATE node_executions
                SET status = 'pending',
                    result_json = '{}',
                    result_text = NULL,
                    error_message = NULL,
                    completed_at = NULL,
                    retry_count = retry_count + 1
                WHERE run_id = ? AND node_id = ?
            """, (run_id, node_id))

            if cursor.rowcount > 0:
                # Log the reset
                cursor.execute("""
                    INSERT INTO conductor_decisions
                    (run_id, decision_type, decision_data, reason)
                    VALUES (?, 'reset_node', ?, ?)
                """, (
                    run_id,
                    json.dumps({"node_id": node_id}),
                    f"Reset node {node_id} for re-execution"
                ))
                return True

            return False


def format_plan(plan: Dict) -> str:
    """Format replay plan for display."""
    lines = [
        f"Replay Plan for Run #{plan['original_run_id']}",
        f"From Node: {plan['from_node'] or 'beginning'}",
        f"Total Nodes: {plan['total_nodes']}",
        ""
    ]

    if plan["nodes_to_skip"]:
        lines.append("Nodes to SKIP (already completed):")
        for n in plan["nodes_to_skip"]:
            status_icon = "✓" if n["original_status"] == "completed" else "✗"
            lines.append(f"  {status_icon} {n['node_name']} ({n['node_id']})")
        lines.append("")

    if plan["nodes_to_replay"]:
        lines.append("Nodes to REPLAY:")
        for n in plan["nodes_to_replay"]:
            status_icon = "→"
            lines.append(f"  {status_icon} {n['node_name']} ({n['node_id']})")
        lines.append("")

    if plan["context_at_start"]:
        lines.append("Context at start:")
        for k, v in list(plan["context_at_start"].items())[:5]:
            val_str = str(v)[:50] + "..." if len(str(v)) > 50 else str(v)
            lines.append(f"  {k}: {val_str}")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Replay workflows from specific nodes")

    parser.add_argument("--run-id", type=int, required=True, help="Workflow run ID")
    parser.add_argument("--from-node", help="Node ID to replay from")
    parser.add_argument("--retry-failed", action="store_true", help="Retry all failed nodes")
    parser.add_argument("--reset-node", help="Reset a specific node to pending")
    parser.add_argument("--clone", action="store_true", help="Clone the run")
    parser.add_argument("--dry-run", action="store_true", help="Preview without executing")
    parser.add_argument("--info", action="store_true", help="Show run information")
    parser.add_argument("--format", choices=["text", "json"], default="text")

    args = parser.parse_args()

    manager = ReplayManager()

    try:
        if args.info:
            run = manager.get_run_info(args.run_id)
            if not run:
                print(f"Run {args.run_id} not found")
                return 1

            if args.format == "json":
                print(json.dumps(run, indent=2, default=str))
            else:
                print(f"Run #{run['id']}: {run.get('workflow_name', 'Unknown')}")
                print(f"Status: {run['status']}")
                print(f"Phase: {run['phase']}")
                print(f"Nodes: {run['completed_nodes']}/{run['total_nodes']} completed, {run['failed_nodes']} failed")
                print(f"Started: {run['started_at']}")
                print(f"Completed: {run['completed_at'] or 'Running'}")
                print("\nExecutions:")
                for ex in run.get("executions", []):
                    icon = "✓" if ex["status"] == "completed" else "✗" if ex["status"] == "failed" else "○"
                    print(f"  {icon} {ex['node_name']} ({ex['status']})")

        elif args.retry_failed:
            result = manager.retry_failed_nodes(args.run_id, dry_run=args.dry_run)
            if args.format == "json":
                print(json.dumps(result, indent=2))
            else:
                if result.get("dry_run"):
                    print("DRY RUN - Would retry these nodes:")
                else:
                    print(f"Created retry run #{result.get('new_run_id')}")

                for n in result.get("nodes", []):
                    print(f"  - {n['node_name']}: {n.get('error_message', 'Unknown error')[:50]}")

        elif args.reset_node:
            if manager.reset_node(args.run_id, args.reset_node):
                print(f"Reset node {args.reset_node} to pending")
            else:
                print(f"Node {args.reset_node} not found in run {args.run_id}")
                return 1

        elif args.clone:
            new_id = manager.clone_run(args.run_id)
            print(f"Cloned run {args.run_id} -> {new_id}")

        elif args.from_node or args.dry_run:
            plan = manager.get_replay_plan(args.run_id, args.from_node)
            if args.format == "json":
                print(json.dumps(plan, indent=2))
            else:
                print(format_plan(plan))

            if not args.dry_run and args.from_node:
                new_id = manager.create_replay_run(args.run_id, args.from_node)
                print(f"\nCreated replay run #{new_id}")

        else:
            # Default: show plan
            plan = manager.get_replay_plan(args.run_id)
            print(format_plan(plan))

    except Exception as e:
        print(f"Error: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
