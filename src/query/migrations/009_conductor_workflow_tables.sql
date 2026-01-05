-- Conductor/workflow orchestration tables
-- These support multi-agent coordination and workflow execution

CREATE TABLE IF NOT EXISTS workflows (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    description TEXT,
    nodes_json TEXT NOT NULL DEFAULT '[]',
    config_json TEXT DEFAULT '{}',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME
);

CREATE INDEX IF NOT EXISTS idx_workflows_name ON workflows(name);

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

CREATE INDEX IF NOT EXISTS idx_edges_workflow ON workflow_edges(workflow_id);
CREATE INDEX IF NOT EXISTS idx_edges_from ON workflow_edges(from_node);
CREATE INDEX IF NOT EXISTS idx_edges_to ON workflow_edges(to_node);

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

CREATE INDEX IF NOT EXISTS idx_runs_workflow ON workflow_runs(workflow_id);
CREATE INDEX IF NOT EXISTS idx_runs_status ON workflow_runs(status);
CREATE INDEX IF NOT EXISTS idx_runs_created ON workflow_runs(created_at DESC);

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

CREATE INDEX IF NOT EXISTS idx_node_exec_run ON node_executions(run_id);
CREATE INDEX IF NOT EXISTS idx_node_exec_agent ON node_executions(agent_id);
CREATE INDEX IF NOT EXISTS idx_node_exec_status ON node_executions(status);
CREATE INDEX IF NOT EXISTS idx_node_exec_created ON node_executions(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_node_exec_node_id ON node_executions(node_id);

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

CREATE INDEX IF NOT EXISTS idx_trails_run ON trails(run_id);
CREATE INDEX IF NOT EXISTS idx_trails_location ON trails(location);
CREATE INDEX IF NOT EXISTS idx_trails_scent ON trails(scent);
CREATE INDEX IF NOT EXISTS idx_trails_strength ON trails(strength DESC);
CREATE INDEX IF NOT EXISTS idx_trails_created ON trails(created_at DESC);

CREATE TABLE IF NOT EXISTS conductor_decisions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER NOT NULL,
    decision_type TEXT NOT NULL,
    decision_data TEXT DEFAULT '{}',
    reason TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (run_id) REFERENCES workflow_runs(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_decisions_run ON conductor_decisions(run_id);
CREATE INDEX IF NOT EXISTS idx_decisions_type ON conductor_decisions(decision_type);
