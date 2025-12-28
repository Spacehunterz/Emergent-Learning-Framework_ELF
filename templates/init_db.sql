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

-- Confidence update audit trail
CREATE TABLE IF NOT EXISTS confidence_updates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    heuristic_id INTEGER NOT NULL,
    old_confidence REAL NOT NULL,
    new_confidence REAL NOT NULL,
    delta REAL NOT NULL,
    update_type TEXT NOT NULL,
    reason TEXT,
    rate_limited INTEGER DEFAULT 0,
    session_id TEXT,
    agent_id TEXT,
    raw_target_confidence REAL,
    smoothed_delta REAL,
    alpha_used REAL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (heuristic_id) REFERENCES heuristics(id)
);

CREATE INDEX IF NOT EXISTS idx_confidence_updates_heuristic ON confidence_updates(heuristic_id);
CREATE INDEX IF NOT EXISTS idx_confidence_updates_created ON confidence_updates(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_confidence_updates_type ON confidence_updates(update_type);

-- Extracted heuristics (learned patterns)
CREATE TABLE IF NOT EXISTS heuristics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    domain TEXT NOT NULL,
    rule TEXT NOT NULL,
    explanation TEXT,
    source_type TEXT,
    source_id INTEGER,
    confidence REAL DEFAULT 0.5 CHECK(confidence >= 0.0 AND confidence <= 1.0),
    confidence_ema REAL DEFAULT 0.5,
    ema_alpha REAL DEFAULT 0.15,
    ema_warmup_remaining INTEGER DEFAULT 5,
    status TEXT DEFAULT 'active' CHECK(status IN ('active', 'deprecated', 'archived')),
    times_validated INTEGER DEFAULT 0 CHECK(times_validated >= 0),
    times_violated INTEGER DEFAULT 0 CHECK(times_violated >= 0),
    times_contradicted INTEGER DEFAULT 0 CHECK(times_contradicted >= 0),
    update_count_today INTEGER DEFAULT 0,
    update_count_reset_date TEXT,
    last_confidence_update DATETIME,
    last_ema_update DATETIME,
    last_used_at DATETIME,
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

-- Building query logging (tracks all queries to the framework)
CREATE TABLE IF NOT EXISTS building_queries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    query_type TEXT NOT NULL,
    session_id TEXT,
    agent_id TEXT,
    domain TEXT,
    tags TEXT,
    limit_requested INTEGER,
    max_tokens_requested INTEGER,
    results_returned INTEGER,
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

-- Spike reports (time-boxed research investigations)
CREATE TABLE IF NOT EXISTS spike_reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    topic TEXT,
    question TEXT,
    findings TEXT,
    gotchas TEXT,
    resources TEXT,
    time_invested_minutes INTEGER,
    domain TEXT,
    tags TEXT,
    usefulness_score REAL DEFAULT 0,
    access_count INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Assumptions tracking (hypotheses to verify or challenge)
CREATE TABLE IF NOT EXISTS assumptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    assumption TEXT NOT NULL,
    context TEXT,
    source TEXT,
    confidence REAL DEFAULT 0.5 CHECK(confidence >= 0.0 AND confidence <= 1.0),
    status TEXT DEFAULT 'active' CHECK(status IN ('active', 'verified', 'challenged', 'invalidated')),
    domain TEXT,
    verified_count INTEGER DEFAULT 0,
    challenged_count INTEGER DEFAULT 0,
    last_verified_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Session summaries (haiku-generated summaries of Claude sessions)
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


-- Indexes for new tables
CREATE INDEX IF NOT EXISTS idx_building_queries_type ON building_queries(query_type);
CREATE INDEX IF NOT EXISTS idx_building_queries_session ON building_queries(session_id);
CREATE INDEX IF NOT EXISTS idx_building_queries_created ON building_queries(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_building_queries_status ON building_queries(status);

CREATE INDEX IF NOT EXISTS idx_spike_reports_domain ON spike_reports(domain);
CREATE INDEX IF NOT EXISTS idx_spike_reports_topic ON spike_reports(topic);
CREATE INDEX IF NOT EXISTS idx_spike_reports_created ON spike_reports(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_spike_reports_usefulness ON spike_reports(usefulness_score DESC);

CREATE INDEX IF NOT EXISTS idx_assumptions_domain ON assumptions(domain);
CREATE INDEX IF NOT EXISTS idx_assumptions_status ON assumptions(status);
CREATE INDEX IF NOT EXISTS idx_assumptions_confidence ON assumptions(confidence DESC);
CREATE INDEX IF NOT EXISTS idx_assumptions_created ON assumptions(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_session_summaries_session ON session_summaries(session_id);
CREATE INDEX IF NOT EXISTS idx_session_summaries_project ON session_summaries(project);
CREATE INDEX IF NOT EXISTS idx_session_summaries_summarized ON session_summaries(summarized_at DESC);
CREATE INDEX IF NOT EXISTS idx_session_summaries_stale ON session_summaries(is_stale);

-- Domain baselines for fraud detection
CREATE TABLE IF NOT EXISTS domain_baselines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    domain TEXT NOT NULL UNIQUE,
    avg_success_rate REAL NOT NULL DEFAULT 0.5,
    std_success_rate REAL NOT NULL DEFAULT 0.1,
    avg_update_frequency REAL,
    std_update_frequency REAL,
    sample_count INTEGER DEFAULT 0,
    calculated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Domain baseline history for drift tracking
CREATE TABLE IF NOT EXISTS domain_baseline_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    domain TEXT NOT NULL,
    avg_success_rate REAL NOT NULL,
    std_success_rate REAL NOT NULL,
    avg_update_frequency REAL,
    std_update_frequency REAL,
    sample_count INTEGER NOT NULL,
    calculated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    prev_avg_success_rate REAL,
    prev_std_success_rate REAL,
    drift_percentage REAL,
    is_significant_drift INTEGER DEFAULT 0,
    triggered_by TEXT DEFAULT 'manual',
    notes TEXT
);

-- Baseline drift alerts
CREATE TABLE IF NOT EXISTS baseline_drift_alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    domain TEXT NOT NULL,
    baseline_history_id INTEGER NOT NULL,
    drift_percentage REAL NOT NULL,
    previous_baseline REAL NOT NULL,
    new_baseline REAL NOT NULL,
    severity TEXT CHECK(severity IN ('low', 'medium', 'high', 'critical')),
    alerted_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    acknowledged_at DATETIME,
    acknowledged_by TEXT,
    resolution_notes TEXT,
    FOREIGN KEY (baseline_history_id) REFERENCES domain_baseline_history(id)
);

-- Baseline refresh schedule
CREATE TABLE IF NOT EXISTS baseline_refresh_schedule (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    domain TEXT UNIQUE,
    interval_days INTEGER NOT NULL DEFAULT 30,
    last_refresh DATETIME,
    next_refresh DATETIME,
    enabled INTEGER DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_domain_baselines_domain ON domain_baselines(domain);
CREATE INDEX IF NOT EXISTS idx_baseline_history_domain ON domain_baseline_history(domain);
CREATE INDEX IF NOT EXISTS idx_baseline_history_calculated ON domain_baseline_history(calculated_at DESC);
CREATE INDEX IF NOT EXISTS idx_drift_alerts_domain ON baseline_drift_alerts(domain);
CREATE INDEX IF NOT EXISTS idx_drift_alerts_severity ON baseline_drift_alerts(severity);
CREATE INDEX IF NOT EXISTS idx_refresh_schedule_domain ON baseline_refresh_schedule(domain);
CREATE INDEX IF NOT EXISTS idx_refresh_schedule_next ON baseline_refresh_schedule(next_refresh);

-- Views for baseline monitoring
CREATE VIEW IF NOT EXISTS domains_needing_refresh AS
SELECT
    brs.domain,
    brs.last_refresh,
    brs.next_refresh,
    brs.interval_days,
    JULIANDAY('now') - JULIANDAY(brs.last_refresh) AS days_since_refresh,
    CASE
        WHEN brs.next_refresh IS NULL THEN 1
        WHEN JULIANDAY('now') >= JULIANDAY(brs.next_refresh) THEN 1
        ELSE 0
    END AS needs_refresh
FROM baseline_refresh_schedule brs
WHERE brs.enabled = 1;

CREATE VIEW IF NOT EXISTS domains_with_drift AS
SELECT
    dbh.domain,
    dbh.drift_percentage,
    dbh.is_significant_drift,
    dbh.calculated_at,
    dbh.prev_avg_success_rate,
    dbh.avg_success_rate
FROM domain_baseline_history dbh
WHERE dbh.is_significant_drift = 1
  AND dbh.calculated_at >= datetime('now', '-30 days');

CREATE VIEW IF NOT EXISTS recent_baseline_changes AS
SELECT
    dbh.domain,
    dbh.avg_success_rate,
    dbh.std_success_rate,
    dbh.sample_count,
    dbh.calculated_at,
    dbh.drift_percentage,
    dbh.triggered_by
FROM domain_baseline_history dbh
WHERE dbh.calculated_at = (
    SELECT MAX(dbh2.calculated_at)
    FROM domain_baseline_history dbh2
    WHERE dbh2.domain = dbh.domain
);

CREATE VIEW IF NOT EXISTS unacknowledged_drift_alerts AS
SELECT
    bda.*
FROM baseline_drift_alerts bda
WHERE bda.acknowledged_at IS NULL;

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

-- Initialize schema version
INSERT OR REPLACE INTO schema_version (version, description) VALUES (2, 'Added building_queries, spike_reports, assumptions, session_summaries tables');

-- Initialize db operations tracking
INSERT OR IGNORE INTO db_operations (id, operation_count, total_vacuums, total_analyzes) VALUES (1, 0, 0, 0);

-- Analyze tables for query planner
ANALYZE;
