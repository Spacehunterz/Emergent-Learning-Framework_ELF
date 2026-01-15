"""
Base repository class for generic CRUD operations.

Provides reusable database operations to eliminate code duplication across endpoints.
"""

from typing import Any, Optional
from datetime import datetime
from contextlib import AbstractContextManager
import sqlite3
import re

from .database import dict_from_row


ALLOWED_TABLES = frozenset([
    "decisions",
    "heuristics",
    "learnings",
    "experiments",
    "violations",
    "invariants",
    "assumptions",
    "spike_reports",
    "workflows",
    "workflow_runs",
    "workflow_edges",
    "node_executions",
    "trails",
    "metrics",
    "session_summaries",
    "building_queries",
    "system_health",
    "schema_version",
    "db_operations",
    "cycles",
    "conductor_decisions",
    "confidence_updates",
    "fraud_reports",
    "meta_alerts",
    "game_state",
    "tags",
    "learning_tags",
])

ALLOWED_COLUMNS = frozenset([
    "id",
    "domain",
    "rule",
    "explanation",
    "confidence",
    "times_validated",
    "times_violated",
    "is_golden",
    "is_quarantined",
    "status",
    "title",
    "context",
    "decision",
    "rationale",
    "created_at",
    "updated_at",
    "type",
    "severity",
    "summary",
    "source",
    "tags",
    "workflow_id",
    "workflow_name",
    "run_id",
    "node_id",
    "node_name",
    "node_type",
    "agent_type",
    "started_at",
    "completed_at",
    "duration_ms",
    "result_json",
    "findings_json",
    "error_message",
    "metric_type",
    "metric_name",
    "metric_value",
    "timestamp",
    "session_id",
    "session_file_path",
    "project_path",
    "score",
    "username",
    "github_id",
    "avatar_url",
    "review_outcome",
    "heuristic_id",
    "experiment_id",
    "from_node",
    "to_node",
    "condition",
    "phase",
    "total_nodes",
    "completed_nodes",
    "failed_nodes",
    "input_json",
    "output_json",
    "context_json",
    "nodes_json",
    "config_json",
    "superseded_by",
    "name",
    "description",
])

ALLOWED_ORDER_DIRECTIONS = frozenset(["ASC", "DESC"])


def _validate_identifier(name: str, allowed: frozenset, kind: str) -> str:
    if name not in allowed:
        raise ValueError(f"Invalid {kind}: {name}")
    return name


def _validate_order_by(order_by: str) -> str:
    parts = order_by.strip().split()
    if len(parts) == 1:
        column = parts[0]
        direction = "ASC"
    elif len(parts) == 2:
        column, direction = parts
    else:
        raise ValueError(f"Invalid ORDER BY clause: {order_by}")

    if column not in ALLOWED_COLUMNS:
        raise ValueError(f"Invalid column in ORDER BY: {column}")
    if direction.upper() not in ALLOWED_ORDER_DIRECTIONS:
        raise ValueError(f"Invalid direction in ORDER BY: {direction}")

    return f"{column} {direction.upper()}"


