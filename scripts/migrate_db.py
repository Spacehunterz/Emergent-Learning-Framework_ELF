#!/usr/bin/env python3
"""Database migration runner for ELF.

Reads sequential .sql files from scripts/migrations/ and applies them
to the database, tracking schema version in a dedicated table.

Usage:
    python scripts/migrate_db.py
    python scripts/migrate_db.py path/to/database.db
"""

import sqlite3
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
MIGRATIONS_DIR = SCRIPT_DIR / "migrations"
DEFAULT_DB = Path.home() / ".claude" / "emergent-learning" / "memory" / "index.db"


def get_db_version(conn):
    """Get current schema version from database."""
    try:
        cur = conn.execute("SELECT version FROM schema_version ORDER BY version DESC LIMIT 1")
        row = cur.fetchone()
        return row[0] if row else 0
    except sqlite3.OperationalError:
        return 0


def ensure_version_table(conn):
    """Create schema_version table if it doesn't exist."""
    # Check if table exists first
    cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='schema_version'")
    if cur.fetchone():
        return  # Table already exists, don't modify it

    conn.execute("""
        CREATE TABLE schema_version (
            version INTEGER PRIMARY KEY,
            applied_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            description TEXT
        )
    """)
    conn.commit()


def set_db_version(conn, version):
    """Record schema version in database."""
    conn.execute("INSERT OR REPLACE INTO schema_version (version, applied_at) VALUES (?, datetime('now'))", (version,))
    conn.commit()


def run_migrations(db_path):
    """Run all pending migrations on the database."""
    db_path = Path(db_path)

    if not db_path.exists():
        print(f"  Database not found: {db_path}")
        print("  Skipping migrations (database will be created on first use)")
        return 0

    conn = sqlite3.connect(str(db_path), timeout=5.0)
    ensure_version_table(conn)
    current_version = get_db_version(conn)

    if not MIGRATIONS_DIR.exists():
        MIGRATIONS_DIR.mkdir(parents=True, exist_ok=True)
        print(f"  Created migrations directory: {MIGRATIONS_DIR}")

    migrations = sorted(MIGRATIONS_DIR.glob("*.sql"))

    if not migrations:
        print(f"  No migrations found (current version: {current_version})")
        conn.close()
        return 0

    applied = 0
    for migration_file in migrations:
        try:
            version = int(migration_file.stem.split("_")[0])
        except (ValueError, IndexError):
            print(f"  Skipping {migration_file.name}: invalid filename format")
            continue

        if version > current_version:
            print(f"  Applying migration {migration_file.name}...")
            try:
                sql = migration_file.read_text()
                conn.executescript(sql)
                set_db_version(conn, version)
                applied += 1
                print(f"    OK")
            except sqlite3.Error as e:
                print(f"    FAILED: {e}")
                conn.close()
                raise

    if applied == 0:
        print(f"  Database up to date (version {current_version})")
    else:
        print(f"  Applied {applied} migration(s), now at version {get_db_version(conn)}")

    conn.close()
    return applied


def main():
    db_path = Path(sys.argv[1]).expanduser() if len(sys.argv) > 1 else DEFAULT_DB
    print(f"Running migrations on: {db_path}")
    run_migrations(db_path)


if __name__ == "__main__":
    main()
