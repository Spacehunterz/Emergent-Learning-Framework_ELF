#!/usr/bin/env python3
"""
Migration: Add plans and postmortems tables for plan-postmortem learning.

This enables the workflow:
  PLAN (before) -> EXECUTE -> POSTMORTEM (after) -> LEARNING
"""

import sqlite3
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
BASE_DIR = SCRIPT_DIR.parent
DB_PATH = BASE_DIR / "memory" / "index.db"

MIGRATION_SQL = """
-- Plans: Pre-task intent capture for plan-postmortem learning
CREATE TABLE IF NOT EXISTS plans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT UNIQUE,                    -- Slug for linking (e.g., 'refactor-auth-2025-12-16')
    title TEXT NOT NULL,                    -- Brief task title
    description TEXT,                       -- What we're trying to accomplish
    approach TEXT,                          -- How we plan to do it
    risks TEXT,                             -- Identified risks/concerns
    expected_outcome TEXT,                  -- What success looks like
    domain TEXT,                            -- Domain category
    status TEXT DEFAULT 'active',           -- 'active' | 'completed' | 'abandoned'
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    completed_at DATETIME
);

-- Postmortems: Post-task analysis linked to plans
CREATE TABLE IF NOT EXISTS postmortems (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    plan_id INTEGER,                        -- FK to plans.id (optional - can exist without plan)
    title TEXT NOT NULL,                    -- Brief description
    actual_outcome TEXT,                    -- What actually happened
    divergences TEXT,                       -- What differed from plan
    went_well TEXT,                         -- What succeeded
    went_wrong TEXT,                        -- What failed
    lessons TEXT,                           -- Key takeaways
    heuristics_extracted TEXT,              -- JSON array of heuristic IDs created from this
    domain TEXT,                            -- Domain category
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (plan_id) REFERENCES plans(id)
);

-- Indexes for plans and postmortems
CREATE INDEX IF NOT EXISTS idx_plans_status ON plans(status);
CREATE INDEX IF NOT EXISTS idx_plans_domain ON plans(domain);
CREATE INDEX IF NOT EXISTS idx_plans_task_id ON plans(task_id);
CREATE INDEX IF NOT EXISTS idx_postmortems_plan_id ON postmortems(plan_id);
CREATE INDEX IF NOT EXISTS idx_postmortems_domain ON postmortems(domain);
"""

def main():
    print(f"Migrating database: {DB_PATH}")

    if not DB_PATH.exists():
        print(f"ERROR: Database not found at {DB_PATH}")
        return 1

    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()

    # Check if tables already exist
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='plans'")
    if cursor.fetchone():
        print("Tables already exist. Migration skipped.")
        conn.close()
        return 0

    # Run migration
    try:
        cursor.executescript(MIGRATION_SQL)
        conn.commit()
        print("Migration successful!")
        print("  - Created table: plans")
        print("  - Created table: postmortems")
        print("  - Created indexes")
    except Exception as e:
        print(f"ERROR: Migration failed: {e}")
        conn.close()
        return 1

    conn.close()
    return 0

if __name__ == "__main__":
    exit(main())
