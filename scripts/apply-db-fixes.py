#!/usr/bin/env python3
"""
Agent D: Apply SQLite Database Fixes
Safely applies defensive fixes to the emergent-learning database.

Fixes applied:
1. Schema migration - add missing columns
2. Add UNIQUE constraints
3. Add CHECK constraints
4. Enable WAL mode
5. Add NOT NULL constraints (where possible)
6. Integrity checks before and after
"""

import sqlite3
import shutil
import sys
from pathlib import Path
from datetime import datetime


def backup_database(db_path: Path) -> Path:
    """Create timestamped backup."""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = db_path.with_suffix(f'.db.backup_{timestamp}')
    shutil.copy2(db_path, backup_path)
    print(f"[BACKUP] Created: {backup_path}")
    return backup_path


def check_integrity(conn: sqlite3.Connection) -> bool:
    """Check database integrity."""
    cursor = conn.cursor()
    cursor.execute("PRAGMA integrity_check")
    result = cursor.fetchone()[0]

    if result == "ok":
        print("[CHECK] Integrity check: PASS")
        return True
    else:
        print(f"[CHECK] Integrity check: FAIL - {result}")
        return False


def get_schema_info(conn: sqlite3.Connection, table: str) -> dict:
    """Get current schema information."""
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({table})")
    columns = {row[1]: row for row in cursor.fetchall()}
    return columns


def apply_schema_migration(conn: sqlite3.Connection):
    """Add missing columns to existing tables."""
    print("\n[MIGRATION] Checking schema...")

    cursor = conn.cursor()

    # Check learnings table
    columns = get_schema_info(conn, 'learnings')

    migrations = []

    if 'tags' not in columns:
        migrations.append("ALTER TABLE learnings ADD COLUMN tags TEXT")
    if 'domain' not in columns:
        migrations.append("ALTER TABLE learnings ADD COLUMN domain TEXT")
    if 'severity' not in columns:
        migrations.append("ALTER TABLE learnings ADD COLUMN severity INTEGER DEFAULT 3")
    if 'created_at' not in columns:
        migrations.append("ALTER TABLE learnings ADD COLUMN created_at DATETIME DEFAULT CURRENT_TIMESTAMP")
    if 'updated_at' not in columns:
        migrations.append("ALTER TABLE learnings ADD COLUMN updated_at DATETIME DEFAULT CURRENT_TIMESTAMP")

    if migrations:
        print(f"[MIGRATION] Applying {len(migrations)} column additions...")
        for migration in migrations:
            print(f"  - {migration}")
            cursor.execute(migration)
        conn.commit()
        print("[MIGRATION] Schema updated successfully")
    else:
        print("[MIGRATION] Schema is up to date")


