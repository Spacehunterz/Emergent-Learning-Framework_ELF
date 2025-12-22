-- Agent D: SQLite Database Fixes
-- Apply these fixes to existing databases to harden against edge cases

-- ============================================================
-- FIX 1: Add UNIQUE constraint on filepath
-- ============================================================
-- Note: SQLite doesn't support adding UNIQUE constraint to existing column
-- Must recreate table with constraint

BEGIN TRANSACTION;

-- Create new table with UNIQUE constraint
CREATE TABLE learnings_new (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type TEXT NOT NULL CHECK(type IN ('failure', 'success', 'observation', 'experiment')),
    filepath TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    summary TEXT,
    tags TEXT,
    domain TEXT,
    severity INTEGER DEFAULT 3 CHECK(severity >= 1 AND severity <= 5),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Copy data (handle duplicates by keeping first occurrence)
INSERT INTO learnings_new (id, type, filepath, title, summary, tags, domain, severity, created_at, updated_at)
SELECT id, type, filepath, title, summary, tags, domain, severity, created_at, updated_at
FROM learnings
WHERE id IN (
    SELECT MIN(id)
    FROM learnings
    GROUP BY filepath
);

-- Drop old table
DROP TABLE learnings;

-- Rename new table
ALTER TABLE learnings_new RENAME TO learnings;

-- Recreate indexes
CREATE INDEX idx_learnings_domain ON learnings(domain);
CREATE INDEX idx_learnings_type ON learnings(type);
CREATE INDEX idx_learnings_created_at ON learnings(created_at DESC);
CREATE INDEX idx_learnings_domain_created ON learnings(domain, created_at DESC);
CREATE INDEX idx_learnings_filepath ON learnings(filepath);

COMMIT;

-- ============================================================
-- FIX 2: Add UNIQUE constraint on heuristics (domain, rule)
-- ============================================================

BEGIN TRANSACTION;

CREATE TABLE heuristics_new (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    domain TEXT NOT NULL,
    rule TEXT NOT NULL,
    explanation TEXT,
    source_type TEXT CHECK(source_type IN ('failure', 'success', 'observation', NULL)),
    source_id INTEGER,
    confidence REAL DEFAULT 0.5 CHECK(confidence >= 0.0 AND confidence <= 1.0),
    times_validated INTEGER DEFAULT 0 CHECK(times_validated >= 0),
    times_violated INTEGER DEFAULT 0 CHECK(times_violated >= 0),
    is_golden BOOLEAN DEFAULT FALSE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(domain, rule)
);

-- Copy data (handle duplicates by keeping highest confidence)
INSERT INTO heuristics_new (id, domain, rule, explanation, source_type, source_id, confidence, times_validated, times_violated, is_golden, created_at, updated_at)
SELECT id, domain, rule, explanation, source_type, source_id, confidence, times_validated, times_violated, is_golden, created_at, updated_at
FROM heuristics
WHERE id IN (
    SELECT id FROM (
        SELECT id, domain, rule, confidence,
               ROW_NUMBER() OVER (PARTITION BY domain, rule ORDER BY confidence DESC, times_validated DESC) as rn
        FROM heuristics
    ) WHERE rn = 1
);

DROP TABLE heuristics;
ALTER TABLE heuristics_new RENAME TO heuristics;

-- Recreate indexes
CREATE INDEX idx_heuristics_domain ON heuristics(domain);
CREATE INDEX idx_heuristics_golden ON heuristics(is_golden);
CREATE INDEX idx_heuristics_created_at ON heuristics(created_at DESC);
CREATE INDEX idx_heuristics_domain_confidence ON heuristics(domain, confidence DESC);

COMMIT;

-- ============================================================
-- FIX 3: Enable WAL mode for better concurrency
-- ============================================================

PRAGMA journal_mode=WAL;
PRAGMA synchronous=NORMAL;
PRAGMA busy_timeout=30000;

-- ============================================================
-- FIX 4: Analyze for query optimization
-- ============================================================

ANALYZE;
