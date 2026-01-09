#!/usr/bin/env python3
"""
Database Consolidation Script for ELF

Finds orphaned database files from legacy installations and merges
unique heuristics into the canonical memory/index.db location.

Usage:
    python consolidate-databases.py              # Dry-run (report only)
    python consolidate-databases.py --merge      # Actually merge heuristics
    python consolidate-databases.py --cleanup    # Merge + remove orphan files
"""

import argparse
import hashlib
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.resolve()
BASE_DIR = SCRIPT_DIR.parent
CANONICAL_DB = BASE_DIR / "memory" / "index.db"

LEGACY_LOCATIONS = [
    BASE_DIR / "index.db",
    BASE_DIR / "learning.db",
    BASE_DIR / "learnings.db",
    BASE_DIR / "memory" / "learnings.db",
    BASE_DIR / "memory" / "learning.db",
    BASE_DIR / "memory" / "heuristics" / "index.db",
]


def get_heuristics_from_db(db_path):
    """Extract heuristics from a database file."""
    if not db_path.exists():
        return []

    try:
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='heuristics'")
        if not cursor.fetchone():
            conn.close()
            return []

        cursor.execute("SELECT * FROM heuristics")
        rows = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return rows
    except sqlite3.Error as e:
        print(f"  Error reading {db_path}: {e}")
        return []


def heuristic_hash(h):
    """Create a hash to identify duplicate heuristics by content."""
    content = f"{h.get('domain', '')}|{h.get('rule', '')}".lower().strip()
    return hashlib.md5(content.encode()).hexdigest()


def merge_heuristic(canonical_conn, heuristic):
    """Insert a heuristic into the canonical database."""
    cursor = canonical_conn.cursor()

    cursor.execute("""
        INSERT INTO heuristics (
            domain, rule, explanation, source_type, confidence,
            times_validated, times_violated, is_golden, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        heuristic.get('domain', 'unknown'),
        heuristic.get('rule', ''),
        heuristic.get('explanation', ''),
        heuristic.get('source_type', 'observation'),
        heuristic.get('confidence', 0.5),
        heuristic.get('times_validated', 0),
        heuristic.get('times_violated', 0),
        heuristic.get('is_golden', 0),
        heuristic.get('created_at', datetime.now().isoformat()),
        datetime.now().isoformat()
    ))
    return cursor.lastrowid


def find_all_databases():
    """Find all .db files in the ELF directory tree."""
    all_dbs = set()

    for legacy in LEGACY_LOCATIONS:
        if legacy.exists() and legacy != CANONICAL_DB:
            all_dbs.add(legacy)

    for db_file in BASE_DIR.rglob("*.db"):
        if db_file != CANONICAL_DB and db_file not in all_dbs:
            if "node_modules" not in str(db_file) and ".git" not in str(db_file):
                all_dbs.add(db_file)

    return sorted(all_dbs)


def main():
    parser = argparse.ArgumentParser(description="Consolidate ELF database files")
    parser.add_argument("--merge", action="store_true", help="Actually merge heuristics into canonical DB")
    parser.add_argument("--cleanup", action="store_true", help="Merge and remove orphan database files")
    args = parser.parse_args()

    print("=" * 60)
    print("ELF Database Consolidation Tool")
    print("=" * 60)
    print(f"\nCanonical database: {CANONICAL_DB}")

    if not CANONICAL_DB.exists():
        print(f"\nERROR: Canonical database not found at {CANONICAL_DB}")
        print("Please ensure ELF is properly installed.")
        sys.exit(1)

    canonical_heuristics = get_heuristics_from_db(CANONICAL_DB)
    canonical_hashes = {heuristic_hash(h) for h in canonical_heuristics}
    print(f"Canonical DB contains: {len(canonical_heuristics)} heuristics")

    print("\nScanning for orphaned databases...")
    orphan_dbs = find_all_databases()

    if not orphan_dbs:
        print("\nNo orphaned databases found. Your installation is clean!")
        sys.exit(0)

    print(f"\nFound {len(orphan_dbs)} potential orphan database(s):\n")

    total_orphan_heuristics = 0
    total_unique_heuristics = 0
    merge_candidates = []

    for db_path in orphan_dbs:
        rel_path = db_path.relative_to(BASE_DIR) if db_path.is_relative_to(BASE_DIR) else db_path
        heuristics = get_heuristics_from_db(db_path)

        if not heuristics:
            size = db_path.stat().st_size if db_path.exists() else 0
            print(f"  {rel_path}")
            print(f"    -> Empty or no heuristics table ({size} bytes)")
            if args.cleanup and size == 0:
                print(f"    -> Would delete (empty file)")
            continue

        unique = []
        duplicates = 0
        for h in heuristics:
            h_hash = heuristic_hash(h)
            if h_hash not in canonical_hashes:
                unique.append(h)
                canonical_hashes.add(h_hash)
            else:
                duplicates += 1

        total_orphan_heuristics += len(heuristics)
        total_unique_heuristics += len(unique)

        print(f"  {rel_path}")
        print(f"    -> {len(heuristics)} heuristics ({len(unique)} unique, {duplicates} duplicates)")

        if unique:
            merge_candidates.append((db_path, unique))
            for h in unique[:3]:
                print(f"       - [{h.get('domain')}] {h.get('rule', '')[:50]}...")
            if len(unique) > 3:
                print(f"       ... and {len(unique) - 3} more")

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Canonical heuristics:     {len(canonical_heuristics)}")
    print(f"Orphan databases found:   {len(orphan_dbs)}")
    print(f"Total orphan heuristics:  {total_orphan_heuristics}")
    print(f"Unique (not in canonical):{total_unique_heuristics}")

    if not merge_candidates:
        print("\nNo unique heuristics to merge.")
        if args.cleanup:
            print("Would clean up empty database files.")
        sys.exit(0)

    if not args.merge and not args.cleanup:
        print(f"\nDRY RUN - No changes made.")
        print(f"To merge unique heuristics:    python {Path(__file__).name} --merge")
        print(f"To merge and cleanup:          python {Path(__file__).name} --cleanup")
        sys.exit(0)

    print(f"\nMerging {total_unique_heuristics} unique heuristics...")

    conn = sqlite3.connect(str(CANONICAL_DB))
    merged_count = 0

    try:
        for db_path, unique_heuristics in merge_candidates:
            for h in unique_heuristics:
                new_id = merge_heuristic(conn, h)
                merged_count += 1
                print(f"  Merged: [{h.get('domain')}] {h.get('rule', '')[:40]}... (new ID: {new_id})")

        conn.commit()
        print(f"\nSuccessfully merged {merged_count} heuristics!")

    except Exception as e:
        conn.rollback()
        print(f"\nERROR during merge: {e}")
        sys.exit(1)
    finally:
        conn.close()

    if args.cleanup:
        print("\nCleaning up orphan databases...")
        backup_dir = BASE_DIR / "backups" / f"db-consolidation-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        backup_dir.mkdir(parents=True, exist_ok=True)

        for db_path in orphan_dbs:
            rel_path = db_path.relative_to(BASE_DIR) if db_path.is_relative_to(BASE_DIR) else db_path
            backup_path = backup_dir / rel_path.name

            shutil.copy2(db_path, backup_path)
            db_path.unlink()
            print(f"  Removed: {rel_path} (backed up to {backup_path.name})")

        print(f"\nBackups saved to: {backup_dir}")

    print("\nDone!")


if __name__ == "__main__":
    main()
