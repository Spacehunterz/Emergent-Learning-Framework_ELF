-- Patterns table for session observation and distillation
-- Supports Ralph loop pattern extraction and auto-promotion to heuristics

CREATE TABLE IF NOT EXISTS patterns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pattern_type TEXT NOT NULL CHECK(pattern_type IN ('retry', 'error', 'search', 'success_sequence', 'tool_sequence')),
    pattern_hash TEXT NOT NULL UNIQUE,
    pattern_text TEXT NOT NULL,
    signature TEXT,
    occurrence_count INTEGER DEFAULT 1,
    first_seen DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_seen DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    session_ids TEXT DEFAULT '[]',
    project_path TEXT,
    domain TEXT DEFAULT 'general',
    strength REAL DEFAULT 0.5 CHECK(strength >= 0.0 AND strength <= 1.0),
    promoted_to_heuristic_id INTEGER,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_patterns_type ON patterns(pattern_type);
CREATE UNIQUE INDEX IF NOT EXISTS idx_patterns_hash ON patterns(pattern_hash);
CREATE INDEX IF NOT EXISTS idx_patterns_strength ON patterns(strength DESC);
CREATE INDEX IF NOT EXISTS idx_patterns_last_seen ON patterns(last_seen DESC);
CREATE INDEX IF NOT EXISTS idx_patterns_project_path ON patterns(project_path);
CREATE INDEX IF NOT EXISTS idx_patterns_domain_type ON patterns(domain, pattern_type);
CREATE INDEX IF NOT EXISTS idx_patterns_promoted ON patterns(promoted_to_heuristic_id);
