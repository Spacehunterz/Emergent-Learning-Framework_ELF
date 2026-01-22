#!/usr/bin/env python3
"""
Database repair script for the Emergent Learning Framework.

This script repairs corrupted or incomplete database schemas by:
1. Creating missing tables (schema_version, patterns, etc.)
2. Adding missing columns to existing tables
3. Running pending migrations

Usage:
    python repair_database.py              # Repair default database
    python repair_database.py --check      # Check only (no changes)
    python repair_database.py --path /path/to/index.db  # Custom path
"""

import sqlite3
import argparse
import sys
from pathlib import Path
from datetime import datetime


def get_default_db_path() -> Path:
    """Get the default database path."""
    return Path.home() / ".claude" / "emergent-learning" / "memory" / "index.db"


def get_existing_columns(conn: sqlite3.Connection, table: str) -> set:
    """Get the set of existing column names for a table."""
    cursor = conn.execute(f"PRAGMA table_info({table})")
    return {row[1] for row in cursor.fetchall()}


def get_existing_tables(conn: sqlite3.Connection) -> set:
    """Get the set of existing table names."""
    cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    return {row[0] for row in cursor.fetchall()}


def add_column_if_missing(conn: sqlite3.Connection, table: str, column: str,
                          col_type: str, existing_columns: set) -> bool:
    """Add a column to a table if it doesn't exist. Returns True if added."""
    if column.lower() in {c.lower() for c in existing_columns}:
        return False
    try:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")
        print(f"  Added column: {table}.{column}")
        return True
    except sqlite3.OperationalError as e:
        if "duplicate column" not in str(e).lower():
            print(f"  Warning: Could not add {table}.{column}: {e}")
        return False


