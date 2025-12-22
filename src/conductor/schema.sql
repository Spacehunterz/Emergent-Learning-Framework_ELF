-- Conductor Schema Additions for Agent Coordination
-- These tables extend the existing index.db schema for workflow orchestration
-- Apply with: sqlite3 ~/.claude/emergent-learning/memory/index.db < schema.sql

-- ============================================================================
-- WORKFLOW DEFINITIONS
-- Named workflow graphs that can be executed multiple times
-- ============================================================================
CREATE TABLE IF NOT EXISTS workflows (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    description TEXT,
    -- JSON array of node definitions: [{id, name, type, prompt_template, ...}]
    nodes_json TEXT NOT NULL DEFAULT '[]',
    -- Default configuration for the workflow
    config_json TEXT DEFAULT '{}',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_workflows_name ON workflows(name);

-- ============================================================================
-- WORKFLOW EDGES
-- Graph edges defining execution order and conditions
-- ============================================================================
CREATE TABLE IF NOT EXISTS workflow_edges (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    workflow_id INTEGER NOT NULL,
    from_node TEXT NOT NULL,           -- Node ID (or '__start__' for entry points)
    to_node TEXT NOT NULL,             -- Node ID (or '__end__' for terminal nodes)
    -- Condition for edge traversal (empty = always, else Python expression)
    condition TEXT DEFAULT '',
    -- Priority when multiple edges match (lower = higher priority)
    priority INTEGER DEFAULT 100,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (workflow_id) REFERENCES workflows(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_edges_workflow ON workflow_edges(workflow_id);
CREATE INDEX IF NOT EXISTS idx_edges_from ON workflow_edges(from_node);
CREATE INDEX IF NOT EXISTS idx_edges_to ON workflow_edges(to_node);

-- ============================================================================
-- WORKFLOW RUNS
-- Individual execution instances of a workflow
-- ============================================================================
CREATE TABLE IF NOT EXISTS workflow_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    workflow_id INTEGER,               -- NULL for ad-hoc swarms
    workflow_name TEXT,                -- Denormalized for quick access
    -- Execution state
    status TEXT NOT NULL DEFAULT 'pending',  -- pending, running, completed, failed, cancelled
    phase TEXT DEFAULT 'init',         -- Current phase (init, explore, converge, etc.)
    -- Context and results
    input_json TEXT DEFAULT '{}',      -- Initial input parameters
    output_json TEXT DEFAULT '{}',     -- Final aggregated output
    context_json TEXT DEFAULT '{}',    -- Shared context across nodes
    -- Metrics
    total_nodes INTEGER DEFAULT 0,
    completed_nodes INTEGER DEFAULT 0,
    failed_nodes INTEGER DEFAULT 0,
    -- Timing
    started_at DATETIME,
    completed_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    -- Error tracking
    error_message TEXT,
    FOREIGN KEY (workflow_id) REFERENCES workflows(id)
);

CREATE INDEX IF NOT EXISTS idx_runs_workflow ON workflow_runs(workflow_id);
CREATE INDEX IF NOT EXISTS idx_runs_status ON workflow_runs(status);
CREATE INDEX IF NOT EXISTS idx_runs_created ON workflow_runs(created_at DESC);

-- ============================================================================
-- NODE EXECUTIONS
-- Every subagent/node execution with full context
-- ============================================================================
CREATE TABLE IF NOT EXISTS node_executions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER NOT NULL,
    -- Node identification
    node_id TEXT NOT NULL,             -- Node ID within workflow
    node_name TEXT,                    -- Human-readable name
    node_type TEXT NOT NULL DEFAULT 'single',  -- single, parallel, swarm
    -- Agent linkage
    agent_id TEXT,                     -- Links to blackboard agent_id
    session_id TEXT,                   -- Claude session ID if available
    -- Execution details
    prompt TEXT,                       -- Full prompt sent to agent
    prompt_hash TEXT,                  -- SHA256 of prompt for deduplication
    -- Results
    status TEXT NOT NULL DEFAULT 'pending',  -- pending, running, completed, failed, skipped
    result_json TEXT DEFAULT '{}',     -- Structured output
    result_text TEXT,                  -- Raw text output
    -- Findings extracted
    findings_json TEXT DEFAULT '[]',   -- Array of extracted findings
    files_modified TEXT DEFAULT '[]',  -- Array of files touched
    -- Metrics
    duration_ms INTEGER,               -- Execution time in milliseconds
    token_count INTEGER,               -- Approximate tokens used
    retry_count INTEGER DEFAULT 0,     -- Number of retries
    -- Timing
    started_at DATETIME,
    completed_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    -- Error tracking
    error_message TEXT,
    error_type TEXT,                   -- blocker, timeout, crash, etc.
    FOREIGN KEY (run_id) REFERENCES workflow_runs(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_node_exec_run ON node_executions(run_id);
CREATE INDEX IF NOT EXISTS idx_node_exec_agent ON node_executions(agent_id);
CREATE INDEX IF NOT EXISTS idx_node_exec_status ON node_executions(status);
CREATE INDEX IF NOT EXISTS idx_node_exec_created ON node_executions(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_node_exec_node_id ON node_executions(node_id);
CREATE INDEX IF NOT EXISTS idx_node_exec_prompt_hash ON node_executions(prompt_hash);

-- ============================================================================
-- PHEROMONE TRAILS
-- Swarm intelligence signals for coordinated exploration
-- ============================================================================
CREATE TABLE IF NOT EXISTS trails (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER,                    -- Which workflow run
    -- Trail location
    location TEXT NOT NULL,            -- File path, function name, or concept
    location_type TEXT DEFAULT 'file', -- file, function, class, concept, tag
    -- Trail properties
    scent TEXT NOT NULL,               -- Type: discovery, warning, blocker, hot, cold
    strength REAL DEFAULT 1.0,         -- 0.0-1.0, decays over time
    -- Source
    agent_id TEXT,                     -- Who laid the trail
    node_id TEXT,                      -- Which node execution
    -- Metadata
    message TEXT,                      -- Optional description
    tags TEXT,                         -- Comma-separated tags
    -- Timing
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    expires_at DATETIME,               -- When trail should be considered stale
    FOREIGN KEY (run_id) REFERENCES workflow_runs(id)
);

CREATE INDEX IF NOT EXISTS idx_trails_run ON trails(run_id);
CREATE INDEX IF NOT EXISTS idx_trails_location ON trails(location);
CREATE INDEX IF NOT EXISTS idx_trails_scent ON trails(scent);
CREATE INDEX IF NOT EXISTS idx_trails_strength ON trails(strength DESC);
CREATE INDEX IF NOT EXISTS idx_trails_created ON trails(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_trails_agent ON trails(agent_id);

-- ============================================================================
-- CONDUCTOR DECISIONS
-- Audit log of orchestration decisions
-- ============================================================================
CREATE TABLE IF NOT EXISTS conductor_decisions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER NOT NULL,
    decision_type TEXT NOT NULL,       -- fire_node, skip_node, retry, abort, phase_change
    decision_data TEXT DEFAULT '{}',   -- JSON with decision details
    reason TEXT,                       -- Human-readable explanation
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (run_id) REFERENCES workflow_runs(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_decisions_run ON conductor_decisions(run_id);
CREATE INDEX IF NOT EXISTS idx_decisions_type ON conductor_decisions(decision_type);

-- ============================================================================
-- SCHEMA VERSION TRACKING
-- ============================================================================
INSERT OR IGNORE INTO schema_version (version, description)
VALUES (2, 'Added conductor tables: workflows, workflow_edges, workflow_runs, node_executions, trails, conductor_decisions');

-- Update query planner statistics
ANALYZE;
