-- Migration 001: Add schema version tracking
-- Creates the schema_version table to track database migrations
-- This migration bootstraps the version tracking system

CREATE TABLE IF NOT EXISTS schema_version (
    id INTEGER PRIMARY KEY CHECK (id = 1),  -- Ensure single row
    version INTEGER NOT NULL DEFAULT 1,
    applied_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Insert initial version record
INSERT OR IGNORE INTO schema_version (id, version, applied_at)
VALUES (1, 1, datetime('now'));
