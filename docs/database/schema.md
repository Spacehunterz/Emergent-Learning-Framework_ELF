# Emergent Learning Framework - Database Schema Documentation

**Version:** 1.0
**Last Updated:** 2026-01-05
**Database Engine:** SQLite 3

---

## 1. Overview

### Database Architecture

The Emergent Learning Framework uses SQLite as its persistence layer, providing a lightweight, file-based database that requires no separate server process. The architecture supports both global (framework-wide) and project-specific databases.

### Database File Locations

| Database | Path | Purpose |
|----------|------|---------|
| Global Database | `~/.claude/emergent-learning/memory/index.db` | Primary ELF knowledge store |
| Project Database | `<project>/.elf/learnings.db` | Project-specific heuristics and learnings |

### ORM Layer

The framework uses **Peewee-AIO** for async database operations. Models are defined in:
- `src/query/models.py` - Async ORM model definitions
- `apps/dashboard/backend/utils/database.py` - Sync utilities and table creation

### Connection Parameters

```python
sqlite3.connect(db_path, timeout=10.0)
conn.row_factory = sqlite3.Row  # Dict-like access
```

---

## 2. Entity Relationship Diagram

```
+------------------+       +------------------+       +------------------+
|    learnings     |       |    heuristics    |       |   experiments    |
+------------------+       +------------------+       +------------------+
| id (PK)          |       | id (PK)          |       | id (PK)          |
| type             |       | domain           |<---+  | name (UNIQUE)    |
| filepath (UNIQUE)|       | rule             |    |  | hypothesis       |
| title            |       | confidence       |    |  | status           |
| domain           |------>| is_golden        |    |  | cycles_run       |
| severity         |       | source_id (FK?)  |    |  +--------+---------+
| created_at       |       | project_path     |    |           |
+------------------+       +--------+---------+    |           |
                                    |              |           |
                                    v              |           v
                           +------------------+    |  +------------------+
                           |     cycles       |    |  |   ceo_reviews    |
                           +------------------+    |  +------------------+
                           | id (PK)          |    |  | id (PK)          |
                           | experiment_id(FK)|----+  | title            |
                           | heuristic_id(FK) |       | status           |
                           | cycle_number     |       | reviewed_at      |
                           +------------------+       +------------------+

+------------------+       +------------------+       +------------------+
|    decisions     |       |   invariants     |       |   violations     |
+------------------+       +------------------+       +------------------+
| id (PK)          |       | id (PK)          |       | id (PK)          |
| title            |       | statement        |       | rule_id          |
| context          |       | rationale        |       | rule_name        |
| decision         |       | domain           |       | violation_date   |
| domain           |       | scope            |       | acknowledged     |
| superseded_by(FK)|----+  | severity         |       +------------------+
+------------------+    |  | violation_count  |
        ^               |  +------------------+
        +---------------+

+------------------+       +------------------+       +------------------+
|    workflows     |       |  workflow_runs   |       | node_executions  |
+------------------+       +------------------+       +------------------+
| id (PK)          |<------| workflow_id (FK) |<------| run_id (FK)      |
| name (UNIQUE)    |       | status           |       | node_id          |
| nodes_json       |       | phase            |       | agent_id         |
| config_json      |       | input_json       |       | status           |
+------------------+       | output_json      |       | result_json      |
        |                  +------------------+       +------------------+
        |                          |
        v                          v
+------------------+       +------------------+
| workflow_edges   |       |     trails       |
+------------------+       +------------------+
| workflow_id (FK) |       | run_id (FK)      |
| from_node        |       | location         |
| to_node          |       | scent            |
| condition        |       | strength         |
+------------------+       +------------------+

+------------------+       +------------------+       +------------------+
|  fraud_reports   |       | anomaly_signals  |       | fraud_responses  |
+------------------+       +------------------+       +------------------+
| id (PK)          |<------| fraud_report_id  |       | fraud_report_id  |
| heuristic_id(FK) |       | heuristic_id(FK) |       | response_type    |
| fraud_score      |       | detector_name    |       | executed_at      |
| classification   |       | score            |       +------------------+
+------------------+       +------------------+

+------------------+       +------------------+       +------------------+
| domain_metadata  |       | domain_baselines |       | expansion_events |
+------------------+       +------------------+       +------------------+
| domain (PK)      |       | domain (PK)      |       | domain           |
| soft_limit       |       | avg_success_rate |       | heuristic_id(FK) |
| hard_limit       |       | std_success_rate |       | event_type       |
| current_count    |       | sample_count     |       | count_before     |
| state            |       +------------------+       | count_after      |
+------------------+                                  +------------------+
```

---

## 3. Core Tables

### 3.1 learnings

**Purpose:** Core learning records capturing failures, successes, and observations from Claude sessions.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | Unique identifier |
| `type` | TEXT | NOT NULL | Type: 'failure', 'success', 'observation', 'experiment' |
| `filepath` | TEXT | NOT NULL, UNIQUE | Path to the learning markdown file |
| `title` | TEXT | NOT NULL | Human-readable title |
| `summary` | TEXT | | Brief description of the learning |
| `tags` | TEXT | | Comma-separated tags for categorization |
| `domain` | TEXT | | Knowledge domain (e.g., 'architecture', 'testing') |
| `severity` | TEXT/INTEGER | | Importance level (1-5 in v1 schema) |
| `created_at` | DATETIME | DEFAULT CURRENT_TIMESTAMP | Creation timestamp |
| `updated_at` | DATETIME | | Last modification timestamp |

