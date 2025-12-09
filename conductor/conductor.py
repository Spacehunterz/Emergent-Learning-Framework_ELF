#!/usr/bin/env python3
"""
Conductor: Workflow Orchestration for Multi-Agent Coordination

The Conductor reads workflow graphs from SQLite and fires nodes in order,
respecting edges and dependencies. It bridges the real-time blackboard
coordination with persistent SQLite storage for historical queries.

Node Types:
- single: Execute one agent with a prompt
- parallel: Execute multiple agents concurrently
- swarm: Delegate to existing blackboard-based [SWARM] coordination

Integration Points:
- Reads workflow definitions from SQLite workflows table
- Writes execution records to node_executions table
- Bridges with blackboard.json for real-time state
- Lays pheromone trails for swarm intelligence
"""

import json
import os
import sys
import sqlite3
import hashlib
import time
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any, Callable, Tuple
from contextlib import contextmanager
from dataclasses import dataclass, asdict
from enum import Enum
import re


def safe_eval_condition(condition: str, context: dict) -> bool:
    """Safely evaluate a condition string against a context dictionary."""
    if not condition or not condition.strip():
        return True
    condition = condition.strip()
    if condition.lower() == 'true':
        return True
    if condition.lower() == 'false':
        return False

    match = re.match(r"['\"](\w+)['\"]\s+not\s+in\s+context", condition)
    if match:
        return match.group(1) not in context
    match = re.match(r"['\"](\w+)['\"]\s+in\s+context", condition)
    if match:
        return match.group(1) in context

    def _parse_value(value_str) -> Union[str, int, float, bool, None]:
        value_str = value_str.strip()
        if value_str.startswith(("'", '"')) and value_str.endswith(("'", '"')):
            return value_str[1:-1]
        if value_str.lower() in ('true', 'false', 'none'):
            return {'true': True, 'false': False, 'none': None}[value_str.lower()]
        try:
            return float(value_str) if '.' in value_str else int(value_str)
        except ValueError:
            return value_str

    def _compare(ctx_value, op, compare_value) -> bool:
        if ctx_value is None or compare_value is None:
            return (ctx_value == compare_value) if op == '==' else (ctx_value != compare_value) if op == '!=' else False
        ops = {'==': lambda a,b: a==b, '!=': lambda a,b: a!=b, '>': lambda a,b: a>b, '<': lambda a,b: a<b, '>=': lambda a,b: a>=b, '<=': lambda a,b: a<=b}
        return ops.get(op, lambda a,b: False)(ctx_value, compare_value)

    for pattern in [r"context\.get\(['\"](\w+)['\"]\)\s*(==|!=|>|<|>=|<=)\s*(.+)", r"context\[['\"](\w+)['\"]\]\s*(==|!=|>|<|>=|<=)\s*(.+)"]:
        match = re.match(pattern, condition)
        if match:
            key, op, value = match.groups()
            return _compare(context.get(key), op, _parse_value(value))
    return False


# Add parent utils to path for blackboard access
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "plugins" / "agent-coordination" / "utils"))

try:
    from blackboard import Blackboard
except ImportError:
    Blackboard = None  # Will run without blackboard if not available


class NodeType(Enum):
    SINGLE = "single"
    PARALLEL = "parallel"
    SWARM = "swarm"


class NodeStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class RunStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class Node:
    """Workflow node definition."""
    id: str
    name: str
    node_type: NodeType
    prompt_template: str
    config: Dict[str, Any] = None

    def __post_init__(self):
        if self.config is None:
            self.config = {}
        if isinstance(self.node_type, str):
            self.node_type = NodeType(self.node_type)


@dataclass
class Edge:
    """Workflow edge definition."""
    from_node: str
    to_node: str
    condition: str = ""
    priority: int = 100


