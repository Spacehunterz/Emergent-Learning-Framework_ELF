-- Ensure spike_reports table exists with all required columns
-- Fixes: no such column: t1.topic error from issue #63

CREATE TABLE IF NOT EXISTS spike_reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    topic TEXT NOT NULL,
    question TEXT NOT NULL,
    findings TEXT NOT NULL,
    gotchas TEXT,
    resources TEXT,
    time_invested_minutes INTEGER,
    domain TEXT,
    tags TEXT,
    usefulness_score REAL DEFAULT 0,
    access_count INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME
);

-- Add missing columns to spike_reports if they don't exist
-- These statements will fail silently if columns already exist
ALTER TABLE spike_reports ADD COLUMN topic TEXT NOT NULL DEFAULT '';
ALTER TABLE spike_reports ADD COLUMN question TEXT NOT NULL DEFAULT '';
ALTER TABLE spike_reports ADD COLUMN findings TEXT NOT NULL DEFAULT '';

-- Ensure indexes exist
CREATE INDEX IF NOT EXISTS idx_spike_reports_domain ON spike_reports(domain);
CREATE INDEX IF NOT EXISTS idx_spike_reports_topic ON spike_reports(topic);
CREATE INDEX IF NOT EXISTS idx_spike_reports_created_at ON spike_reports(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_spike_reports_tags ON spike_reports(tags);