**Indexes:**
- `idx_learnings_domain` - Filter by domain
- `idx_learnings_type` - Filter by learning type
- `idx_learnings_tags` - Search by tags
- `idx_learnings_created_at` - Chronological queries
- `idx_learnings_domain_created` - Domain + time compound

**Example Data:**
```sql
INSERT INTO learnings (type, filepath, title, domain, severity)
VALUES ('failure', 'failure-analysis/2025-01-05-sql-injection.md',
        'SQL Injection via String Interpolation', 'security', 5);
```

---

### 3.2 heuristics

**Purpose:** Extracted patterns and rules learned from experiences. Central to the framework's intelligence.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | Unique identifier |
| `domain` | TEXT | NOT NULL | Knowledge domain |
| `rule` | TEXT | NOT NULL | The heuristic statement |
| `explanation` | TEXT | | Why this heuristic matters |
| `source_type` | TEXT | | Origin: 'failure', 'success', 'observation' |
| `source_id` | INTEGER | | FK to source learning (if applicable) |
| `confidence` | REAL | DEFAULT 0.0, CHECK 0.0-1.0 | Confidence score |
| `times_validated` | INTEGER | DEFAULT 0 | Successful applications |
| `times_violated` | INTEGER | DEFAULT 0 | Failed applications |
| `is_golden` | INTEGER | DEFAULT 0 | 1 if promoted to golden rule |
| `status` | TEXT | DEFAULT 'active' | 'active', 'dormant', 'deprecated' |
| `dormant_since` | DATETIME | | When marked dormant |
| `revival_conditions` | TEXT | | Conditions to reactivate |
| `times_revived` | INTEGER | DEFAULT 0 | Revival count |
| `times_contradicted` | INTEGER | DEFAULT 0 | Contradiction count |
| `min_applications` | INTEGER | DEFAULT 10 | Threshold for confidence stability |
| `last_confidence_update` | DATETIME | | Last confidence change |
| `update_count_today` | INTEGER | DEFAULT 0 | Rate limiting counter |
| `update_count_reset_date` | DATE | | Rate limit reset date |
| `last_used_at` | DATETIME | | Last access timestamp |
| `confidence_ema` | REAL | | Exponential moving average |
| `ema_alpha` | REAL | | EMA smoothing factor |
| `ema_warmup_remaining` | INTEGER | DEFAULT 0 | EMA warmup counter |
| `last_ema_update` | DATETIME | | Last EMA calculation |
| `fraud_flags` | INTEGER | DEFAULT 0 | Fraud detection flags |
| `is_quarantined` | INTEGER | DEFAULT 0 | Quarantine status |
| `last_fraud_check` | DATETIME | | Last fraud scan |
| `project_path` | TEXT | DEFAULT NULL | NULL=global, path=project-specific |
| `created_at` | DATETIME | DEFAULT CURRENT_TIMESTAMP | Creation time |
| `updated_at` | DATETIME | | Last update time |

**Indexes:**
- `idx_heuristics_domain` - Filter by domain
- `idx_heuristics_is_golden` - Find golden rules quickly
- `idx_heuristics_confidence` - Sort by confidence
- `idx_heuristics_domain_confidence` - Domain queries sorted by confidence
- `idx_heuristics_project_path` - Project-specific queries
- `idx_heuristics_status` - Filter by status
- `idx_heuristics_last_used` - Access patterns
- `idx_heuristics_ema_warmup` - Partial index for warmup tracking

**Example Data:**
```sql
INSERT INTO heuristics (domain, rule, explanation, confidence, is_golden)
VALUES ('architecture',
        'Always escape user input before SQL interpolation',
        'Direct string interpolation allows injection attacks',
        0.9, 0);
```

---

### 3.3 experiments

**Purpose:** Track active experiments following the TRY-BREAK-ANALYZE-LEARN cycle.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | Unique identifier |
| `name` | TEXT | NOT NULL, UNIQUE | Experiment name/slug |
| `hypothesis` | TEXT | | What we're testing |
| `status` | TEXT | DEFAULT 'active' | 'active', 'completed', 'abandoned' |
| `cycles_run` | INTEGER | DEFAULT 0 | Number of learning cycles |
| `folder_path` | TEXT | | Path to experiment files |
| `created_at` | DATETIME | DEFAULT CURRENT_TIMESTAMP | Start time |
| `updated_at` | DATETIME | | Last update |

**Indexes:**
- `experiment_name` (UNIQUE)
- `idx_experiments_status`

---

### 3.4 cycles

**Purpose:** Individual learning cycles within an experiment.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | Unique identifier |
| `experiment_id` | INTEGER | FK -> experiments.id | Parent experiment |
| `cycle_number` | INTEGER | | Sequence number |
| `try_summary` | TEXT | | What was attempted |
| `break_summary` | TEXT | | What broke |
| `analysis` | TEXT | | Root cause analysis |
| `learning_extracted` | TEXT | | Key takeaways |
| `heuristic_id` | INTEGER | FK -> heuristics.id | Resulting heuristic |
| `created_at` | DATETIME | DEFAULT CURRENT_TIMESTAMP | Cycle timestamp |

---

### 3.5 decisions

