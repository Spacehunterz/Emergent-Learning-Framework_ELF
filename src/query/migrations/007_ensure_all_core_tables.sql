-- Initial schema version tracking table
-- This must exist before any other migrations

CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    applied_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    description TEXT
);

-- Core tables (if they don't exist yet, they will be created by peewee models)
-- This migration mainly ensures schema_version exists

CREATE TABLE IF NOT EXISTS learnings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type TEXT NOT NULL,
    filepath TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    summary TEXT,
    tags TEXT,
    domain TEXT,
    severity TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME
);

CREATE INDEX IF NOT EXISTS idx_learnings_domain ON learnings(domain);
CREATE INDEX IF NOT EXISTS idx_learnings_type ON learnings(type);
CREATE INDEX IF NOT EXISTS idx_learnings_tags ON learnings(tags);
CREATE INDEX IF NOT EXISTS idx_learnings_created_at ON learnings(created_at DESC);

CREATE TABLE IF NOT EXISTS heuristics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    domain TEXT NOT NULL,
    rule TEXT NOT NULL,
    explanation TEXT,
    source_type TEXT,
    source_id INTEGER,
    confidence REAL DEFAULT 0.0,
    times_validated INTEGER DEFAULT 0,
    times_violated INTEGER DEFAULT 0,
    is_golden INTEGER DEFAULT 0,
    status TEXT DEFAULT 'active',
    dormant_since DATETIME,
    revival_conditions TEXT,
    times_revived INTEGER DEFAULT 0,
    times_contradicted INTEGER DEFAULT 0,
    min_applications INTEGER DEFAULT 10,
    last_confidence_update DATETIME,
    update_count_today INTEGER DEFAULT 0,
    update_count_reset_date DATE,
    last_used_at DATETIME,
    confidence_ema REAL,
    ema_alpha REAL,
    ema_warmup_remaining INTEGER DEFAULT 0,
    last_ema_update DATETIME,
    fraud_flags INTEGER DEFAULT 0,
    is_quarantined INTEGER DEFAULT 0,
    last_fraud_check DATETIME,
    project_path TEXT DEFAULT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME
);

CREATE INDEX IF NOT EXISTS idx_heuristics_domain ON heuristics(domain);
CREATE INDEX IF NOT EXISTS idx_heuristics_is_golden ON heuristics(is_golden);
CREATE INDEX IF NOT EXISTS idx_heuristics_confidence ON heuristics(confidence DESC);
CREATE INDEX IF NOT EXISTS idx_heuristics_domain_confidence ON heuristics(domain, confidence DESC);
CREATE INDEX IF NOT EXISTS idx_heuristics_project_path ON heuristics(project_path);
CREATE INDEX IF NOT EXISTS idx_heuristics_status ON heuristics(status);
CREATE INDEX IF NOT EXISTS idx_heuristics_last_used ON heuristics(last_used_at DESC);

CREATE TABLE IF NOT EXISTS experiments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    hypothesis TEXT,
    status TEXT DEFAULT 'active',
    cycles_run INTEGER DEFAULT 0,
    folder_path TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME
);

CREATE TABLE IF NOT EXISTS cycles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    experiment_id INTEGER,
    cycle_number INTEGER,
    try_summary TEXT,
    break_summary TEXT,
    analysis TEXT,
    learning_extracted TEXT,
    heuristic_id INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (experiment_id) REFERENCES experiments(id)
);

CREATE TABLE IF NOT EXISTS decisions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    context TEXT NOT NULL,
    options_considered TEXT,
    decision TEXT NOT NULL,
    rationale TEXT NOT NULL,
    files_touched TEXT,
    tests_added TEXT,
    status TEXT DEFAULT 'accepted',
    domain TEXT,
    superseded_by INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME,
    FOREIGN KEY (superseded_by) REFERENCES decisions(id)
);

CREATE TABLE IF NOT EXISTS invariants (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    statement TEXT NOT NULL,
    rationale TEXT NOT NULL,
    domain TEXT,
    scope TEXT DEFAULT 'codebase',
    validation_type TEXT,
    validation_code TEXT,
    severity TEXT DEFAULT 'error',
    status TEXT DEFAULT 'active',
    violation_count INTEGER DEFAULT 0,
    last_validated_at DATETIME,
    last_violated_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME
);