def repair_database(db_path: Path, check_only: bool = False) -> dict:
    """
    Repair the database schema.

    Returns:
        Dict with repair results: {'tables_created': [...], 'columns_added': [...], 'errors': [...]}
    """
    results = {
        'tables_created': [],
        'columns_added': [],
        'errors': [],
        'already_ok': []
    }

    if not db_path.exists():
        results['errors'].append(f"Database not found: {db_path}")
        return results

    print(f"{'Checking' if check_only else 'Repairing'} database: {db_path}")
    print()

    conn = sqlite3.connect(str(db_path), timeout=30.0)
    conn.row_factory = sqlite3.Row

    try:
        existing_tables = get_existing_tables(conn)

        # ==============================================================
        # 1. Create schema_version table (required for migrations)
        # ==============================================================
        if 'schema_version' not in existing_tables:
            if check_only:
                print("  Missing table: schema_version")
                results['tables_created'].append('schema_version (needed)')
            else:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS schema_version (
                        version INTEGER PRIMARY KEY,
                        applied_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        description TEXT
                    )
                """)
                print("  Created table: schema_version")
                results['tables_created'].append('schema_version')
        else:
            results['already_ok'].append('schema_version table exists')

        # ==============================================================
        # 2. Create patterns table (required for pattern accumulation)
        # ==============================================================
        if 'patterns' not in existing_tables:
            if check_only:
                print("  Missing table: patterns")
                results['tables_created'].append('patterns (needed)')
            else:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS patterns (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        pattern_type TEXT NOT NULL,
                        pattern_hash TEXT NOT NULL UNIQUE,
                        pattern_text TEXT NOT NULL,
                        signature TEXT,
                        occurrence_count INTEGER DEFAULT 1,
                        first_seen DATETIME DEFAULT CURRENT_TIMESTAMP,
                        last_seen DATETIME DEFAULT CURRENT_TIMESTAMP,
                        session_ids TEXT DEFAULT '[]',
                        project_path TEXT DEFAULT NULL,
                        domain TEXT DEFAULT 'general',
                        strength REAL DEFAULT 0.5,
                        promoted_to_heuristic_id INTEGER,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME
                    )
                """)
                conn.execute("CREATE INDEX IF NOT EXISTS idx_patterns_type ON patterns(pattern_type)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_patterns_hash ON patterns(pattern_hash)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_patterns_strength ON patterns(strength)")
                print("  Created table: patterns")
                results['tables_created'].append('patterns')
        else:
            results['already_ok'].append('patterns table exists')

        # ==============================================================
        # 3. Repair spike_reports table
        # ==============================================================
        if 'spike_reports' in existing_tables:
            print("\nChecking spike_reports table...")
            sr_cols = get_existing_columns(conn, 'spike_reports')

            spike_columns = [
                ('topic', 'TEXT DEFAULT ""'),
                ('question', 'TEXT DEFAULT ""'),
                ('findings', 'TEXT DEFAULT ""'),
                ('gotchas', 'TEXT'),
                ('resources', 'TEXT'),
                ('domain', 'TEXT'),
                ('tags', 'TEXT'),
                ('access_count', 'INTEGER DEFAULT 0'),
                ('updated_at', 'DATETIME'),
            ]

            for col_name, col_type in spike_columns:
                if col_name.lower() not in {c.lower() for c in sr_cols}:
                    if check_only:
                        print(f"  Missing column: spike_reports.{col_name}")
                        results['columns_added'].append(f'spike_reports.{col_name} (needed)')
                    else:
                        if add_column_if_missing(conn, 'spike_reports', col_name, col_type, sr_cols):
                            results['columns_added'].append(f'spike_reports.{col_name}')
                else:
                    results['already_ok'].append(f'spike_reports.{col_name} exists')

        # ==============================================================
        # 4. Repair session_summaries table
        # ==============================================================
        if 'session_summaries' in existing_tables:
            print("\nChecking session_summaries table...")
            ss_cols = get_existing_columns(conn, 'session_summaries')

            session_columns = [
                ('project', 'TEXT DEFAULT ""'),
                ('session_file_path', 'TEXT'),
                ('session_file_size', 'INTEGER'),
                ('session_last_modified', 'DATETIME'),
                ('summary_version', 'INTEGER DEFAULT 1'),
                ('needs_resummarize', 'INTEGER DEFAULT 0'),
            ]

            for col_name, col_type in session_columns:
                if col_name.lower() not in {c.lower() for c in ss_cols}:
                    if check_only:
                        print(f"  Missing column: session_summaries.{col_name}")
                        results['columns_added'].append(f'session_summaries.{col_name} (needed)')
                    else:
                        if add_column_if_missing(conn, 'session_summaries', col_name, col_type, ss_cols):
                            results['columns_added'].append(f'session_summaries.{col_name}')
                else:
                    results['already_ok'].append(f'session_summaries.{col_name} exists')

        # ==============================================================
        # 5. Repair heuristics table
        # ==============================================================
        if 'heuristics' in existing_tables:
            print("\nChecking heuristics table...")
            h_cols = get_existing_columns(conn, 'heuristics')

            heuristic_columns = [
                ('status', 'TEXT DEFAULT "active"'),
                ('dormant_since', 'DATETIME'),
                ('revival_conditions', 'TEXT'),
                ('times_revived', 'INTEGER DEFAULT 0'),
                ('times_contradicted', 'INTEGER DEFAULT 0'),
                ('min_applications', 'INTEGER DEFAULT 10'),
                ('last_confidence_update', 'DATETIME'),
                ('update_count_today', 'INTEGER DEFAULT 0'),
                ('update_count_reset_date', 'DATE'),
                ('last_used_at', 'DATETIME'),
                ('confidence_ema', 'REAL'),
                ('ema_alpha', 'REAL'),
                ('ema_warmup_remaining', 'INTEGER DEFAULT 0'),
                ('last_ema_update', 'DATETIME'),
                ('fraud_flags', 'INTEGER DEFAULT 0'),
                ('is_quarantined', 'INTEGER DEFAULT 0'),
                ('last_fraud_check', 'DATETIME'),
                ('project_path', 'TEXT DEFAULT NULL'),
            ]

            for col_name, col_type in heuristic_columns:
                if col_name.lower() not in {c.lower() for c in h_cols}:
                    if check_only:
                        print(f"  Missing column: heuristics.{col_name}")
                        results['columns_added'].append(f'heuristics.{col_name} (needed)')
                    else:
                        if add_column_if_missing(conn, 'heuristics', col_name, col_type, h_cols):
                            results['columns_added'].append(f'heuristics.{col_name}')
                else:
                    results['already_ok'].append(f'heuristics.{col_name} exists')

        # ==============================================================
        # 6. Repair building_queries table
        # ==============================================================
        if 'building_queries' in existing_tables:
            print("\nChecking building_queries table...")
            bq_cols = get_existing_columns(conn, 'building_queries')

            bq_columns = [
                ('query_type', 'TEXT DEFAULT ""'),
                ('session_id', 'TEXT'),
                ('agent_id', 'TEXT'),
                ('domain', 'TEXT'),
                ('tags', 'TEXT'),
                ('limit_requested', 'INTEGER'),
                ('max_tokens_requested', 'INTEGER'),
                ('results_returned', 'INTEGER DEFAULT 0'),
                ('tokens_approximated', 'INTEGER'),
                ('status', 'TEXT DEFAULT "success"'),
                ('error_message', 'TEXT'),
                ('error_code', 'TEXT'),
                ('golden_rules_returned', 'INTEGER DEFAULT 0'),
                ('heuristics_count', 'INTEGER DEFAULT 0'),
                ('learnings_count', 'INTEGER DEFAULT 0'),
                ('experiments_count', 'INTEGER DEFAULT 0'),
                ('ceo_reviews_count', 'INTEGER DEFAULT 0'),
                ('query_summary', 'TEXT'),
                ('completed_at', 'DATETIME'),
            ]

            for col_name, col_type in bq_columns:
                if col_name.lower() not in {c.lower() for c in bq_cols}:
                    if check_only:
                        print(f"  Missing column: building_queries.{col_name}")
                        results['columns_added'].append(f'building_queries.{col_name} (needed)')
                    else:
                        if add_column_if_missing(conn, 'building_queries', col_name, col_type, bq_cols):
                            results['columns_added'].append(f'building_queries.{col_name}')

        # ==============================================================
        # 7. Create missing indexes
        # ==============================================================
        if not check_only:
            print("\nCreating missing indexes...")
            indexes = [
                ("idx_heuristics_status", "heuristics", "status"),
                ("idx_heuristics_last_used", "heuristics", "last_used_at DESC"),
                ("idx_heuristics_project_path", "heuristics", "project_path"),
                ("idx_spike_reports_domain", "spike_reports", "domain"),
                ("idx_spike_reports_topic", "spike_reports", "topic"),
                ("idx_spike_reports_tags", "spike_reports", "tags"),
                ("idx_spike_reports_created_at", "spike_reports", "created_at DESC"),
                ("idx_session_summaries_project", "session_summaries", "project"),
            ]

            for idx_name, table, columns in indexes:
                if table in existing_tables:
                    try:
                        conn.execute(f"CREATE INDEX IF NOT EXISTS {idx_name} ON {table}({columns})")
                    except sqlite3.OperationalError:
                        pass  # Index might exist or table structure differs

        # ==============================================================
        # 8. Mark schema as repaired (add to schema_version)
        # ==============================================================
        if not check_only and results['tables_created'] or results['columns_added']:
            try:
                # Get max version and add a new entry
                cursor = conn.execute("SELECT MAX(version) FROM schema_version")
                row = cursor.fetchone()
                max_version = row[0] if row and row[0] else 0

                conn.execute(
                    "INSERT OR IGNORE INTO schema_version (version, description) VALUES (?, ?)",
                    (max_version + 1, f"repair_database.py run at {datetime.now().isoformat()}")
                )
            except sqlite3.OperationalError:
                pass  # Table might not exist yet

        if not check_only:
            conn.commit()
            print("\nCommitted changes.")

    except Exception as e:
        results['errors'].append(str(e))
        print(f"\nError: {e}")
        if not check_only:
            conn.rollback()
    finally:
        conn.close()

    return results