**Purpose:** Architecture Decision Records (ADRs) for tracking design choices.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | Unique identifier |
| `title` | TEXT | NOT NULL | Decision title |
| `context` | TEXT | NOT NULL | Background and problem statement |
| `options_considered` | TEXT | | Alternatives evaluated |
| `decision` | TEXT | NOT NULL | The choice made |
| `rationale` | TEXT | NOT NULL | Why this choice |
| `files_touched` | TEXT | | Affected file paths (JSON) |
| `tests_added` | TEXT | | Related test files (JSON) |
| `status` | TEXT | DEFAULT 'accepted' | 'proposed', 'accepted', 'deprecated', 'superseded' |
| `domain` | TEXT | | Knowledge domain |
| `superseded_by` | INTEGER | FK -> decisions.id | Replacement decision |
| `created_at` | DATETIME | DEFAULT CURRENT_TIMESTAMP | Decision date |
| `updated_at` | DATETIME | | Last modification |

**Indexes:**
- `idx_decisions_domain`
- `idx_decisions_status`
- `idx_decisions_created_at`
- `idx_decisions_superseded_by`

---

### 3.6 invariants

**Purpose:** Statements about what must always be true in the codebase.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | Unique identifier |
| `statement` | TEXT | NOT NULL | The invariant statement |
| `rationale` | TEXT | NOT NULL | Why this invariant exists |
| `domain` | TEXT | | Knowledge domain |
| `scope` | TEXT | DEFAULT 'codebase' | 'codebase', 'module', 'function', 'runtime' |
| `validation_type` | TEXT | | 'manual', 'automated', 'test' |
| `validation_code` | TEXT | | Code/script to verify |
| `severity` | TEXT | DEFAULT 'error' | 'error', 'warning', 'info' |
| `status` | TEXT | DEFAULT 'active' | 'active', 'deprecated' |
| `violation_count` | INTEGER | DEFAULT 0 | Times violated |
| `last_validated_at` | DATETIME | | Last verification |
| `last_violated_at` | DATETIME | | Last violation |
| `created_at` | DATETIME | DEFAULT CURRENT_TIMESTAMP | Creation time |
| `updated_at` | DATETIME | | Last update |

---

### 3.7 violations

**Purpose:** Track golden rule and invariant violations for accountability.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | Unique identifier |
| `rule_id` | INTEGER | NOT NULL | ID of violated rule |
| `rule_name` | TEXT | NOT NULL | Name of violated rule |
| `violation_date` | DATETIME | DEFAULT CURRENT_TIMESTAMP | When it occurred |
| `description` | TEXT | | What happened |
| `session_id` | TEXT | | Claude session that violated |
| `acknowledged` | BOOLEAN | DEFAULT 0 | Has CEO acknowledged |

**Indexes:**
- `idx_violations_rule`
- `idx_violations_date`
- `idx_violations_acknowledged`

---

### 3.8 assumptions

**Purpose:** Track hypotheses that need verification.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | Unique identifier |
| `assumption` | TEXT | NOT NULL | The assumption statement |
| `context` | TEXT | NOT NULL | What situation led to this |
| `source` | TEXT | | Where it came from |
| `confidence` | REAL | DEFAULT 0.5, CHECK 0.0-1.0 | Confidence level |
| `status` | TEXT | DEFAULT 'active' | 'active', 'verified', 'challenged', 'invalidated' |
| `domain` | TEXT | | Knowledge domain |
| `verified_count` | INTEGER | DEFAULT 0 | Verification count |
| `challenged_count` | INTEGER | DEFAULT 0 | Challenge count |
| `last_verified_at` | DATETIME | | Last verification |
| `created_at` | DATETIME | DEFAULT CURRENT_TIMESTAMP | Creation time |
| `updated_at` | DATETIME | | Last update |

---

### 3.9 spike_reports

**Purpose:** Time-boxed research investigations and their findings.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | Unique identifier |
| `title` | TEXT | NOT NULL | Short title |
| `topic` | TEXT | NOT NULL | Investigation area |
| `question` | TEXT | NOT NULL | Question being answered |
| `findings` | TEXT | NOT NULL | What was learned (markdown) |
| `gotchas` | TEXT | | Pitfalls and edge cases |
| `resources` | TEXT | | URLs and references |
| `time_invested_minutes` | INTEGER | | Research duration |
| `domain` | TEXT | | Knowledge domain |
| `tags` | TEXT | | Comma-separated tags |
| `usefulness_score` | REAL | DEFAULT 0 | Feedback score |
| `access_count` | INTEGER | DEFAULT 0 | View count |
| `created_at` | DATETIME | DEFAULT CURRENT_TIMESTAMP | Creation time |
| `updated_at` | DATETIME | | Last update |

**Full-Text Search:**
```sql
CREATE VIRTUAL TABLE spike_reports_fts USING fts4(
    spike_id, title, topic, question, findings, gotchas
);
```

---

### 3.10 ceo_reviews

**Purpose:** CEO escalation requests requiring human decision.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | Unique identifier |
| `title` | TEXT | NOT NULL | Escalation title |
| `context` | TEXT | | Background information |
| `recommendation` | TEXT | | Claude's recommendation |
| `status` | TEXT | DEFAULT 'pending' | 'pending', 'approved', 'rejected' |
| `created_at` | DATETIME | DEFAULT CURRENT_TIMESTAMP | Escalation time |
| `reviewed_at` | DATETIME | | CEO review time |

---