CREATE TABLE IF NOT EXISTS violations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    rule_id INTEGER NOT NULL,
    rule_name TEXT NOT NULL,
    violation_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    description TEXT,
    session_id TEXT,
    acknowledged BOOLEAN DEFAULT 0
);

CREATE TABLE IF NOT EXISTS assumptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    assumption TEXT NOT NULL,
    context TEXT NOT NULL,
    source TEXT,
    confidence REAL DEFAULT 0.5,
    status TEXT DEFAULT 'active',
    domain TEXT,
    verified_count INTEGER DEFAULT 0,
    challenged_count INTEGER DEFAULT 0,
    last_verified_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME
);

CREATE TABLE IF NOT EXISTS ceo_reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    context TEXT,
    recommendation TEXT,
    status TEXT DEFAULT 'pending',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    reviewed_at DATETIME
);

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

CREATE TABLE IF NOT EXISTS building_queries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    query_type TEXT NOT NULL,
    session_id TEXT,
    agent_id TEXT,
    domain TEXT,
    tags TEXT,
    limit_requested INTEGER DEFAULT 10,
    max_tokens_requested INTEGER,
    results_returned INTEGER DEFAULT 0,
    tokens_approximated INTEGER,
    duration_ms INTEGER,
    status TEXT DEFAULT 'success',
    error_message TEXT,
    error_code TEXT,
    golden_rules_returned INTEGER DEFAULT 0,
    heuristics_count INTEGER DEFAULT 0,
    learnings_count INTEGER DEFAULT 0,
    experiments_count INTEGER DEFAULT 0,
    ceo_reviews_count INTEGER DEFAULT 0,
    query_summary TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    completed_at DATETIME
);

CREATE TABLE IF NOT EXISTS session_contexts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    agent_id TEXT,
    context_hash TEXT NOT NULL,
    context_preview TEXT,
    heuristics_applied TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS session_summaries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL UNIQUE,
    project TEXT NOT NULL,
    tool_summary TEXT,
    content_summary TEXT,
    conversation_summary TEXT,
    files_touched TEXT DEFAULT '[]',
    tool_counts TEXT DEFAULT '{}',
    message_count INTEGER DEFAULT 0,
    session_file_path TEXT,
    session_file_size INTEGER,
    session_last_modified DATETIME,
    summarized_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    summarizer_model TEXT DEFAULT 'haiku',
    summary_version INTEGER DEFAULT 1,
    is_stale INTEGER DEFAULT 0,
    needs_resummarize INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS fraud_reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    heuristic_id INTEGER NOT NULL,
    fraud_score REAL NOT NULL,
    classification TEXT NOT NULL,
    likelihood_ratio REAL,
    signal_count INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    reviewed_at DATETIME,
    reviewed_by TEXT,
    review_outcome TEXT,
    FOREIGN KEY (heuristic_id) REFERENCES heuristics(id)
);

CREATE TABLE IF NOT EXISTS anomaly_signals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fraud_report_id INTEGER NOT NULL,
    heuristic_id INTEGER NOT NULL,
    detector_name TEXT NOT NULL,
    score REAL NOT NULL,
    severity TEXT NOT NULL,
    reason TEXT NOT NULL,
    evidence TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (fraud_report_id) REFERENCES fraud_reports(id),
    FOREIGN KEY (heuristic_id) REFERENCES heuristics(id)
);

CREATE TABLE IF NOT EXISTS domain_metadata (
    domain TEXT PRIMARY KEY,
    soft_limit INTEGER NOT NULL DEFAULT 5,
    hard_limit INTEGER NOT NULL DEFAULT 10,
    ceo_override_limit INTEGER,
    current_count INTEGER NOT NULL DEFAULT 0,
    state TEXT NOT NULL DEFAULT 'normal',
    overflow_entered_at DATETIME,
    expansion_min_confidence REAL DEFAULT 0.70,
    expansion_min_validations INTEGER DEFAULT 3,
    expansion_min_novelty REAL DEFAULT 0.60,
    grace_period_days INTEGER DEFAULT 7,
    max_overflow_days INTEGER DEFAULT 28,
    avg_confidence REAL,
    health_score REAL,
    last_health_check DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME
);

CREATE TABLE IF NOT EXISTS domain_baselines (
    domain TEXT PRIMARY KEY,
    avg_success_rate REAL,
    std_success_rate REAL,
    avg_update_frequency REAL,
    std_update_frequency REAL,
    sample_count INTEGER DEFAULT 0,
    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
);