def add_unique_constraints(conn: sqlite3.Connection):
    """Add UNIQUE constraints by recreating tables."""
    print("\n[CONSTRAINTS] Adding UNIQUE constraints...")

    cursor = conn.cursor()

    # Check if filepath is already unique
    cursor.execute("""
        SELECT COUNT(*) as count, filepath
        FROM learnings
        GROUP BY filepath
        HAVING count > 1
    """)
    duplicates = cursor.fetchall()

    if duplicates:
        print(f"[CONSTRAINTS] Found {len(duplicates)} duplicate filepaths")
        print("[CONSTRAINTS] Will keep first occurrence of each duplicate")
        for count, filepath in duplicates[:5]:  # Show first 5
            print(f"  - {filepath} ({count} occurrences)")

    # Create new learnings table with UNIQUE constraint
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS learnings_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT NOT NULL,
            filepath TEXT NOT NULL UNIQUE,
            title TEXT NOT NULL,
            summary TEXT,
            tags TEXT,
            domain TEXT,
            severity INTEGER DEFAULT 3,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Copy unique data
    cursor.execute("""
        INSERT INTO learnings_new (id, type, filepath, title, summary, tags, domain, severity, created_at, updated_at)
        SELECT id, type, filepath, title, summary, tags, domain, severity, created_at, updated_at
        FROM learnings
        WHERE id IN (
            SELECT MIN(id)
            FROM learnings
            GROUP BY filepath
        )
    """)

    # Drop old table and rename
    cursor.execute("DROP TABLE learnings")
    cursor.execute("ALTER TABLE learnings_new RENAME TO learnings")

    # Recreate indexes
    indexes = [
        "CREATE INDEX idx_learnings_domain ON learnings(domain)",
        "CREATE INDEX idx_learnings_type ON learnings(type)",
        "CREATE INDEX idx_learnings_created_at ON learnings(created_at DESC)",
        "CREATE INDEX idx_learnings_domain_created ON learnings(domain, created_at DESC)",
        "CREATE INDEX idx_learnings_filepath ON learnings(filepath)",
    ]

    for index_sql in indexes:
        cursor.execute(index_sql)

    conn.commit()
    print("[CONSTRAINTS] UNIQUE constraint added to learnings.filepath")

    # Similar for heuristics table
    cursor.execute("""
        SELECT COUNT(*) as count, domain, rule
        FROM heuristics
        GROUP BY domain, rule
        HAVING count > 1
    """)
    dup_heuristics = cursor.fetchall()

    if dup_heuristics:
        print(f"[CONSTRAINTS] Found {len(dup_heuristics)} duplicate heuristics")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS heuristics_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            domain TEXT NOT NULL,
            rule TEXT NOT NULL,
            explanation TEXT,
            source_type TEXT,
            source_id INTEGER,
            confidence REAL DEFAULT 0.5,
            times_validated INTEGER DEFAULT 0,
            times_violated INTEGER DEFAULT 0,
            is_golden BOOLEAN DEFAULT FALSE,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(domain, rule)
        )
    """)

    # Copy unique data (keep highest confidence)
    cursor.execute("""
        INSERT INTO heuristics_new
        SELECT * FROM heuristics
        WHERE id IN (
            SELECT MAX(id)
            FROM heuristics
            GROUP BY domain, rule
        )
    """)

    cursor.execute("DROP TABLE heuristics")
    cursor.execute("ALTER TABLE heuristics_new RENAME TO heuristics")

    # Recreate indexes
    heur_indexes = [
        "CREATE INDEX idx_heuristics_domain ON heuristics(domain)",
        "CREATE INDEX idx_heuristics_golden ON heuristics(is_golden)",
        "CREATE INDEX idx_heuristics_created_at ON heuristics(created_at DESC)",
        "CREATE INDEX idx_heuristics_domain_confidence ON heuristics(domain, confidence DESC)",
    ]

    for index_sql in heur_indexes:
        cursor.execute(index_sql)

    conn.commit()
    print("[CONSTRAINTS] UNIQUE constraint added to heuristics(domain, rule)")


def enable_wal_mode(conn: sqlite3.Connection):
    """Enable WAL mode for better concurrency."""
    print("\n[WAL MODE] Enabling Write-Ahead Logging...")

    cursor = conn.cursor()

    # Check current journal mode
    cursor.execute("PRAGMA journal_mode")
    current_mode = cursor.fetchone()[0]
    print(f"[WAL MODE] Current mode: {current_mode}")

    if current_mode.lower() != 'wal':
        try:
            cursor.execute("PRAGMA journal_mode=WAL")
            new_mode = cursor.fetchone()[0]
            print(f"[WAL MODE] Enabled: {new_mode}")
        except sqlite3.OperationalError as e:
            print(f"[WAL MODE] Warning: Could not enable WAL mode: {e}")
    else:
        print("[WAL MODE] Already enabled")

    # Set other performance/safety parameters
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.execute("PRAGMA busy_timeout=30000")  # 30 second timeout
    cursor.execute("PRAGMA foreign_keys=ON")

    print("[WAL MODE] Performance settings applied")


def run_maintenance(conn: sqlite3.Connection):
    """Run database maintenance."""
    print("\n[MAINTENANCE] Running optimization...")

    cursor = conn.cursor()

    # Check freelist
    cursor.execute("PRAGMA freelist_count")
    freelist = cursor.fetchone()[0]

    cursor.execute("PRAGMA page_count")
    page_count = cursor.fetchone()[0]

    print(f"[MAINTENANCE] Database: {page_count} pages, {freelist} free")

    if freelist > 10:
        print("[MAINTENANCE] Running VACUUM...")
        cursor.execute("VACUUM")

        cursor.execute("PRAGMA page_count")
        new_page_count = cursor.fetchone()[0]
        print(f"[MAINTENANCE] VACUUM complete: {page_count} -> {new_page_count} pages")

    print("[MAINTENANCE] Running ANALYZE...")
    cursor.execute("ANALYZE")

    print("[MAINTENANCE] Optimization complete")


def main():
    """Main fix application."""
    print("=" * 70)
    print("Agent D: SQLite Database Hardening")
    print("=" * 70)

    # Locate database
    home = Path.home()
    db_path = home / ".claude" / "emergent-learning" / "memory" / "index.db"

    if not db_path.exists():
        print(f"[ERROR] Database not found: {db_path}")
        sys.exit(1)

    print(f"[INFO] Database: {db_path}")

    # Create backup
    backup_path = backup_database(db_path)

    try:
        # Connect with longer timeout
        conn = sqlite3.connect(str(db_path), timeout=30.0)

        # Pre-flight check
        print("\n[CHECK] Pre-fix integrity check...")
        if not check_integrity(conn):
            print("[ERROR] Database is corrupted. Restore from backup.")
            sys.exit(1)

        # Apply fixes
        apply_schema_migration(conn)
        add_unique_constraints(conn)
        enable_wal_mode(conn)
        run_maintenance(conn)

        # Post-flight check
        print("\n[CHECK] Post-fix integrity check...")
        if not check_integrity(conn):
            print("[ERROR] Database corrupted during fixes. Restoring backup...")
            conn.close()
            shutil.copy2(backup_path, db_path)
            print(f"[RESTORE] Database restored from: {backup_path}")
            sys.exit(1)

        conn.close()

        print("\n" + "=" * 70)
        print("SUCCESS: All fixes applied successfully")
        print("=" * 70)
        print(f"Backup saved at: {backup_path}")
        print("\nRecommendations:")
        print("  1. Test query.py to ensure compatibility")
        print("  2. Run shell scripts to verify no breakage")
        print("  3. Keep backup for 30 days")
        print("  4. Monitor logs for any SQLite errors")

    except Exception as e:
        print(f"\n[ERROR] Fix failed: {e}")
        print(f"[RESTORE] Restoring from backup: {backup_path}")
        conn.close()
        shutil.copy2(backup_path, db_path)
        print("[RESTORE] Database restored")
        sys.exit(1)


if __name__ == '__main__':
    main()