## 4. Workflow Tables

### 4.1 workflows

**Purpose:** Define reusable workflow templates for multi-agent orchestration.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | Unique identifier |
| `name` | TEXT | NOT NULL, UNIQUE | Workflow name |
| `description` | TEXT | | Human-readable description |
| `nodes_json` | TEXT | DEFAULT '[]' | JSON array of node definitions |
| `config_json` | TEXT | DEFAULT '{}' | Default configuration |
| `created_at` | DATETIME | DEFAULT CURRENT_TIMESTAMP | Creation time |
| `updated_at` | DATETIME | | Last update |

**nodes_json Structure:**
```json
[
  {
    "id": "analyze",
    "name": "Code Analyzer",
    "type": "single",
    "prompt_template": "Analyze the following code..."
  }
]
```

---

### 4.2 workflow_edges

**Purpose:** Define transitions between workflow nodes.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | Unique identifier |
| `workflow_id` | INTEGER | NOT NULL, FK -> workflows.id | Parent workflow |
| `from_node` | TEXT | NOT NULL | Source node ID (or '__start__') |
| `to_node` | TEXT | NOT NULL | Target node ID (or '__end__') |
| `condition` | TEXT | DEFAULT '' | Python expression for edge |
| `priority` | INTEGER | DEFAULT 100 | Lower = higher priority |
| `created_at` | DATETIME | DEFAULT CURRENT_TIMESTAMP | Creation time |

---

### 4.3 workflow_runs

**Purpose:** Track execution of workflow instances.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | Unique identifier |
| `workflow_id` | INTEGER | FK -> workflows.id | Source workflow (NULL for ad-hoc) |
| `workflow_name` | TEXT | | Denormalized for quick access |
| `status` | TEXT | NOT NULL, DEFAULT 'pending' | 'pending', 'running', 'completed', 'failed', 'cancelled' |
| `phase` | TEXT | DEFAULT 'init' | Current execution phase |
| `input_json` | TEXT | DEFAULT '{}' | Initial parameters |
| `output_json` | TEXT | DEFAULT '{}' | Final results |
| `context_json` | TEXT | DEFAULT '{}' | Shared context |
| `total_nodes` | INTEGER | DEFAULT 0 | Node count |
| `completed_nodes` | INTEGER | DEFAULT 0 | Completed count |
| `failed_nodes` | INTEGER | DEFAULT 0 | Failed count |
| `started_at` | DATETIME | | Execution start |
| `completed_at` | DATETIME | | Execution end |
| `created_at` | DATETIME | DEFAULT CURRENT_TIMESTAMP | Creation time |
| `error_message` | TEXT | | Error details if failed |

---

### 4.4 node_executions

**Purpose:** Track individual node execution within a workflow run.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | Unique identifier |
| `run_id` | INTEGER | NOT NULL, FK -> workflow_runs.id | Parent run |
| `node_id` | TEXT | NOT NULL | Node identifier |
| `node_name` | TEXT | | Human-readable name |
| `node_type` | TEXT | DEFAULT 'single' | 'single', 'parallel', 'swarm' |
| `agent_id` | TEXT | | Executing agent ID |
| `session_id` | TEXT | | Claude session ID |
| `prompt` | TEXT | | Full prompt sent |
| `prompt_hash` | TEXT | | SHA256 for deduplication |
| `status` | TEXT | DEFAULT 'pending' | 'pending', 'running', 'completed', 'failed', 'skipped' |
| `result_json` | TEXT | DEFAULT '{}' | Structured output |
| `result_text` | TEXT | | Raw text output |
| `findings_json` | TEXT | DEFAULT '[]' | Extracted findings |
| `files_modified` | TEXT | DEFAULT '[]' | Files touched |
| `duration_ms` | INTEGER | | Execution time |
| `token_count` | INTEGER | | Tokens used |
| `retry_count` | INTEGER | DEFAULT 0 | Retry attempts |
| `started_at` | DATETIME | | Start time |
| `completed_at` | DATETIME | | End time |
| `created_at` | DATETIME | DEFAULT CURRENT_TIMESTAMP | Creation time |
| `error_message` | TEXT | | Error details |
| `error_type` | TEXT | | 'blocker', 'timeout', 'crash' |

---

### 4.5 trails

**Purpose:** Pheromone trails - agent breadcrumbs for swarm coordination.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | Unique identifier |
| `run_id` | INTEGER | FK -> workflow_runs.id | Parent run |
| `location` | TEXT | NOT NULL | File path, function, or concept |
| `location_type` | TEXT | DEFAULT 'file' | 'file', 'function', 'class', 'concept', 'tag' |
| `scent` | TEXT | NOT NULL | Type: 'discovery', 'warning', 'blocker', 'hot', 'cold' |
| `strength` | REAL | DEFAULT 1.0 | 0.0-1.0, decays over time |
| `agent_id` | TEXT | | Trail creator |
| `node_id` | TEXT | | Source node |
| `message` | TEXT | | Optional description |
| `tags` | TEXT | | Comma-separated tags |
| `created_at` | DATETIME | DEFAULT CURRENT_TIMESTAMP | Creation time |
| `expires_at` | DATETIME | | Expiration time |

---

### 4.6 conductor_decisions

