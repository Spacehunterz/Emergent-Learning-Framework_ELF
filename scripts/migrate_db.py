#!/usr/bin/env python3
"""Database migration runner for ELF.

Reads sequential .sql files from scripts/migrations/ and applies them
to the database, tracking schema version in a dedicated table.

Usage:
    python scripts/migrate_db.py <database_path>
    python scripts/migrate_db.py ~/.claude/emergent-learning/memory/index.db
"""

import sqlite3
import sys
from pathlib import Path

MIGRATIONS_DIR = Path(__file__).parent / "migrations"


def get_db_version(conn):
    """Get current schema version from database.

    Returns 0 if schema_version table doesn't exist (fresh database).
    """
    try:
        cur = conn.execute("SELECT version FROM schema_version ORDER BY version DESC LIMIT 1")
        row = cur.fetchone()
        return row[0] if row else 0
    except sqlite3.OperationalError:
        # Table doesn't exist yet
        return 0


def set_db_version(conn, version):
    """Update schema version in database."""
    conn.execute("""
        INSERT OR REPLACE INTO schema_version (id, version, applied_at)
        VALUES (1, ?, datetime('now'))
    """, (version,))
    conn.commit()


def run_migrations(db_path):
    """Run all pending migrations on the database.

    Args:
        db_path: Path to SQLite database file

    Returns:
        Number of migrations applied
    """
    if not Path(db_path).exists():
        print(f"  Database not found: {db_path}")
        print("  Skipping migrations (database will be created on first use)")
        return 0

    conn = sqlite3.connect(db_path)
    current_version = get_db_version(conn)

    if not MIGRATIONS_DIR.exists():
        print(f"  No migrations directory found at {MIGRATIONS_DIR}")
        conn.close()
        return 0

    # Get all migration files, sorted by version number
    migrations = sorted(MIGRATIONS_DIR.glob("*.sql"))

    if not migrations:
        print("  No migration files found")
        conn.close()
        return 0

    applied = 0
    for migration_file in migrations:
        # Extract version number from filename (e.g., 001_add_version_tracking.sql -> 1)
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
                print(f"    ✓ Migration {version} applied successfully")
            except sqlite3.Error as e:
                print(f"    ✗ Migration {version} failed: {e}")
                conn.close()
                raise

    final_version = get_db_version(conn)
    conn.close()

    if applied == 0:
        print(f"  Database already at latest version ({final_version})")
    else:
        print(f"  Database migrated to version {final_version} ({applied} migration(s) applied)")

    return applied


def main():
    if len(sys.argv) != 2:
        print("Usage: python migrate_db.py <database_path>")
        print("Example: python migrate_db.py ~/.claude/emergent-learning/memory/index.db")
        sys.exit(1)

    db_path = Path(sys.argv[1]).expanduser()
    run_migrations(str(db_path))


if __name__ == "__main__":
    main()