@dataclass
class ExecutionRecord:
    """Record of a node execution for SQLite storage."""
    run_id: int
    node_id: str
    node_name: str
    node_type: str
    agent_id: str = None
    session_id: str = None
    prompt: str = None
    prompt_hash: str = None
    status: str = "pending"
    result_json: str = "{}"
    result_text: str = None
    findings_json: str = "[]"
    files_modified: str = "[]"
    duration_ms: int = None
    token_count: int = None
    retry_count: int = 0
    started_at: str = None
    completed_at: str = None
    error_message: str = None
    error_type: str = None


class Conductor:
    """
    Workflow orchestration engine.

    Reads workflow graphs from SQLite, fires nodes in order, and logs
    all executions for historical queries.
    """

    def __init__(self, base_path: Optional[str] = None, project_root: str = "."):
        """
        Initialize the Conductor.

        Args:
            base_path: Path to emergent-learning directory (default: ~/.claude/emergent-learning)
            project_root: Project root for blackboard coordination (default: current dir)
        """
        if base_path is None:
            home = Path.home()
            self.base_path = home / ".claude" / "emergent-learning"
        else:
            self.base_path = Path(base_path)

        self.db_path = self.base_path / "memory" / "index.db"
        self.project_root = Path(project_root).resolve()

        # Initialize blackboard if available
        self.blackboard = None
        if Blackboard is not None:
            try:
                self.blackboard = Blackboard(str(self.project_root))
            except Exception as e:
                print(f"Warning: Could not initialize blackboard: {e}", file=sys.stderr)

        # Node execution callbacks (for external integration)
        self._node_executor: Optional[Callable] = None

    def set_node_executor(self, executor: Callable[[Node, Dict], Tuple[str, Dict]]) -> None:
        """
        Set the callback function for executing nodes.

        The executor receives (node, context) and returns (result_text, result_dict).
        This allows the conductor to be used with different execution backends
        (e.g., Claude API, subprocess, etc.)
        """
        self._node_executor = executor

    @contextmanager
    def _get_connection(self):
        """Get a database connection with proper settings."""
        conn = sqlite3.connect(str(self.db_path), timeout=10.0)
        conn.execute("PRAGMA busy_timeout=10000")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    # =========================================================================
    # Workflow Management
    # =========================================================================

    def create_workflow(self, name: str, description: str = "",
                       nodes: List[Dict] = None, edges: List[Dict] = None,
                       config: Dict = None) -> int:
        """
        Create a new workflow definition.

        Args:
            name: Unique workflow name
            description: Human-readable description
            nodes: List of node definitions
            edges: List of edge definitions
            config: Default workflow configuration

        Returns:
            Workflow ID
        """
        nodes = nodes or []
        edges = edges or []
        config = config or {}

        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Insert workflow
            cursor.execute("""
                INSERT INTO workflows (name, description, nodes_json, config_json)
                VALUES (?, ?, ?, ?)
            """, (name, description, json.dumps(nodes), json.dumps(config)))
            workflow_id = cursor.lastrowid

            # Insert edges
            for edge in edges:
                cursor.execute("""
                    INSERT INTO workflow_edges
                    (workflow_id, from_node, to_node, condition, priority)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    workflow_id,
                    edge.get("from_node", "__start__"),
                    edge.get("to_node", "__end__"),
                    edge.get("condition", ""),
                    edge.get("priority", 100)
                ))

            return workflow_id

    def get_workflow(self, name: str) -> Optional[Dict]:
        """Get a workflow by name."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM workflows WHERE name = ?
            """, (name,))
            row = cursor.fetchone()
            if row:
                workflow = dict(row)
                workflow["nodes"] = json.loads(workflow.pop("nodes_json", "[]"))
                workflow["config"] = json.loads(workflow.pop("config_json", "{}"))

                # Get edges
                cursor.execute("""
                    SELECT from_node, to_node, condition, priority
                    FROM workflow_edges WHERE workflow_id = ?
                    ORDER BY priority
                """, (workflow["id"],))
                workflow["edges"] = [dict(r) for r in cursor.fetchall()]

                return workflow
            return None

    def list_workflows(self) -> List[Dict]:
        """List all workflow definitions."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, name, description, created_at
                FROM workflows ORDER BY name
            """)
            return [dict(row) for row in cursor.fetchall()]

    # =========================================================================
    # Run Management
    # =========================================================================

    def start_run(self, workflow_name: str = None, workflow_id: int = None,
                  input_data: Dict = None, phase: str = "init") -> int:
        """
        Start a new workflow run.

        Args:
            workflow_name: Name of workflow to run (optional for ad-hoc)
            workflow_id: ID of workflow to run
            input_data: Initial input parameters
            phase: Initial phase name

        Returns:
            Run ID
        """
        input_data = input_data or {}

        with self._get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO workflow_runs
                (workflow_id, workflow_name, status, phase, input_json, started_at)
                VALUES (?, ?, 'running', ?, ?, ?)
            """, (
                workflow_id,
                workflow_name,
                phase,
                json.dumps(input_data),
                datetime.now().isoformat()
            ))

            run_id = cursor.lastrowid

            # Log decision
            self._log_decision(cursor, run_id, "start_run", {
                "workflow_name": workflow_name,
                "phase": phase
            }, "Workflow run started")

            return run_id

    def get_run(self, run_id: int) -> Optional[Dict]:
        """Get a workflow run by ID."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM workflow_runs WHERE id = ?", (run_id,))
            row = cursor.fetchone()
            if row:
                run = dict(row)
                run["input"] = json.loads(run.pop("input_json", "{}"))
                run["output"] = json.loads(run.pop("output_json", "{}"))
                run["context"] = json.loads(run.pop("context_json", "{}"))
                return run
            return None

    def update_run_status(self, run_id: int, status,
                          error_message: str = None, output: Dict = None):
        """Update the status of a workflow run."""
        # Convert enum to string if needed
        if hasattr(status, 'value'):
            status = status.value

        with self._get_connection() as conn:
            cursor = conn.cursor()

            updates = ["status = ?"]
            params = [status]

            if status in ("completed", "failed", "cancelled"):
                updates.append("completed_at = ?")
                params.append(datetime.now().isoformat())

            if error_message:
                updates.append("error_message = ?")
                params.append(error_message)

            if output:
                updates.append("output_json = ?")
                params.append(json.dumps(output))

            params.append(run_id)
            cursor.execute(f"""
                UPDATE workflow_runs SET {', '.join(updates)} WHERE id = ?
            """, params)

    def update_run_phase(self, run_id: int, phase: str):
        """Update the current phase of a workflow run."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE workflow_runs SET phase = ? WHERE id = ?
            """, (phase, run_id))

            self._log_decision(cursor, run_id, "phase_change", {
                "new_phase": phase
            }, f"Transitioned to {phase} phase")

    def update_run_context(self, run_id: int, context: Dict):
        """Update the shared context of a workflow run."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE workflow_runs SET context_json = ? WHERE id = ?
            """, (json.dumps(context), run_id))

    # =========================================================================
    # Node Execution
    # =========================================================================

    def record_node_start(self, run_id: int, node: Node, prompt: str,
                          agent_id: str = None) -> int:
        """
        Record the start of a node execution.

        Returns the execution record ID.
        """
        prompt_hash = hashlib.sha256(prompt.encode()).hexdigest()[:16]

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO node_executions
                (run_id, node_id, node_name, node_type, agent_id, prompt,
                 prompt_hash, status, started_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, 'running', ?)
            """, (
                run_id,
                node.id,
                node.name,
                node.node_type.value,
                agent_id,
                prompt,
                prompt_hash,
                datetime.now().isoformat()
            ))

            exec_id = cursor.lastrowid

            # Update run node count
            cursor.execute("""
                UPDATE workflow_runs SET total_nodes = total_nodes + 1 WHERE id = ?
            """, (run_id,))

            self._log_decision(cursor, run_id, "fire_node", {
                "node_id": node.id,
                "node_name": node.name,
                "node_type": node.node_type.value,
                "execution_id": exec_id
            }, f"Started node: {node.name}")

            return exec_id

    def record_node_completion(self, exec_id: int, result_text: str,
                               result_dict: Dict = None, findings: List[Dict] = None,
                               files_modified: List[str] = None, duration_ms: int = None,
                               token_count: int = None):
        """Record successful completion of a node execution."""
        result_dict = result_dict or {}
        findings = findings or []
        files_modified = files_modified or []

        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Get run_id for updating counts
            cursor.execute("SELECT run_id FROM node_executions WHERE id = ?", (exec_id,))
            row = cursor.fetchone()
            if not row:
                return
            run_id = row["run_id"]

            cursor.execute("""
                UPDATE node_executions SET
                    status = 'completed',
                    result_text = ?,
                    result_json = ?,
                    findings_json = ?,
                    files_modified = ?,
                    duration_ms = ?,
                    token_count = ?,
                    completed_at = ?
                WHERE id = ?
            """, (
                result_text,
                json.dumps(result_dict),
                json.dumps(findings),
                json.dumps(files_modified),
                duration_ms,
                token_count,
                datetime.now().isoformat(),
                exec_id
            ))

            # Update run completed count
            cursor.execute("""
                UPDATE workflow_runs SET completed_nodes = completed_nodes + 1 WHERE id = ?
            """, (run_id,))

    def record_node_failure(self, exec_id: int, error_message: str,
                            error_type: str = "error", duration_ms: int = None):
        """Record failure of a node execution."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Get run_id for updating counts
            cursor.execute("SELECT run_id, node_id FROM node_executions WHERE id = ?", (exec_id,))
            row = cursor.fetchone()
            if not row:
                return
            run_id = row["run_id"]
            node_id = row["node_id"]

            cursor.execute("""
                UPDATE node_executions SET
                    status = 'failed',
                    error_message = ?,
                    error_type = ?,
                    duration_ms = ?,
                    completed_at = ?
                WHERE id = ?
            """, (
                error_message,
                error_type,
                duration_ms,
                datetime.now().isoformat(),
                exec_id
            ))

            # Update run failed count
            cursor.execute("""
                UPDATE workflow_runs SET failed_nodes = failed_nodes + 1 WHERE id = ?
            """, (run_id,))

            self._log_decision(cursor, run_id, "node_failed", {
                "node_id": node_id,
                "execution_id": exec_id,
                "error_type": error_type,
                "error_message": error_message[:200]
            }, f"Node failed: {error_message[:100]}")

    def get_node_executions(self, run_id: int) -> List[Dict]:
        """Get all node executions for a run."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM node_executions
                WHERE run_id = ?
                ORDER BY created_at
            """, (run_id,))
            results = []
            for row in cursor.fetchall():
                record = dict(row)
                record["result"] = json.loads(record.pop("result_json", "{}"))
                record["findings"] = json.loads(record.pop("findings_json", "[]"))
                record["files_modified"] = json.loads(record.pop("files_modified", "[]"))
                results.append(record)
            return results

    # =========================================================================
    # Pheromone Trails (Swarm Intelligence)
    # =========================================================================

    def lay_trail(self, run_id: int, location: str, scent: str,
                  strength: float = 1.0, agent_id: str = None,
                  node_id: str = None, message: str = None,
                  tags: List[str] = None, ttl_hours: int = 24):
        """
        Lay a pheromone trail at a location.

        Args:
            run_id: Workflow run ID
            location: File path, function name, or concept
            scent: Trail type (discovery, warning, blocker, hot, cold)
            strength: Trail strength 0.0-1.0
            agent_id: Agent that laid the trail
            node_id: Node that laid the trail
            message: Optional description
            tags: Optional tags
            ttl_hours: Hours until trail expires
        """
        expires_at = (datetime.now() + timedelta(hours=ttl_hours)).isoformat()
        tags_str = ",".join(tags) if tags else ""

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO trails
                (run_id, location, scent, strength, agent_id, node_id,
                 message, tags, expires_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                run_id, location, scent, strength, agent_id, node_id,
                message, tags_str, expires_at
            ))

    def get_trails(self, location: str = None, scent: str = None,
                   min_strength: float = 0.0, run_id: int = None,
                   include_expired: bool = False) -> List[Dict]:
        """
        Get pheromone trails matching criteria.

        Args:
            location: Filter by location (substring match)
            scent: Filter by scent type
            min_strength: Minimum trail strength
            run_id: Filter by workflow run
            include_expired: Include expired trails
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            conditions = ["strength >= ?"]
            params = [min_strength]

            if not include_expired:
                conditions.append("(expires_at IS NULL OR expires_at > datetime('now'))")

            if location:
                conditions.append("location LIKE ?")
                params.append(f"%{location}%")

            if scent:
                conditions.append("scent = ?")
                params.append(scent)

            if run_id:
                conditions.append("run_id = ?")
                params.append(run_id)

            query = f"""
                SELECT * FROM trails
                WHERE {' AND '.join(conditions)}
                ORDER BY strength DESC, created_at DESC
                LIMIT 100
            """
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]

    def get_hot_spots(self, run_id: int = None, limit: int = 20) -> List[Dict]:
        """
        Get locations with the most trail activity.

        Returns aggregated trail data grouped by location.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            run_filter = "WHERE run_id = ?" if run_id else ""
            params = [run_id] if run_id else []

            cursor.execute(f"""
                SELECT
                    location,
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

    def decay_trails(self, decay_rate: float = 0.1):
        """
        Decay all trail strengths by a percentage.

        This simulates pheromone evaporation over time.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE trails
                SET strength = strength * (1.0 - ?)
                WHERE expires_at > datetime('now') OR expires_at IS NULL
            """, (decay_rate,))

            # Remove very weak trails
            cursor.execute("""
                DELETE FROM trails WHERE strength < 0.01
            """)

    # =========================================================================
    # Blackboard Bridge
    # =========================================================================

    def sync_findings_to_blackboard(self, run_id: int):
        """
        Sync findings from SQLite to blackboard for real-time access.

        This bridges the persistent storage with real-time coordination.
        """
        if self.blackboard is None:
            return

        executions = self.get_node_executions(run_id)
        for exec_record in executions:
            if exec_record["status"] != "completed":
                continue

            for finding in exec_record.get("findings", []):
                try:
                    self.blackboard.add_finding(
                        agent_id=exec_record.get("agent_id", "conductor"),
                        finding_type=finding.get("type", "note"),
                        content=finding.get("content", ""),
                        files=exec_record.get("files_modified", []),
                        importance=finding.get("importance", "normal"),
                        tags=finding.get("tags", [])
                    )
                except Exception as e:
                    print(f"Warning: Failed to sync finding to blackboard: {e}",
                          file=sys.stderr)

    def sync_trails_to_blackboard(self, run_id: int):
        """
        Convert trails to blackboard findings for agent visibility.
        """
        if self.blackboard is None:
            return

        hot_spots = self.get_hot_spots(run_id, limit=10)
        for spot in hot_spots:
            try:
                self.blackboard.add_finding(
                    agent_id="conductor",
                    finding_type="trail",
                    content=f"Hot spot: {spot['location']} ({spot['trail_count']} trails, scents: {spot['scents']})",
                    files=[spot["location"]] if "/" in spot["location"] else [],
                    importance="high" if spot["total_strength"] > 3.0 else "normal",
                    tags=["trail", "hot-spot"]
                )
            except Exception as e:
                print(f"Warning: Failed to sync trail to blackboard: {e}",
                      file=sys.stderr)

    # =========================================================================
    # Decision Logging
    # =========================================================================

    def _log_decision(self, cursor, run_id: int, decision_type: str,
                      data: Dict, reason: str):
        """Log a conductor decision."""
        cursor.execute("""
            INSERT INTO conductor_decisions
            (run_id, decision_type, decision_data, reason)
            VALUES (?, ?, ?, ?)
        """, (run_id, decision_type, json.dumps(data), reason))

    def get_decisions(self, run_id: int) -> List[Dict]:
        """Get all decisions for a workflow run."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM conductor_decisions
                WHERE run_id = ?
                ORDER BY created_at
            """, (run_id,))
            results = []
            for row in cursor.fetchall():
                record = dict(row)
                record["data"] = json.loads(record.pop("decision_data", "{}"))
                results.append(record)
            return results

    # =========================================================================
    # Workflow Execution
    # =========================================================================

    def execute_node(self, run_id: int, node: Node, context: Dict) -> Tuple[bool, Dict]:
        """
        Execute a single node.

        Returns (success, result_dict)
        """
        # Prepare prompt from template
        prompt = node.prompt_template.format(**context) if context else node.prompt_template

        # Record start
        exec_id = self.record_node_start(run_id, node, prompt)
        start_time = time.time()

        try:
            if self._node_executor:
                # Use external executor
                result_text, result_dict = self._node_executor(node, context)
            else:
                # Placeholder - in real usage, this would call Claude API or Task tool
                result_text = f"[Placeholder execution of {node.name}]"
                result_dict = {"placeholder": True}

            duration_ms = int((time.time() - start_time) * 1000)

            self.record_node_completion(
                exec_id,
                result_text=result_text,
                result_dict=result_dict,
                findings=result_dict.get("findings", []),
                files_modified=result_dict.get("files_modified", []),
                duration_ms=duration_ms
            )

            return True, result_dict

        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            self.record_node_failure(exec_id, str(e), "exception", duration_ms)
            return False, {"error": str(e)}

    def _build_edge_index(self, edges: List[Dict]) -> Dict[str, List[Edge]]:
        """
        Build node_id -> outgoing edges index.

        Args:
            edges: List of edge dictionaries from workflow

        Returns:
            Dictionary mapping node IDs to lists of outgoing edges
        """
        edges_from = {}
        for e in edges:
            edge = Edge(**e)
            edges_from.setdefault(edge.from_node, []).append(edge)
        return edges_from

    def _get_initial_nodes(self, edges_from: Dict[str, List[Edge]]) -> List[str]:
        """
        Get starting nodes from __start__.

        Args:
            edges_from: Dictionary mapping node IDs to outgoing edges

        Returns:
            List of node IDs to start execution from
        """
        return [e.to_node for e in edges_from.get("__start__", [])]

    def _evaluate_edge_condition(self, edge: Edge, context: Dict) -> bool:
        """
        Evaluate edge condition, returning True if should traverse.

        Args:
            edge: Edge object with optional condition
            context: Current workflow context for condition evaluation

        Returns:
            True if edge should be traversed, False otherwise
        """
        if not edge.condition:
            return True
        try:
            return safe_eval_condition(edge.condition, context)
        except Exception as e:
            sys.stderr.write(f"Warning: Condition evaluation failed for edge: {e}\n")
            return False

    def _get_next_nodes(self, current_node: str, edges_from: Dict[str, List[Edge]],
                        context: Dict) -> List[str]:
        """
        Get next nodes to traverse based on edge conditions.

        Args:
            current_node: Current node ID
            edges_from: Dictionary mapping node IDs to outgoing edges
            context: Current workflow context for condition evaluation

        Returns:
            List of next node IDs to execute
        """
        next_nodes = []
        for edge in edges_from.get(current_node, []):
            if self._evaluate_edge_condition(edge, context):
                next_nodes.append(edge.to_node)
        return next_nodes

    def run_workflow(self, workflow_name: str, input_data: Dict = None,
                     on_node_complete: Callable = None) -> int:
        """
        Execute a workflow from start to finish.

        Args:
            workflow_name: Name of workflow to run
            input_data: Initial input parameters
            on_node_complete: Callback after each node (for progress reporting)

        Returns:
            Run ID
        """
        workflow = self.get_workflow(workflow_name)
        if not workflow:
            raise ValueError(f"Workflow not found: {workflow_name}")

        input_data = input_data or {}
        run_id = self.start_run(workflow_name, workflow["id"], input_data)

        context = input_data.copy()
        nodes_by_id = {n["id"]: Node(**n) for n in workflow["nodes"]}

        # Build adjacency list from edges and get initial nodes
        edges_from = self._build_edge_index(workflow["edges"])
        current_nodes = self._get_initial_nodes(edges_from)
        completed_nodes = set()

        while current_nodes:
            # Execute current batch (could be parallel)
            next_nodes = []

            for node_id in current_nodes:
                if node_id == "__end__" or node_id in completed_nodes:
                    continue

                node = nodes_by_id.get(node_id)
                if not node:
                    continue

                success, result = self.execute_node(run_id, node, context)

                # Merge result into context
                if success and isinstance(result, dict):
                    context.update(result)

                completed_nodes.add(node_id)

                if on_node_complete:
                    on_node_complete(node_id, success, result)

                # Get next nodes based on edge conditions
                next_nodes.extend(self._get_next_nodes(node_id, edges_from, context))

            current_nodes = list(set(next_nodes))

        # Complete the run
        self.update_run_context(run_id, context)
        self.update_run_status(run_id, "completed", output=context)

        return run_id