**Purpose:** Log conductor orchestration decisions.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | Unique identifier |
| `run_id` | INTEGER | NOT NULL, FK -> workflow_runs.id | Parent run |
| `decision_type` | TEXT | NOT NULL | 'fire_node', 'skip_node', 'retry', 'abort', 'phase_change' |
| `decision_data` | TEXT | DEFAULT '{}' | JSON decision details |
| `reason` | TEXT | | Human-readable explanation |
| `created_at` | DATETIME | DEFAULT CURRENT_TIMESTAMP | Decision time |

---

## 5. Metrics & Health Tables

### 5.1 metrics

**Purpose:** Real-time metrics collection.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | Unique identifier |
| `timestamp` | DATETIME | DEFAULT CURRENT_TIMESTAMP | Measurement time |
| `metric_type` | TEXT | NOT NULL | Category (e.g., 'performance', 'usage') |
| `metric_name` | TEXT | NOT NULL | Specific metric name |
| `metric_value` | REAL | NOT NULL | Numeric value |
| `tags` | TEXT | | Additional tags |
| `context` | TEXT | | JSON context data |

**Indexes:**
- `idx_metrics_timestamp`
- `idx_metrics_type`
- `idx_metrics_name`
- `idx_metrics_type_name` - Compound for efficient querying

---

### 5.2 system_health

**Purpose:** System health snapshots for monitoring.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | Unique identifier |
| `timestamp` | DATETIME | DEFAULT CURRENT_TIMESTAMP | Check time |
| `status` | TEXT | NOT NULL | 'healthy', 'degraded', 'unhealthy' |
| `db_integrity` | TEXT | | SQLite integrity check result |
| `db_size_mb` | REAL | | Database file size |
| `disk_free_mb` | REAL | | Available disk space |
| `git_status` | TEXT | | Git repository status |
| `stale_locks` | INTEGER | DEFAULT 0 | Stale lock count |
| `details` | TEXT | | JSON with additional details |

---

### 5.3 schema_version

**Purpose:** Track database schema migrations.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `version` | INTEGER | PRIMARY KEY | Schema version number |
| `applied_at` | DATETIME | DEFAULT CURRENT_TIMESTAMP | Migration timestamp |
| `description` | TEXT | | Migration description |

---

### 5.4 db_operations

**Purpose:** Singleton table for tracking database maintenance.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY, CHECK(id = 1) | Always 1 (singleton) |
| `operation_count` | INTEGER | DEFAULT 0 | Total operations |
| `last_vacuum` | DATETIME | | Last VACUUM timestamp |
| `last_analyze` | DATETIME | | Last ANALYZE timestamp |
| `total_vacuums` | INTEGER | DEFAULT 0 | Vacuum count |
| `total_analyzes` | INTEGER | DEFAULT 0 | Analyze count |

---

## 6. Fraud Detection Tables

### 6.1 fraud_reports

**Purpose:** Track potential gaming or manipulation of confidence scores.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | Unique identifier |
| `heuristic_id` | INTEGER | NOT NULL, FK -> heuristics.id | Subject heuristic |
| `fraud_score` | REAL | NOT NULL, CHECK 0.0-1.0 | Fraud likelihood |
| `classification` | TEXT | NOT NULL | 'clean', 'low_confidence', 'suspicious', 'fraud_likely', 'fraud_confirmed' |
| `likelihood_ratio` | REAL | | Statistical confidence |
| `signal_count` | INTEGER | DEFAULT 0 | Number of signals |
| `created_at` | DATETIME | DEFAULT CURRENT_TIMESTAMP | Report time |
| `reviewed_at` | DATETIME | | Review time |
| `reviewed_by` | TEXT | | Reviewer ID |
| `review_outcome` | TEXT | | 'false_positive', 'true_positive', 'pending' |

---

### 6.2 anomaly_signals

**Purpose:** Individual fraud detection signals.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | Unique identifier |
| `fraud_report_id` | INTEGER | NOT NULL, FK | Parent report |
| `heuristic_id` | INTEGER | NOT NULL, FK | Subject heuristic |
| `detector_name` | TEXT | NOT NULL | Detecting algorithm |
| `score` | REAL | NOT NULL, CHECK 0.0-1.0 | Signal score |
| `severity` | TEXT | NOT NULL | 'low', 'medium', 'high', 'critical' |
| `reason` | TEXT | NOT NULL | Explanation |
| `evidence` | TEXT | | JSON with details |
| `created_at` | DATETIME | DEFAULT CURRENT_TIMESTAMP | Detection time |

---

### 6.3 fraud_responses

**Purpose:** Actions taken in response to fraud detection.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | Unique identifier |
| `fraud_report_id` | INTEGER | NOT NULL, FK | Parent report |
| `response_type` | TEXT | NOT NULL | Action type (see CHECK constraint) |
| `parameters` | TEXT | | JSON response params |
| `executed_at` | DATETIME | DEFAULT CURRENT_TIMESTAMP | Action time |
| `executed_by` | TEXT | DEFAULT 'system' | Actor |
| `rollback_at` | DATETIME | | Rollback time if applicable |

**Response Types:**
- `alert` - Notification only
- `confidence_freeze` - Prevent confidence changes
- `confidence_reset` - Reset to baseline
- `status_quarantine` - Mark as quarantined
- `rate_limit_tighten` - Reduce update frequency
- `ceo_escalation` - Escalate to human
- `auto_deprecate` - Automatically deprecate

---

### 6.4 confidence_updates

