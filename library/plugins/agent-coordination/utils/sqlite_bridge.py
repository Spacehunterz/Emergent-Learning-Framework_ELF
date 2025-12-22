#!/usr/bin/env python3
"""
SQLite Bridge: Persist agent coordination data to SQLite for historical queries.

This module bridges the ephemeral blackboard.json coordination with the
persistent SQLite index.db for workflow replay and historical analysis.

ARCHITECTURE:
- Blackboard.json: Real-time coordination (fast, ephemeral)
- SQLite index.db: Persistent storage (queryable, historical)
"""

import json
import sqlite3
import hashlib
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
from contextlib import contextmanager


class SQLiteBridge:
    """Bridge findings to SQLite for historical queries."""

    def __init__(self):
        home = Path.home()
        self.db_path = home / ".claude" / "emergent-learning" / "memory" / "index.db"
        self._connection = None

    def _get_connection(self):
        """Get or create a database connection."""
        if self._connection is None:
            if not self.db_path.exists():
                return None
            try:
                self._connection = sqlite3.connect(str(self.db_path), timeout=5.0)
                self._connection.execute("PRAGMA busy_timeout=5000")
            except sqlite3.Error as e:
                # Ensure connection is closed if PRAGMA fails
                if self._connection:
                    try:
                        self._connection.close()
                    except:
                        pass
                    self._connection = None
                raise
        return self._connection

    @contextmanager
    def _safe_connection(self):
        """Context manager for safe connection handling with proper cleanup."""
        conn = None
        try:
            conn = self._get_connection()
            yield conn
        except sqlite3.Error:
            # On database errors, close and reset connection to allow recovery
            if self._connection:
                try:
                    self._connection.close()
                except:
                    pass
                self._connection = None
            raise

    def get_or_create_run(self, project_root: str) -> Optional[int]:
        """
        Get the current workflow run for this project, or create an ad-hoc one.

        Uses .coordination/run_id to track the current run.
        """
        conn = self._get_connection()
        if conn is None:
            return None

        run_file = Path(project_root) / ".coordination" / "run_id"

        # Check for existing run
        if run_file.exists():
            try:
                run_id = int(run_file.read_text().strip())
                cursor = conn.cursor()
                cursor.execute("SELECT status FROM workflow_runs WHERE id = ?", (run_id,))
                row = cursor.fetchone()
                if row and row[0] == "running":
                    return run_id
            except (ValueError, sqlite3.Error):
                pass

        # Create new ad-hoc run
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO workflow_runs
                (workflow_name, status, phase, input_json, started_at)
                VALUES (?, 'running', 'swarm', '{}', ?)
            """, (f"swarm-{Path(project_root).name}", datetime.now().isoformat()))
            conn.commit()
            run_id = cursor.lastrowid

            # Save run_id for future use
            run_file.parent.mkdir(parents=True, exist_ok=True)
            run_file.write_text(str(run_id))

            return run_id
        except sqlite3.Error as e:
            import sys
            sys.stderr.write(f"Warning: Failed to create workflow run: {e}\n")
            # Reset connection on error to allow recovery on next call
            self.close()
            return None

    def record_node_execution(self, run_id: int, agent_id: str, prompt: str,
                              output: str, status: str, findings: List[Dict],
                              files_modified: List[str], duration_ms: int = None):
        """Record a node execution to SQLite."""
        conn = self._get_connection()
        if conn is None:
            return

        prompt_str = prompt or ""
        prompt_hash = hashlib.sha256(prompt_str.encode()).hexdigest()[:16]

        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO node_executions
                (run_id, node_id, node_name, node_type, agent_id, prompt, prompt_hash,
                 status, result_text, findings_json, files_modified,
                 duration_ms, started_at, completed_at)
                VALUES (?, ?, ?, 'swarm', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                run_id,
                agent_id,
                f"swarm-{agent_id}",
                agent_id,
                prompt[:10000] if prompt else "",  # Truncate long prompts
                prompt_hash,
                status,
                output[:50000] if output else "",  # Truncate long outputs
                json.dumps(findings),
                json.dumps(files_modified),
                duration_ms,
                datetime.now().isoformat(),
                datetime.now().isoformat()
            ))

            # Update run counters
            if status == "completed":
                cursor.execute("""
                    UPDATE workflow_runs
                    SET completed_nodes = completed_nodes + 1,
                        total_nodes = total_nodes + 1
                    WHERE id = ?
                """, (run_id,))
            elif status == "failed":
                cursor.execute("""
                    UPDATE workflow_runs
                    SET failed_nodes = failed_nodes + 1,
                        total_nodes = total_nodes + 1
                    WHERE id = ?
                """, (run_id,))
            else:
                cursor.execute("""
                    UPDATE workflow_runs SET total_nodes = total_nodes + 1 WHERE id = ?
                """, (run_id,))

            conn.commit()
        except sqlite3.Error as e:
            import sys
            sys.stderr.write(f"Warning: Failed to record node execution: {e}\n")
            # Reset connection on error to allow recovery on next call
            self.close()

    def lay_trail(self, run_id: int, location: str, scent: str,
                  agent_id: str = None, message: str = None):
        """Lay a pheromone trail for swarm intelligence."""
        conn = self._get_connection()
        if conn is None:
            return

        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO trails
                (run_id, location, scent, strength, agent_id, message)
                VALUES (?, ?, ?, 1.0, ?, ?)
            """, (run_id, location, scent, agent_id, message))
            conn.commit()
        except sqlite3.Error as e:
            import sys
            sys.stderr.write(f"Warning: Failed to lay trail: {e}\n")
            # Reset connection on error to allow recovery on next call
            self.close()

    def close(self):
        """Close the database connection."""
        if self._connection:
            try:
                self._connection.close()
            except (sqlite3.Error, OSError):
                pass
            self._connection = None

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - ensures connection is closed."""
        self.close()
        return False

    def __del__(self):
        """Destructor - ensures connection cleanup."""
        self.close()


# CLI for testing
if __name__ == "__main__":
    bridge = SQLiteBridge()
    print(f"Database path: {bridge.db_path}")
    print(f"Database exists: {bridge.db_path.exists()}")

    if bridge._get_connection():
        print("Connection successful!")
        bridge.close()
    else:
        print("Could not connect to database")
