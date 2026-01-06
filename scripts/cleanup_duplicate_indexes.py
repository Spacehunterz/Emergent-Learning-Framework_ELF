#!/usr/bin/env python3
"""
Database Index Cleanup Script

Removes duplicate indexes where both `idx_table_column` and `table_column` patterns
exist for the same table/column combination.

Run with --dry-run first to see what would be removed.
"""

import sqlite3
import re
import sys
from pathlib import Path


def get_db_path() -> Path:
    """Find the database path."""
    # Check ELF_BASE_PATH env
    import os
    base = os.environ.get("ELF_BASE_PATH", Path.home() / ".claude" / "emergent-learning")
    return Path(base) / "memory" / "index.db"


def extract_columns_from_sql(sql: str) -> tuple:
    """Extract column names from CREATE INDEX SQL, preserving order."""
    # Match: CREATE INDEX name ON table(column1, column2, ...)
    # Handle both quoted "column" and unquoted column formats
    match = re.search(r'\(([^)]+)\)', sql)
    if match:
        cols_str = match.group(1)
        # Parse columns, handling quotes and DESC/ASC suffixes
        cols = []
        for part in cols_str.split(','):
            # Remove quotes, whitespace, and ASC/DESC
            col = part.strip()
            col = re.sub(r'^["\'`]', '', col)  # Remove leading quote
            col = re.sub(r'["\'`]$', '', col)  # Remove trailing quote
            col = re.sub(r'\s+(ASC|DESC).*$', '', col, flags=re.IGNORECASE)
            col = col.strip().strip('"\'`').lower()
            if col:
                cols.append(col)
        return tuple(cols)
    return tuple()


def find_duplicates(conn: sqlite3.Connection) -> list:
    """Find duplicate indexes by table and columns."""
    cursor = conn.execute('''
        SELECT name, tbl_name, sql
        FROM sqlite_master
        WHERE type='index' AND sql IS NOT NULL
        ORDER BY tbl_name, name
    ''')

    # Group indexes by table and columns (order-sensitive for composite indexes)
    table_indexes = {}  # {(table, tuple(columns)): [(name, sql), ...]}

    for name, table, sql in cursor.fetchall():
        columns = extract_columns_from_sql(sql)
        if not columns:
            continue
        key = (table, columns)  # tuple preserves order
        if key not in table_indexes:
            table_indexes[key] = []
        table_indexes[key].append((name, sql))

    # Find duplicates
    duplicates = []
    for (table, cols), indexes in table_indexes.items():
        if len(indexes) > 1:
            # Keep the idx_ prefixed one (from schema), remove ORM-generated ones
            idx_versions = [i for i in indexes if i[0].startswith('idx_')]
            orm_versions = [i for i in indexes if not i[0].startswith('idx_')]

            if idx_versions and orm_versions:
                # Remove the ORM versions (keep idx_ ones)
                for name, sql in orm_versions:
                    duplicates.append((table, name, list(cols)))
            elif len(orm_versions) > 1:
                # Multiple ORM versions, keep first
                for name, sql in orm_versions[1:]:
                    duplicates.append((table, name, list(cols)))

    return duplicates


def cleanup_indexes(conn: sqlite3.Connection, dry_run: bool = True) -> int:
    """Remove duplicate indexes."""
    duplicates = find_duplicates(conn)

    if not duplicates:
        print("No duplicate indexes found.")
        return 0

    print(f"Found {len(duplicates)} duplicate indexes to remove:\n")

    removed = 0
    for table, name, cols in duplicates:
        cols_str = ", ".join(sorted(cols))
        print(f"  {table}.{name} ({cols_str})")

        if not dry_run:
            try:
                conn.execute(f'DROP INDEX IF EXISTS "{name}"')
                removed += 1
            except Exception as e:
                print(f"    ERROR: {e}")

    if not dry_run:
        conn.commit()
        print(f"\nRemoved {removed} duplicate indexes.")
    else:
        print(f"\nDry run - would remove {len(duplicates)} indexes.")
        print("Run with --execute to actually remove them.")

    return len(duplicates)


def main():
    dry_run = "--execute" not in sys.argv

    db_path = get_db_path()
    if not db_path.exists():
        print(f"Database not found: {db_path}")
        sys.exit(1)

    print(f"Database: {db_path}")
    print(f"Mode: {'DRY RUN' if dry_run else 'EXECUTE'}\n")

    conn = sqlite3.connect(db_path)
    try:
        count = cleanup_indexes(conn, dry_run=dry_run)

        if not dry_run and count > 0:
            # Run VACUUM to reclaim space
            print("\nRunning VACUUM to reclaim space...")
            conn.execute("VACUUM")
            print("Done.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