**Purpose:** Audit trail for all confidence score changes.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | Unique identifier |
| `heuristic_id` | INTEGER | NOT NULL, FK | Subject heuristic |
| `old_confidence` | REAL | NOT NULL | Previous value |
| `new_confidence` | REAL | NOT NULL | New value |
| `delta` | REAL | NOT NULL | Change amount |
| `update_type` | TEXT | NOT NULL | 'validation', 'violation', 'reset', etc. |
| `reason` | TEXT | | Explanation |
| `session_id` | TEXT | | Source session |
| `agent_id` | TEXT | | Source agent |
| `rate_limited` | INTEGER | DEFAULT 0 | Was rate limited |
| `raw_target_confidence` | REAL | | Before smoothing |
| `smoothed_delta` | REAL | | After EMA smoothing |
| `alpha_used` | REAL | | EMA alpha value |
| `created_at` | DATETIME | DEFAULT CURRENT_TIMESTAMP | Update time |

---

## 7. Domain Lifecycle Tables

### 7.1 domain_metadata

**Purpose:** Per-domain configuration and capacity management.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `domain` | TEXT | PRIMARY KEY | Domain name |
| `soft_limit` | INTEGER | NOT NULL, DEFAULT 5, CHECK > 0 | Warning threshold |
| `hard_limit` | INTEGER | NOT NULL, DEFAULT 10, CHECK >= soft_limit | Maximum heuristics |
| `ceo_override_limit` | INTEGER | | CEO can override hard limit |
| `current_count` | INTEGER | NOT NULL, DEFAULT 0 | Current heuristic count |
| `state` | TEXT | NOT NULL, DEFAULT 'normal' | 'normal', 'overflow', 'critical' |
| `overflow_entered_at` | DATETIME | | When overflow started |
| `expansion_min_confidence` | REAL | DEFAULT 0.70 | Min confidence for expansion |
| `expansion_min_validations` | INTEGER | DEFAULT 3 | Min validations for expansion |
| `expansion_min_novelty` | REAL | DEFAULT 0.60 | Min novelty score |
| `grace_period_days` | INTEGER | DEFAULT 7 | Grace period for overflow |
| `max_overflow_days` | INTEGER | DEFAULT 28 | Max days in overflow |
| `avg_confidence` | REAL | | Cached average confidence |
| `health_score` | REAL | | Cached health score |
| `last_health_check` | DATETIME | | Last health calculation |
| `created_at` | DATETIME | DEFAULT CURRENT_TIMESTAMP | Creation time |
| `updated_at` | DATETIME | | Last update |

---

### 7.2 domain_baselines

**Purpose:** Statistical baselines for anomaly detection.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `domain` | TEXT | PRIMARY KEY | Domain name |
| `avg_success_rate` | REAL | | Mean success rate |
| `std_success_rate` | REAL | | Standard deviation |
| `avg_update_frequency` | REAL | | Updates per day |
| `std_update_frequency` | REAL | | Std dev of frequency |
| `sample_count` | INTEGER | DEFAULT 0 | Sample size |
| `last_updated` | DATETIME | DEFAULT CURRENT_TIMESTAMP | Last baseline update |

---

### 7.3 expansion_events

**Purpose:** Log domain expansion and contraction events.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | Unique identifier |
| `domain` | TEXT | NOT NULL | Domain name |
| `heuristic_id` | INTEGER | FK | Related heuristic (NULL for contraction) |
| `event_type` | TEXT | NOT NULL | 'expansion', 'contraction', 'merge' |
| `count_before` | INTEGER | NOT NULL | Count before event |
| `count_after` | INTEGER | NOT NULL | Count after event |
| `quality_score` | REAL | | Quality at time of event |
| `novelty_score` | REAL | | Novelty at time of event |
| `health_score` | REAL | | Health at time of event |
| `reason` | TEXT | | Justification |
| `created_at` | DATETIME | DEFAULT CURRENT_TIMESTAMP | Event time |

---

### 7.4 heuristic_merges

**Purpose:** Track heuristic merge operations during contraction.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | Unique identifier |
| `source_ids` | TEXT | NOT NULL | JSON array of merged IDs |
| `target_id` | INTEGER | NOT NULL, FK | Resulting heuristic |
| `merge_reason` | TEXT | | 'overflow_contraction', 'manual', 'similarity_detected' |
| `merge_strategy` | TEXT | | 'weighted_average', 'sum', 'manual' |
| `similarity_score` | REAL | | Semantic similarity |
| `merged_at` | DATETIME | DEFAULT CURRENT_TIMESTAMP | Merge time |

---

## 8. Session & Query Tables

### 8.1 session_summaries

**Purpose:** AI-generated summaries of Claude sessions.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | Unique identifier |
| `session_id` | TEXT | NOT NULL, UNIQUE | Session UUID |
| `project` | TEXT | NOT NULL | Project name |
| `tool_summary` | TEXT | | "Read 5 files, edited 3..." |
| `content_summary` | TEXT | | What was done |
| `conversation_summary` | TEXT | | Conversation overview |
| `files_touched` | TEXT | DEFAULT '[]' | JSON array of paths |
| `tool_counts` | TEXT | DEFAULT '{}' | JSON tool usage counts |
| `message_count` | INTEGER | DEFAULT 0 | Message count |
| `session_file_path` | TEXT | | Path to .jsonl file |
| `session_file_size` | INTEGER | | File size in bytes |
| `session_last_modified` | DATETIME | | File modification time |
| `summarized_at` | DATETIME | DEFAULT CURRENT_TIMESTAMP | Summary time |
| `summarizer_model` | TEXT | DEFAULT 'haiku' | Model used |
| `summary_version` | INTEGER | DEFAULT 1 | Format version |
| `is_stale` | INTEGER | DEFAULT 0 | Needs update flag |
| `needs_resummarize` | INTEGER | DEFAULT 0 | Resummary flag |

