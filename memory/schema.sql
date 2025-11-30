-- Emergent Learning Framework - Database Schema

-- Learnings: Index into markdown files
CREATE TABLE IF NOT EXISTS learnings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type TEXT NOT NULL,                    -- 'failure' | 'success'
    filepath TEXT NOT NULL,                -- Relative path to markdown file
    title TEXT NOT NULL,                   -- Short descriptive title
    summary TEXT,                          -- One-liner description
    tags TEXT,                             -- Comma-separated tags
    domain TEXT,                           -- 'coordination' | 'architecture' | 'debugging' | etc
    severity INTEGER DEFAULT 1,            -- 1-5, how significant
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Heuristics: Extracted rules
CREATE TABLE IF NOT EXISTS heuristics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    domain TEXT NOT NULL,                  -- Category of the rule
    rule TEXT NOT NULL,                    -- The actual heuristic
    explanation TEXT,                      -- Why this rule exists
    source_type TEXT,                      -- 'failure' | 'success' | 'observation'
    source_id INTEGER,                     -- FK to learnings.id
    confidence REAL DEFAULT 0.5,           -- 0.0-1.0, increases as proven true
    times_validated INTEGER DEFAULT 0,     -- How many times this proved correct
    times_violated INTEGER DEFAULT 0,      -- How many times ignoring this caused issues
    is_golden BOOLEAN DEFAULT FALSE,       -- Promoted to golden rule?
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Experiments: Track what we're testing
CREATE TABLE IF NOT EXISTS experiments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    hypothesis TEXT NOT NULL,
    status TEXT DEFAULT 'active',          -- 'active' | 'paused' | 'success' | 'failed' | 'inconclusive'
    outcome TEXT,                          -- What happened
    cycles_run INTEGER DEFAULT 0,          -- How many try/break loops
    folder_path TEXT,                      -- Path to experiment folder
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    completed_at DATETIME
);

-- Cycles: The learning loop iterations
CREATE TABLE IF NOT EXISTS cycles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    experiment_id INTEGER,
    cycle_number INTEGER,
    try_summary TEXT,
    break_summary TEXT,
    analysis TEXT,
    learning_extracted TEXT,
    heuristic_id INTEGER,                  -- FK if a heuristic was created
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (experiment_id) REFERENCES experiments(id),
    FOREIGN KEY (heuristic_id) REFERENCES heuristics(id)
);

-- CEO Reviews: Decisions needing human input
CREATE TABLE IF NOT EXISTS ceo_reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    context TEXT,                          -- What's the situation
    options TEXT,                          -- JSON array of options
    recommendation TEXT,                   -- What agents suggest
    decision TEXT,                         -- What CEO decided
    status TEXT DEFAULT 'pending',         -- 'pending' | 'decided'
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    decided_at DATETIME
);

-- Create indexes for fast queries
CREATE INDEX IF NOT EXISTS idx_learnings_type ON learnings(type);
CREATE INDEX IF NOT EXISTS idx_learnings_domain ON learnings(domain);
CREATE INDEX IF NOT EXISTS idx_learnings_tags ON learnings(tags);
CREATE INDEX IF NOT EXISTS idx_heuristics_domain ON heuristics(domain);
CREATE INDEX IF NOT EXISTS idx_heuristics_confidence ON heuristics(confidence);
CREATE INDEX IF NOT EXISTS idx_experiments_status ON experiments(status);
CREATE INDEX IF NOT EXISTS idx_ceo_reviews_status ON ceo_reviews(status);
