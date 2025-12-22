"""
Base repository class for generic CRUD operations.

Provides reusable database operations to eliminate code duplication across endpoints.
"""

from typing import Any, Optional
from datetime import datetime
from contextlib import AbstractContextManager
import sqlite3

from .database import dict_from_row


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
            table: Table name
            id: Record ID

        Returns:
            Dictionary of record data, or None if not found

        Example:
            decision = repo.get_by_id("decisions", 123)
            if decision:
                print(decision["title"])
        """
        self.cursor.execute(f"SELECT * FROM {table} WHERE id = ?", (id,))
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
            table: Table name
            limit: Maximum number of records to return (default: 100)
            offset: Number of records to skip (default: 0)
            order_by: SQL ORDER BY clause (default: "created_at DESC")

        Returns:
            List of record dictionaries

        Example:
            decisions = repo.list_all("decisions", limit=50, offset=0)
            for d in decisions:
                print(d["title"])
        """
        query = f"""
            SELECT * FROM {table}
            ORDER BY {order_by}
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
            table: Table name
            filters: Dictionary of column: value pairs for WHERE clause
            limit: Maximum number of records to return (default: 100)
            offset: Number of records to skip (default: 0)
            order_by: SQL ORDER BY clause (default: "created_at DESC")

        Returns:
            List of record dictionaries matching the filters

        Example:
            # Get active decisions in the "auth" domain
            filters = {"status": "active", "domain": "auth"}
            decisions = repo.list_with_filters("decisions", filters, limit=20)
        """
        query = f"SELECT * FROM {table} WHERE 1=1"
        params = []

        for column, value in filters.items():
            if value is not None:  # Only add filter if value is not None
                query += f" AND {column} = ?"
                params.append(value)

        query += f" ORDER BY {order_by} LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        self.cursor.execute(query, params)
        return [dict_from_row(row) for row in self.cursor.fetchall()]

    def create(self, table: str, data: dict[str, Any]) -> int:
        """
        Create a new record.

        Args:
            table: Table name
            data: Dictionary of column: value pairs

        Returns:
            ID of the newly created record

        Raises:
            sqlite3.IntegrityError: If constraints are violated

        Example:
            new_id = repo.create("decisions", {
                "title": "Use JWT",
                "context": "Need auth",
                "status": "active",
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            })
        """
        columns = ", ".join(data.keys())
        placeholders = ", ".join(["?" for _ in data])
        query = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"

        self.cursor.execute(query, list(data.values()))
        self.conn.commit()

        return self.cursor.lastrowid

    def update(self, table: str, id: int, data: dict[str, Any]) -> bool:
        """
        Update an existing record.

        Args:
            table: Table name
            id: Record ID to update
            data: Dictionary of column: value pairs to update

        Returns:
            True if record was updated, False if not found

        Example:
            success = repo.update("decisions", 123, {
                "status": "superseded",
                "updated_at": datetime.now().isoformat()
            })
        """
        if not data:
            return False

        # Build SET clause
        set_clause = ", ".join([f"{col} = ?" for col in data.keys()])
        query = f"UPDATE {table} SET {set_clause} WHERE id = ?"

        params = list(data.values())
        params.append(id)

        self.cursor.execute(query, params)
        self.conn.commit()

        return self.cursor.rowcount > 0

    def delete(self, table: str, id: int) -> bool:
        """
        Delete a record by ID.

        Args:
            table: Table name
            id: Record ID to delete

        Returns:
            True if record was deleted, False if not found

        Example:
            success = repo.delete("decisions", 123)
            if success:
                print("Decision deleted")
        """
        self.cursor.execute(f"DELETE FROM {table} WHERE id = ?", (id,))
        self.conn.commit()

        return self.cursor.rowcount > 0

    def exists(self, table: str, id: int) -> bool:
        """
        Check if a record exists.

        Args:
            table: Table name
            id: Record ID to check

        Returns:
            True if record exists, False otherwise

        Example:
            if repo.exists("decisions", 123):
                print("Decision exists")
        """
        self.cursor.execute(f"SELECT 1 FROM {table} WHERE id = ? LIMIT 1", (id,))
        return self.cursor.fetchone() is not None

    def count(self, table: str, filters: Optional[dict[str, Any]] = None) -> int:
        """
        Count records in a table, optionally with filters.

        Args:
            table: Table name
            filters: Optional dictionary of column: value pairs for WHERE clause

        Returns:
            Number of matching records

        Example:
            # Count all decisions
            total = repo.count("decisions")

            # Count active decisions
            active_count = repo.count("decisions", {"status": "active"})
        """
        query = f"SELECT COUNT(*) FROM {table} WHERE 1=1"
        params = []

        if filters:
            for column, value in filters.items():
                if value is not None:
                    query += f" AND {column} = ?"
                    params.append(value)

        self.cursor.execute(query, params)
        return self.cursor.fetchone()[0]