---

### 8.2 building_queries

**Purpose:** Log all queries to the ELF framework.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | Unique identifier |
| `query_type` | TEXT | NOT NULL | Query type |
| `session_id` | TEXT | | Source session |
| `agent_id` | TEXT | | Source agent |
| `domain` | TEXT | | Domain filter |
| `tags` | TEXT | | Tag filter |
| `limit_requested` | INTEGER | DEFAULT 10 | Result limit |
| `max_tokens_requested` | INTEGER | | Token limit |
| `results_returned` | INTEGER | DEFAULT 0 | Actual results |
| `tokens_approximated` | INTEGER | | Token estimate |
| `duration_ms` | INTEGER | | Query time |
| `status` | TEXT | DEFAULT 'success' | 'success', 'error' |
| `error_message` | TEXT | | Error details |
| `error_code` | TEXT | | Error code |
| `golden_rules_returned` | INTEGER | DEFAULT 0 | Golden rule count |
| `heuristics_count` | INTEGER | DEFAULT 0 | Heuristic count |
| `learnings_count` | INTEGER | DEFAULT 0 | Learning count |
| `experiments_count` | INTEGER | DEFAULT 0 | Experiment count |
| `ceo_reviews_count` | INTEGER | DEFAULT 0 | CEO review count |
| `query_summary` | TEXT | | Query summary |
| `created_at` | DATETIME | DEFAULT CURRENT_TIMESTAMP | Query time |
| `completed_at` | DATETIME | | Completion time |

---

### 8.3 session_contexts

**Purpose:** Track context hashes for privacy-preserving analytics.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | Unique identifier |
| `session_id` | TEXT | NOT NULL | Session ID |
| `agent_id` | TEXT | | Agent ID |
| `context_hash` | TEXT | NOT NULL | SHA256 hash |
| `context_preview` | TEXT | | First 100 chars |
| `heuristics_applied` | TEXT | | JSON array of IDs |
| `created_at` | DATETIME | DEFAULT CURRENT_TIMESTAMP | Creation time |

---

## 9. Meta-Observer Tables

### 9.1 meta_observer_config

**Purpose:** Configuration for the meta-observer system.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | Unique identifier |
| `metric_name` | TEXT | UNIQUE NOT NULL | Metric being monitored |
| `threshold` | REAL | | Alert threshold |
| `auto_adjust` | INTEGER | DEFAULT 0 | LOCKED to 0 per CEO |
| `trend_window_hours` | INTEGER | DEFAULT 168 | 7-day trend window |
| `trend_sensitivity` | REAL | DEFAULT 0.05 | Slope threshold |
| `baseline_window_hours` | INTEGER | DEFAULT 720 | 30-day baseline |
| `z_score_threshold` | REAL | DEFAULT 3.0 | Anomaly threshold |
| `false_positive_count` | INTEGER | DEFAULT 0 | FP tracking |
| `true_positive_count` | INTEGER | DEFAULT 0 | TP tracking |
| `created_at` | DATETIME | DEFAULT CURRENT_TIMESTAMP | Creation time |
| `updated_at` | DATETIME | | Last update |

---

### 9.2 meta_alerts

**Purpose:** Alerts generated by the meta-observer.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | Unique identifier |
| `alert_type` | TEXT | NOT NULL | Alert category |
| `severity` | TEXT | NOT NULL | 'info', 'warning', 'critical' |
| `state` | TEXT | NOT NULL, DEFAULT 'new' | 'new', 'active', 'ack', 'resolved' |
| `metric_name` | TEXT | | Related metric |
| `current_value` | REAL | | Current value |
| `baseline_value` | REAL | | Expected value |
| `message` | TEXT | NOT NULL | Alert message |
| `context` | TEXT | | JSON with trend data |
| `first_seen` | DATETIME | DEFAULT CURRENT_TIMESTAMP | First occurrence |
| `last_seen` | DATETIME | DEFAULT CURRENT_TIMESTAMP | Last occurrence |
| `acknowledged_at` | DATETIME | | Acknowledgment time |
| `resolved_at` | DATETIME | | Resolution time |
| `created_by` | TEXT | DEFAULT 'meta_observer' | Source |

---

## 10. Planning Tables

### 10.1 plans

**Purpose:** Track planned tasks and approaches.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | Unique identifier |
| `task_id` | TEXT | UNIQUE | Slug for linking |
| `title` | TEXT | NOT NULL | Task title |
| `description` | TEXT | | What we're accomplishing |
| `approach` | TEXT | | How we plan to do it |
| `risks` | TEXT | | Identified risks |
| `expected_outcome` | TEXT | | Success criteria |
| `domain` | TEXT | | Domain category |
| `status` | TEXT | DEFAULT 'active' | 'active', 'completed', 'abandoned' |
| `created_at` | DATETIME | DEFAULT CURRENT_TIMESTAMP | Creation time |
| `completed_at` | DATETIME | | Completion time |