class BaseRepository:
    """
    Generic repository for common CRUD operations on any table.

    This class provides standard database operations without the need for
    table-specific code duplication. Use this for basic CRUD, then add
    custom methods for domain-specific operations.

    Usage:
        from utils import BaseRepository, get_db

        # Get a single record
        with get_db() as conn:
            repo = BaseRepository(conn)
            decision = repo.get_by_id("decisions", 1)

        # List all records with pagination
        with get_db() as conn:
            repo = BaseRepository(conn)
            decisions = repo.list_all("decisions", limit=50, offset=0)

        # List with filters
        with get_db() as conn:
            repo = BaseRepository(conn)
            active_decisions = repo.list_with_filters(
                "decisions",
                {"status": "active", "domain": "auth"},
                limit=20
            )

        # Create a new record
        with get_db() as conn:
            repo = BaseRepository(conn)
            new_id = repo.create("decisions", {
                "title": "Use JWT for auth",
                "context": "Need secure auth",
                "status": "active",
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            })

        # Update a record
        with get_db() as conn:
            repo = BaseRepository(conn)
            success = repo.update("decisions", 1, {
                "status": "superseded",
                "updated_at": datetime.now().isoformat()
            })

        # Delete a record
        with get_db() as conn:
            repo = BaseRepository(conn)
            success = repo.delete("decisions", 1)
    """

    def __init__(self, conn: sqlite3.Connection):
        """
        Initialize repository with database connection.

        Args:
            conn: SQLite database connection (from get_db() context manager)
        """
        self.conn = conn
        self.cursor = conn.cursor()

    def get_by_id(self, table: str, id: int) -> Optional[dict[str, Any]]:
        """
        Get a single record by ID.

        Args:
            table: Table name (must be in ALLOWED_TABLES whitelist)
            id: Record ID

        Returns:
            Dictionary of record data, or None if not found

        Raises:
            ValueError: If table name is not in whitelist

        Example:
            decision = repo.get_by_id("decisions", 123)
            if decision:
                print(decision["title"])
        """
        validated_table = _validate_identifier(table, ALLOWED_TABLES, "table")
        self.cursor.execute(f"SELECT * FROM {validated_table} WHERE id = ?", (id,))
        row = self.cursor.fetchone()
        return dict_from_row(row)

    def list_all(
        self,
        table: str,
        limit: int = 100,
        offset: int = 0,
        order_by: str = "created_at DESC"
    ) -> list[dict[str, Any]]:
        """
        List all records from a table with pagination.

        Args:
            table: Table name (must be in ALLOWED_TABLES whitelist)
            limit: Maximum number of records to return (default: 100)
            offset: Number of records to skip (default: 0)
            order_by: SQL ORDER BY clause (default: "created_at DESC")

        Returns:
            List of record dictionaries

        Raises:
            ValueError: If table name or order_by column is not in whitelist

        Example:
            decisions = repo.list_all("decisions", limit=50, offset=0)
            for d in decisions:
                print(d["title"])
        """
        validated_table = _validate_identifier(table, ALLOWED_TABLES, "table")
        validated_order = _validate_order_by(order_by)
        query = f"""
            SELECT * FROM {validated_table}
            ORDER BY {validated_order}
            LIMIT ? OFFSET ?
        """
        self.cursor.execute(query, (limit, offset))
        return [dict_from_row(row) for row in self.cursor.fetchall()]

    def list_with_filters(
        self,
        table: str,
        filters: dict[str, Any],
        limit: int = 100,
        offset: int = 0,
        order_by: str = "created_at DESC"
    ) -> list[dict[str, Any]]:
        """
        List records with WHERE clause filters.

        Args:
            table: Table name (must be in ALLOWED_TABLES whitelist)
            filters: Dictionary of column: value pairs for WHERE clause
            limit: Maximum number of records to return (default: 100)
            offset: Number of records to skip (default: 0)
            order_by: SQL ORDER BY clause (default: "created_at DESC")

        Returns:
            List of record dictionaries matching the filters

        Raises:
            ValueError: If table, column, or order_by is not in whitelist

        Example:
            # Get active decisions in the "auth" domain
            filters = {"status": "active", "domain": "auth"}
            decisions = repo.list_with_filters("decisions", filters, limit=20)
        """
        validated_table = _validate_identifier(table, ALLOWED_TABLES, "table")
        validated_order = _validate_order_by(order_by)
        query = f"SELECT * FROM {validated_table} WHERE 1=1"
        params: list[Any] = []

        for column, value in filters.items():
            if value is not None:
                validated_col = _validate_identifier(column, ALLOWED_COLUMNS, "column")
                query += f" AND {validated_col} = ?"
                params.append(value)

        query += f" ORDER BY {validated_order} LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        self.cursor.execute(query, params)
        return [dict_from_row(row) for row in self.cursor.fetchall()]

    def create(self, table: str, data: dict[str, Any]) -> int:
        """
        Create a new record.

        Args:
            table: Table name (must be in ALLOWED_TABLES whitelist)
            data: Dictionary of column: value pairs

        Returns:
            ID of the newly created record

        Raises:
            sqlite3.IntegrityError: If constraints are violated
            ValueError: If table or column names are not in whitelist

        Example:
            new_id = repo.create("decisions", {
                "title": "Use JWT",
                "context": "Need auth",
                "status": "active",
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            })
        """
        validated_table = _validate_identifier(table, ALLOWED_TABLES, "table")
        validated_columns = [
            _validate_identifier(col, ALLOWED_COLUMNS, "column")
            for col in data.keys()
        ]
        columns = ", ".join(validated_columns)
        placeholders = ", ".join(["?" for _ in data])
        query = f"INSERT INTO {validated_table} ({columns}) VALUES ({placeholders})"

        self.cursor.execute(query, list(data.values()))
        self.conn.commit()

        return self.cursor.lastrowid or 0

    def update(self, table: str, id: int, data: dict[str, Any]) -> bool:
        """
        Update an existing record.

        Args:
            table: Table name (must be in ALLOWED_TABLES whitelist)
            id: Record ID to update
            data: Dictionary of column: value pairs to update

        Returns:
            True if record was updated, False if not found

        Raises:
            ValueError: If table or column names are not in whitelist

        Example:
            success = repo.update("decisions", 123, {
                "status": "superseded",
                "updated_at": datetime.now().isoformat()
            })
        """
        if not data:
            return False

        validated_table = _validate_identifier(table, ALLOWED_TABLES, "table")
        validated_columns = [
            _validate_identifier(col, ALLOWED_COLUMNS, "column")
            for col in data.keys()
        ]
        set_clause = ", ".join([f"{col} = ?" for col in validated_columns])
        query = f"UPDATE {validated_table} SET {set_clause} WHERE id = ?"

        params = list(data.values())
        params.append(id)

        self.cursor.execute(query, params)
        self.conn.commit()

        return self.cursor.rowcount > 0

    def delete(self, table: str, id: int) -> bool:
        """
        Delete a record by ID.

        Args:
            table: Table name (must be in ALLOWED_TABLES whitelist)
            id: Record ID to delete

        Returns:
            True if record was deleted, False if not found

        Raises:
            ValueError: If table name is not in whitelist

        Example:
            success = repo.delete("decisions", 123)
            if success:
                print("Decision deleted")
        """
        validated_table = _validate_identifier(table, ALLOWED_TABLES, "table")
        self.cursor.execute(f"DELETE FROM {validated_table} WHERE id = ?", (id,))
        self.conn.commit()

        return self.cursor.rowcount > 0

    def exists(self, table: str, id: int) -> bool:
        """
        Check if a record exists.

        Args:
            table: Table name (must be in ALLOWED_TABLES whitelist)
            id: Record ID to check

        Returns:
            True if record exists, False otherwise

        Raises:
            ValueError: If table name is not in whitelist

        Example:
            if repo.exists("decisions", 123):
                print("Decision exists")
        """
        validated_table = _validate_identifier(table, ALLOWED_TABLES, "table")
        self.cursor.execute(f"SELECT 1 FROM {validated_table} WHERE id = ? LIMIT 1", (id,))
        return self.cursor.fetchone() is not None

    def count(self, table: str, filters: Optional[dict[str, Any]] = None) -> int:
        """
        Count records in a table, optionally with filters.

        Args:
            table: Table name (must be in ALLOWED_TABLES whitelist)
            filters: Optional dictionary of column: value pairs for WHERE clause

        Returns:
            Number of matching records

        Raises:
            ValueError: If table or column names are not in whitelist

        Example:
            # Count all decisions
            total = repo.count("decisions")

            # Count active decisions
            active_count = repo.count("decisions", {"status": "active"})
        """
        validated_table = _validate_identifier(table, ALLOWED_TABLES, "table")
        query = f"SELECT COUNT(*) FROM {validated_table} WHERE 1=1"
        params: list[Any] = []

        if filters:
            for column, value in filters.items():
                if value is not None:
                    validated_col = _validate_identifier(column, ALLOWED_COLUMNS, "column")
                    query += f" AND {validated_col} = ?"
                    params.append(value)

        self.cursor.execute(query, params)
        result = self.cursor.fetchone()
        return result[0] if result else 0
