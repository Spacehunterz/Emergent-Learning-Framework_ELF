#!/usr/bin/env python3
"""
Migration: Add project_path column to heuristics table.

This migration adds location awareness to heuristics:
- NULL = global heuristic (available everywhere)
- path = location-specific heuristic (only shown when in that directory)

Run: python ~/.claude/emergent-learning/scripts/migrate_add_project_path.py
"""

import sqlite3
import sys
from pathlib import Path
from datetime import datetime

# Resolve paths
SCRIPT_DIR = Path(__file__).resolve().parent
BASE_DIR = SCRIPT_DIR.parent
MEMORY_DIR = BASE_DIR / "memory"
DB_PATH = MEMORY_DIR / "index.db"
MIGRATIONS_LOG = MEMORY_DIR / "migrations.log"


def log(message: str) -> None:
    """Log migration progress."""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{timestamp}] {message}")

    # Also log to file
    try:
        with open(MIGRATIONS_LOG, 'a', encoding='utf-8') as f:
            f.write(f"[{timestamp}] {message}\n")
    except Exception:
        pass


def check_column_exists(conn: sqlite3.Connection, table: str, column: str) -> bool:
    """Check if a column exists in a table."""
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({table})")
    columns = [row[1] for row in cursor.fetchall()]
    return column in columns


def migrate():
    """Run the migration."""
    log("Starting migration: add project_path column to heuristics")

    if not DB_PATH.exists():
        log(f"ERROR: Database not found at {DB_PATH}")
        sys.exit(1)

    conn = sqlite3.connect(str(DB_PATH))

    try:
        # Check if column already exists
        if check_column_exists(conn, 'heuristics', 'project_path'):
            log("Column 'project_path' already exists in heuristics table. Skipping migration.")
            return

        cursor = conn.cursor()

        # Add the column
        log("Adding project_path column to heuristics table...")
        cursor.execute("""
            ALTER TABLE heuristics
            ADD COLUMN project_path TEXT DEFAULT NULL
        """)

        # Create index for efficient filtering
        log("Creating index on project_path...")
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_heuristics_project_path
            ON heuristics(project_path)
        """)

        # Also create a composite index for common queries
        log("Creating composite index on (project_path, domain)...")
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_heuristics_project_path_domain
            ON heuristics(project_path, domain)
        """)

        conn.commit()
        log("Migration completed successfully!")

        # Show stats
        cursor.execute("SELECT COUNT(*) FROM heuristics")
        total = cursor.fetchone()[0]
        log(f"Total heuristics in database: {total} (all now global with project_path=NULL)")

    except Exception as e:
        log(f"ERROR: Migration failed: {e}")
        conn.rollback()
        sys.exit(1)
    finally:
        conn.close()


if __name__ == '__main__':
    migrate()
