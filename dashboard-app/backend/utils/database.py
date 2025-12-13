"""
Database utility functions for the Emergent Learning Dashboard.

Provides database connection management and helper functions for SQLite operations.
"""

import sqlite3
from contextlib import contextmanager
from pathlib import Path


# Database path
EMERGENT_LEARNING_PATH = Path.home() / ".claude" / "emergent-learning"
DB_PATH = EMERGENT_LEARNING_PATH / "memory" / "index.db"


def escape_like(s: str) -> str:
    """
    Escape SQL LIKE wildcards to prevent wildcard injection.

    Args:
        s: String to escape

    Returns:
        String with SQL LIKE wildcards escaped
    """
    return s.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')


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
