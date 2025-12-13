-- Emergent Learning Framework - Database Schema
-- Initialize empty database with all required tables

-- Core learning records
CREATE TABLE IF NOT EXISTS learnings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type TEXT NOT NULL CHECK(type IN ('failure', 'success', 'heuristic', 'experiment', 'observation')),
    filepath TEXT NOT NULL,
    title TEXT NOT NULL,
    summary TEXT,
    tags TEXT,
    domain TEXT,
    severity INTEGER DEFAULT 3 CHECK(severity >= 1 AND severity <= 5),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Extracted heuristics (learned patterns)
CREATE TABLE IF NOT EXISTS heuristics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    domain TEXT NOT NULL,
    rule TEXT NOT NULL,
    explanation TEXT,
    source_type TEXT,
    source_id INTEGER,
    confidence REAL DEFAULT 0.5 CHECK(confidence >= 0.0 AND confidence <= 1.0),
    times_validated INTEGER DEFAULT 0 CHECK(times_validated >= 0),
    times_violated INTEGER DEFAULT 0 CHECK(times_violated >= 0),
    is_golden INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Active experiments
CREATE TABLE IF NOT EXISTS experiments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    hypothesis TEXT,
    status TEXT DEFAULT 'active',
    cycles_run INTEGER DEFAULT 0,
    folder_path TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- CEO escalation requests
CREATE TABLE IF NOT EXISTS ceo_reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    context TEXT,
    recommendation TEXT,
    status TEXT DEFAULT 'pending',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    reviewed_at DATETIME
);

-- Experiment cycles
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
    FOREIGN KEY (experiment_id) REFERENCES experiments(id),
    FOREIGN KEY (heuristic_id) REFERENCES heuristics(id)
);

-- Real-time metrics
CREATE TABLE IF NOT EXISTS metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    metric_type TEXT NOT NULL,
    metric_name TEXT NOT NULL,
    metric_value REAL NOT NULL,
    tags TEXT,
    context TEXT
);

-- System health snapshots
CREATE TABLE IF NOT EXISTS system_health (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    status TEXT NOT NULL,
    db_integrity TEXT,
    db_size_mb REAL,
    disk_free_mb REAL,
    git_status TEXT,
    stale_locks INTEGER DEFAULT 0,
    details TEXT
);

-- Golden rule violations (accountability)
CREATE TABLE IF NOT EXISTS violations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    rule_id INTEGER NOT NULL,
    rule_name TEXT NOT NULL,
    violation_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    description TEXT,
    session_id TEXT,
    acknowledged INTEGER DEFAULT 0
);

-- Schema version tracking
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    applied_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    description TEXT
);

-- Database operation tracking
CREATE TABLE IF NOT EXISTS db_operations (
    id INTEGER PRIMARY KEY CHECK(id = 1),
    operation_count INTEGER DEFAULT 0,
    last_vacuum DATETIME,
    last_analyze DATETIME,
    total_vacuums INTEGER DEFAULT 0,
    total_analyzes INTEGER DEFAULT 0
);

-- Workflow definitions (conductor)
CREATE TABLE IF NOT EXISTS workflows (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    description TEXT,
    nodes_json TEXT NOT NULL DEFAULT '[]',
    config_json TEXT DEFAULT '{}',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Workflow edges (transitions)
CREATE TABLE IF NOT EXISTS workflow_edges (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    workflow_id INTEGER NOT NULL,
    from_node TEXT NOT NULL,
    to_node TEXT NOT NULL,
    condition TEXT DEFAULT '',
    priority INTEGER DEFAULT 100,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (workflow_id) REFERENCES workflows(id) ON DELETE CASCADE
);

-- Workflow execution runs
CREATE TABLE IF NOT EXISTS workflow_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    workflow_id INTEGER,
    workflow_name TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    phase TEXT DEFAULT 'init',
    input_json TEXT DEFAULT '{}',
    output_json TEXT DEFAULT '{}',
    context_json TEXT DEFAULT '{}',
    total_nodes INTEGER DEFAULT 0,
    completed_nodes INTEGER DEFAULT 0,
    failed_nodes INTEGER DEFAULT 0,
    started_at DATETIME,
    completed_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    error_message TEXT,
    FOREIGN KEY (workflow_id) REFERENCES workflows(id)
);