# CLI interface
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Conductor - Workflow Orchestration")
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # List workflows
    list_parser = subparsers.add_parser("list", help="List workflows")

    # Show workflow
    show_parser = subparsers.add_parser("show", help="Show workflow details")
    show_parser.add_argument("name", help="Workflow name")

    # Show run
    run_parser = subparsers.add_parser("run", help="Show run details")
    run_parser.add_argument("run_id", type=int, help="Run ID")

    # Show hot spots
    hotspots_parser = subparsers.add_parser("hotspots", help="Show trail hot spots")
    hotspots_parser.add_argument("--run-id", type=int, help="Filter by run ID")
    hotspots_parser.add_argument("--limit", type=int, default=20, help="Number of results")

    args = parser.parse_args()

    conductor = Conductor()

    if args.command == "list":
        workflows = conductor.list_workflows()
        if workflows:
            print("Workflows:")
            for w in workflows:
                print(f"  - {w['name']}: {w.get('description', 'No description')}")
        else:
            print("No workflows defined.")

    elif args.command == "show":
        workflow = conductor.get_workflow(args.name)
        if workflow:
            print(json.dumps(workflow, indent=2, default=str))
        else:
            print(f"Workflow not found: {args.name}")

    elif args.command == "run":
        run = conductor.get_run(args.run_id)
        if run:
            print(json.dumps(run, indent=2, default=str))
            print("\nNode Executions:")
            for exec_record in conductor.get_node_executions(args.run_id):
                status_icon = "✓" if exec_record["status"] == "completed" else "✗" if exec_record["status"] == "failed" else "○"
                print(f"  {status_icon} {exec_record['node_name']} ({exec_record['status']})")
        else:
            print(f"Run not found: {args.run_id}")

    elif args.command == "hotspots":
        hotspots = conductor.get_hot_spots(args.run_id, args.limit)
        if hotspots:
            print("Hot Spots (by trail activity):")
            for h in hotspots:
                print(f"  {h['location']}")
                print(f"    Trails: {h['trail_count']}, Strength: {h['total_strength']:.2f}")
                print(f"    Scents: {h['scents']}")
        else:
            print("No trail activity found.")

    else:
        parser.print_help()