def print_summary(results: dict):
    """Print a summary of the repair results."""
    print("\n" + "=" * 60)
    print("REPAIR SUMMARY")
    print("=" * 60)

    if results['tables_created']:
        print(f"\nTables created ({len(results['tables_created'])}):")
        for t in results['tables_created']:
            print(f"  + {t}")

    if results['columns_added']:
        print(f"\nColumns added ({len(results['columns_added'])}):")
        for c in results['columns_added']:
            print(f"  + {c}")

    if results['errors']:
        print(f"\nErrors ({len(results['errors'])}):")
        for e in results['errors']:
            print(f"  ! {e}")

    if not results['tables_created'] and not results['columns_added'] and not results['errors']:
        print("\nDatabase schema is already up to date.")

    print()


def main():
    parser = argparse.ArgumentParser(description="Repair ELF database schema")
    parser.add_argument("--check", action="store_true", help="Check only, don't make changes")
    parser.add_argument("--path", type=Path, help="Custom database path")
    args = parser.parse_args()

    db_path = args.path if args.path else get_default_db_path()

    results = repair_database(db_path, check_only=args.check)
    print_summary(results)

    # Exit with error code if there were errors
    if results['errors']:
        sys.exit(1)

    # Exit with code 2 if repairs were needed (for CI/testing)
    if results['tables_created'] or results['columns_added']:
        sys.exit(0 if not args.check else 2)

    sys.exit(0)


if __name__ == "__main__":
    main()