-- Individual node executions
CREATE TABLE IF NOT EXISTS node_executions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER NOT NULL,
    node_id TEXT NOT NULL,
    node_name TEXT,
    node_type TEXT NOT NULL DEFAULT 'single',
    agent_id TEXT,
    session_id TEXT,
    prompt TEXT,
    prompt_hash TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    result_json TEXT DEFAULT '{}',
    result_text TEXT,
    findings_json TEXT DEFAULT '[]',
    files_modified TEXT DEFAULT '[]',
    duration_ms INTEGER,
    token_count INTEGER,
    retry_count INTEGER DEFAULT 0,
    started_at DATETIME,
    completed_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    error_message TEXT,
    error_type TEXT,
    FOREIGN KEY (run_id) REFERENCES workflow_runs(id) ON DELETE CASCADE
);

-- Pheromone trails (agent breadcrumbs)
CREATE TABLE IF NOT EXISTS trails (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER,
    location TEXT NOT NULL,
    location_type TEXT DEFAULT 'file',
    scent TEXT NOT NULL,
    strength REAL DEFAULT 1.0,
    agent_id TEXT,
    node_id TEXT,
    message TEXT,
    tags TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    expires_at DATETIME,
    FOREIGN KEY (run_id) REFERENCES workflow_runs(id)
);

-- Conductor decisions log
CREATE TABLE IF NOT EXISTS conductor_decisions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER NOT NULL,
    decision_type TEXT NOT NULL,
    decision_data TEXT DEFAULT '{}',
    reason TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (run_id) REFERENCES workflow_runs(id) ON DELETE CASCADE
);

-- Indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_learnings_domain ON learnings(domain);
CREATE INDEX IF NOT EXISTS idx_learnings_type ON learnings(type);
CREATE INDEX IF NOT EXISTS idx_learnings_tags ON learnings(tags);
CREATE INDEX IF NOT EXISTS idx_learnings_created_at ON learnings(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_learnings_domain_created ON learnings(domain, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_heuristics_domain ON heuristics(domain);
CREATE INDEX IF NOT EXISTS idx_heuristics_golden ON heuristics(is_golden);
CREATE INDEX IF NOT EXISTS idx_heuristics_confidence ON heuristics(confidence);
CREATE INDEX IF NOT EXISTS idx_heuristics_created_at ON heuristics(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_heuristics_domain_confidence ON heuristics(domain, confidence DESC);

CREATE INDEX IF NOT EXISTS idx_experiments_status ON experiments(status);
CREATE INDEX IF NOT EXISTS idx_ceo_reviews_status ON ceo_reviews(status);

CREATE INDEX IF NOT EXISTS idx_metrics_timestamp ON metrics(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_metrics_type ON metrics(metric_type);
CREATE INDEX IF NOT EXISTS idx_metrics_name ON metrics(metric_name);
CREATE INDEX IF NOT EXISTS idx_metrics_type_name ON metrics(metric_type, metric_name, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_health_timestamp ON system_health(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_health_status ON system_health(status);

CREATE INDEX IF NOT EXISTS idx_violations_date ON violations(violation_date DESC);
CREATE INDEX IF NOT EXISTS idx_violations_rule ON violations(rule_id);
CREATE INDEX IF NOT EXISTS idx_violations_acknowledged ON violations(acknowledged);

CREATE INDEX IF NOT EXISTS idx_workflows_name ON workflows(name);

CREATE INDEX IF NOT EXISTS idx_edges_workflow ON workflow_edges(workflow_id);
CREATE INDEX IF NOT EXISTS idx_edges_from ON workflow_edges(from_node);
CREATE INDEX IF NOT EXISTS idx_edges_to ON workflow_edges(to_node);

CREATE INDEX IF NOT EXISTS idx_runs_workflow ON workflow_runs(workflow_id);
CREATE INDEX IF NOT EXISTS idx_runs_status ON workflow_runs(status);
CREATE INDEX IF NOT EXISTS idx_runs_created ON workflow_runs(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_node_exec_run ON node_executions(run_id);
CREATE INDEX IF NOT EXISTS idx_node_exec_agent ON node_executions(agent_id);
CREATE INDEX IF NOT EXISTS idx_node_exec_status ON node_executions(status);
CREATE INDEX IF NOT EXISTS idx_node_exec_created ON node_executions(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_node_exec_node_id ON node_executions(node_id);
CREATE INDEX IF NOT EXISTS idx_node_exec_prompt_hash ON node_executions(prompt_hash);

CREATE INDEX IF NOT EXISTS idx_trails_run ON trails(run_id);
CREATE INDEX IF NOT EXISTS idx_trails_location ON trails(location);
CREATE INDEX IF NOT EXISTS idx_trails_scent ON trails(scent);
CREATE INDEX IF NOT EXISTS idx_trails_strength ON trails(strength DESC);
CREATE INDEX IF NOT EXISTS idx_trails_created ON trails(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_trails_agent ON trails(agent_id);

CREATE INDEX IF NOT EXISTS idx_decisions_run ON conductor_decisions(run_id);
CREATE INDEX IF NOT EXISTS idx_decisions_type ON conductor_decisions(decision_type);

-- Validation triggers
CREATE TRIGGER IF NOT EXISTS learnings_validate_insert
BEFORE INSERT ON learnings
FOR EACH ROW
WHEN NEW.type NOT IN ('failure', 'success', 'heuristic', 'experiment', 'observation')
   OR (CAST(NEW.severity AS INTEGER) < 1 OR CAST(NEW.severity AS INTEGER) > 5)
BEGIN
    SELECT RAISE(ABORT, 'Validation failed: invalid type or severity');
END;

CREATE TRIGGER IF NOT EXISTS learnings_validate_update
BEFORE UPDATE ON learnings
FOR EACH ROW
WHEN NEW.type NOT IN ('failure', 'success', 'heuristic', 'experiment', 'observation')
   OR (CAST(NEW.severity AS INTEGER) < 1 OR CAST(NEW.severity AS INTEGER) > 5)
BEGIN
    SELECT RAISE(ABORT, 'Validation failed: invalid type or severity');
END;

CREATE TRIGGER IF NOT EXISTS heuristics_validate_insert
BEFORE INSERT ON heuristics
FOR EACH ROW
WHEN NEW.confidence < 0.0 OR NEW.confidence > 1.0
   OR NEW.times_validated < 0
   OR (NEW.times_violated IS NOT NULL AND NEW.times_violated < 0)
BEGIN
    SELECT RAISE(ABORT, 'Validation failed: invalid confidence or counts');
END;

CREATE TRIGGER IF NOT EXISTS heuristics_validate_update
BEFORE UPDATE ON heuristics
FOR EACH ROW
WHEN NEW.confidence < 0.0 OR NEW.confidence > 1.0
   OR NEW.times_validated < 0
   OR (NEW.times_violated IS NOT NULL AND NEW.times_violated < 0)
BEGIN
    SELECT RAISE(ABORT, 'Validation failed: invalid confidence or counts');
END;

-- Initialize schema version
INSERT OR IGNORE INTO schema_version (version, description) VALUES (1, 'Initial schema');

-- Initialize db operations tracking
INSERT OR IGNORE INTO db_operations (id, operation_count, total_vacuums, total_analyzes) VALUES (1, 0, 0, 0);

-- Analyze tables for query planner
ANALYZE;
