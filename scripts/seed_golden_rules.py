#!/usr/bin/env python3
"""
Seed golden rules from markdown into the database.

Reads memory/golden-rules.md and inserts rules into heuristics table with is_golden=1.
Idempotent - safe to run multiple times.

Usage:
    python seed_golden_rules.py [--dry-run]
"""

import argparse
import re
import sqlite3
import sys
from datetime import datetime
from pathlib import Path


# Resolve paths
SCRIPT_DIR = Path(__file__).resolve().parent
BASE_DIR = SCRIPT_DIR.parent
MEMORY_DIR = BASE_DIR / "memory"
DB_PATH = MEMORY_DIR / "index.db"
GOLDEN_RULES_FILE = MEMORY_DIR / "golden-rules.md"


def parse_golden_rules(content: str) -> list:
    """
    Parse golden rules from markdown content.

    Expected format:
    ## N. Rule Title
    > Rule statement here
    **Why:** Explanation here
    """
    rules = []

    # Pattern to match rule sections
    # More flexible pattern that handles various formats
    pattern = re.compile(
        r'##\s+(\d+)\.\s+(.+?)\n'  # ## N. Title
        r'>\s*(.+?)\n'             # > Rule statement
        r'.*?'                      # Any content between
        r'\*\*Why:\*\*\s*(.+?)(?=\n---|\n##|\Z)',  # **Why:** explanation
        re.DOTALL
    )

    for match in pattern.finditer(content):
        num = int(match.group(1))
        title = match.group(2).strip()
        statement = match.group(3).strip()
        explanation = match.group(4).strip()

        rules.append({
            'num': num,
            'title': title,
            'statement': statement,
            'explanation': explanation
        })

    return rules


def ensure_schema(conn: sqlite3.Connection):
    """Ensure heuristics table exists with correct schema."""
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS heuristics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            domain TEXT NOT NULL,
            rule TEXT NOT NULL,
            explanation TEXT,
            source_type TEXT,
            source_id INTEGER,
            confidence REAL DEFAULT 0.5,
            times_validated INTEGER DEFAULT 0,
            times_violated INTEGER DEFAULT 0,
            is_golden INTEGER DEFAULT 0,
            project_path TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Create index on is_golden if not exists
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_heuristics_is_golden
        ON heuristics(is_golden)
    """)

    conn.commit()


def seed_rule(conn: sqlite3.Connection, rule: dict, dry_run: bool = False) -> str:
    """
    Insert or update a golden rule in the database.

    Returns: 'inserted', 'updated', or 'skipped'
    """
    cursor = conn.cursor()

    # Check if rule already exists (by statement similarity)
    cursor.execute(
        "SELECT id, rule FROM heuristics WHERE is_golden = 1 AND rule = ?",
        (rule['statement'],)
    )
    existing = cursor.fetchone()

    if existing:
        if dry_run:
            print(f"  [DRY-RUN] Would skip (already exists): #{rule['num']} {rule['title']}")
            return 'skipped'
        return 'skipped'

    if dry_run:
        print(f"  [DRY-RUN] Would insert: #{rule['num']} {rule['title']}")
        print(f"    Statement: {rule['statement'][:80]}...")
        return 'inserted'

    # Insert new golden rule
    cursor.execute("""
        INSERT INTO heuristics (
            domain, rule, explanation, source_type,
            confidence, is_golden, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        'golden',
        rule['statement'],
        f"{rule['title']}: {rule['explanation']}",
        'markdown-seed',
        1.0,
        1,
        datetime.utcnow().isoformat(),
        datetime.utcnow().isoformat()
    ))

    conn.commit()
    return 'inserted'


def main():
    parser = argparse.ArgumentParser(description='Seed golden rules into database')
    parser.add_argument('--dry-run', action='store_true',
                        help='Show what would be done without making changes')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Show detailed output')
    args = parser.parse_args()

    # Check prerequisites
    if not DB_PATH.exists():
        print(f"ERROR: Database not found at {DB_PATH}")
        print("Run query.py first to initialize the database.")
        return 1

    if not GOLDEN_RULES_FILE.exists():
        print(f"ERROR: Golden rules file not found at {GOLDEN_RULES_FILE}")
        return 1

    # Read and parse golden rules
    content = GOLDEN_RULES_FILE.read_text(encoding='utf-8')
    rules = parse_golden_rules(content)

    if not rules:
        print("WARNING: No rules found in golden-rules.md")
        print("Check the file format matches expected pattern.")
        return 1

    print(f"Found {len(rules)} golden rules in {GOLDEN_RULES_FILE.name}")

    if args.dry_run:
        print("\n=== DRY RUN MODE ===\n")

    # Connect to database and seed rules
    conn = sqlite3.connect(str(DB_PATH))

    try:
        ensure_schema(conn)

        # Get count before
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM heuristics WHERE is_golden = 1")
        count_before = cursor.fetchone()[0]

        # Seed each rule
        stats = {'inserted': 0, 'updated': 0, 'skipped': 0}

        for rule in rules:
            result = seed_rule(conn, rule, args.dry_run)
            stats[result] += 1

            if args.verbose and not args.dry_run:
                print(f"  [{result.upper()}] #{rule['num']} {rule['title']}")

        # Get count after
        cursor.execute("SELECT COUNT(*) FROM heuristics WHERE is_golden = 1")
        count_after = cursor.fetchone()[0]

        print(f"\nResults:")
        print(f"  Before: {count_before} golden rules")
        print(f"  After:  {count_after} golden rules")
        print(f"  Inserted: {stats['inserted']}, Skipped: {stats['skipped']}")

        if args.dry_run:
            print("\n[DRY RUN] No changes were made.")
        else:
            print("\nGolden rules seeded successfully!")

    finally:
        conn.close()

    return 0


if __name__ == '__main__':
    sys.exit(main())