---

### 10.2 postmortems

**Purpose:** Post-task analysis and lessons learned.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | Unique identifier |
| `plan_id` | INTEGER | FK -> plans.id | Related plan (optional) |
| `title` | TEXT | NOT NULL | Description |
| `actual_outcome` | TEXT | | What actually happened |
| `divergences` | TEXT | | Plan vs reality |
| `went_well` | TEXT | | Successes |
| `went_wrong` | TEXT | | Failures |
| `lessons` | TEXT | | Key takeaways |
| `heuristics_extracted` | TEXT | | JSON array of heuristic IDs |
| `domain` | TEXT | | Domain category |
| `created_at` | DATETIME | DEFAULT CURRENT_TIMESTAMP | Creation time |

---

## 11. Game Tables (Dashboard)

### 11.1 users

**Purpose:** OAuth user accounts for dashboard.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | Unique identifier |
| `github_id` | INTEGER | UNIQUE | GitHub user ID |
| `username` | TEXT | NOT NULL | Display name |
| `avatar_url` | TEXT | | Profile image URL |
| `created_at` | DATETIME | DEFAULT CURRENT_TIMESTAMP | Registration time |

---

### 11.2 game_state

**Purpose:** Gamification state for dashboard users.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `user_id` | INTEGER | PRIMARY KEY, FK -> users.id | User ID |
| `score` | INTEGER | DEFAULT 0 | Current score |
| `unlocked_weapons` | TEXT | DEFAULT '["pulse_laser"]' | JSON array |
| `unlocked_cursors` | TEXT | DEFAULT '["default"]' | JSON array |
| `active_weapon` | TEXT | DEFAULT 'pulse_laser' | Current weapon |

---

## 12. Migration Notes

### Adding New Tables

1. **Define in ORM (models.py)**:
```python
class NewTable(BaseModel):
    id = fields.AutoField()
    name = fields.TextField(null=False)
    created_at = fields.DateTimeField(default=datetime.utcnow)

    class Meta:
        table_name = 'new_table'
        indexes = (
            (('name',), False),
        )
```

2. **Register in _register_all_models()**:
```python
models_to_register = [
    # ... existing models
    NewTable,
]
```

3. **Add to create_tables()**:
```python
for model in [
    # ... existing models
    NewTable,
]:
    await model.create_table(safe=True)
```

4. **Add sync creation in database.py** if needed for dashboard:
```python
cursor.execute("""
    CREATE TABLE IF NOT EXISTS new_table (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
""")
```

### Adding New Columns

1. **Update ORM model** with new field
2. **Create migration SQL**:
```sql
-- Check if column exists first
SELECT * FROM pragma_table_info('table_name') WHERE name='new_column';

-- Add column if not exists
ALTER TABLE table_name ADD COLUMN new_column TEXT;
```

3. **Update schema_version**:
```sql
INSERT INTO schema_version (version, description)
VALUES (X, 'Add new_column to table_name');
```

### Schema Version Tracking

```python
CURRENT_SCHEMA_VERSION = 15

async def migrate_schema():
    current = await SchemaVersion.select().order_by(SchemaVersion.version.desc()).first()
    if current is None or current.version < CURRENT_SCHEMA_VERSION:
        # Run migrations
        await apply_migrations(current.version if current else 0)
```

### Index Best Practices

1. **Always index foreign keys** - Speeds up JOINs
2. **Index columns used in WHERE** - Filter optimization
3. **Create compound indexes** for multi-column queries
4. **Use partial indexes** for filtered queries:
```sql
CREATE INDEX idx_active_heuristics ON heuristics(domain)
WHERE status = 'active';
```

5. **Monitor index usage** with:
```sql
SELECT * FROM sqlite_stat1;
```

---

## 13. Query Patterns

### Common Query Examples

**Get top heuristics by domain:**
```sql
SELECT * FROM heuristics
WHERE domain = ?
  AND status = 'active'
ORDER BY confidence DESC
LIMIT 10;
```

**Find violations in last 7 days:**
```sql
SELECT * FROM violations
WHERE violation_date >= datetime('now', '-7 days')
  AND acknowledged = 0
ORDER BY violation_date DESC;
```

**Aggregate workflow success rates:**
```sql
SELECT
    workflow_name,
    COUNT(*) as total_runs,
    SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as successful,
    ROUND(100.0 * SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) / COUNT(*), 2) as success_rate
FROM workflow_runs
GROUP BY workflow_name;
```

**Find similar heuristics (for merge candidates):**
```sql
SELECT h1.id, h1.rule, h2.id, h2.rule
FROM heuristics h1
JOIN heuristics h2 ON h1.domain = h2.domain AND h1.id < h2.id
WHERE h1.status = 'active' AND h2.status = 'active';
```

---

## 14. Backup & Recovery

### Backup Command
```bash
sqlite3 ~/.claude/emergent-learning/memory/index.db ".backup 'backup.db'"
```

### Integrity Check
```bash
sqlite3 ~/.claude/emergent-learning/memory/index.db "PRAGMA integrity_check;"
```

### Vacuum (Reclaim Space)
```bash
sqlite3 ~/.claude/emergent-learning/memory/index.db "VACUUM;"
```

### Statistics Update
```bash
sqlite3 ~/.claude/emergent-learning/memory/index.db "ANALYZE;"
```

---

*Document generated from schema inspection of production database.*
