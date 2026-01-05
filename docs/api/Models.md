# Data Models API Reference

Complete reference for all database models in the Emergent Learning Framework.

## Table of Contents

- [Database Configuration](#database-configuration)
- [Core Learning Models](#core-learning-models)
  - [Learning](#learning)
  - [Heuristic](#heuristic)
  - [Experiment](#experiment)
  - [CeoReview](#ceoreview)
  - [Cycle](#cycle)
  - [Decision](#decision)
  - [Invariant](#invariant)
  - [Violation](#violation)
  - [SpikeReport](#spikereport)
  - [Assumption](#assumption)
- [Metrics & Health Models](#metrics--health-models)
  - [Metric](#metric)
  - [SystemHealth](#systemhealth)
  - [SchemaVersion](#schemaversion)
  - [DbOperations](#dboperations)
- [Workflow Models](#workflow-models)
  - [Workflow](#workflow)
  - [WorkflowEdge](#workflowedge)
  - [WorkflowRun](#workflowrun)
  - [NodeExecution](#nodeexecution)
  - [Trail](#trail)
  - [ConductorDecision](#conductordecision)
- [Query & Session Models](#query--session-models)
  - [BuildingQuery](#buildingquery)
  - [SessionSummary](#sessionsummary)

---

## Database Configuration

The framework uses **peewee-aio** for async ORM with SQLite backend.

### initialize_database()

Initialize async database connection.

**Since:** v2.0.0

```python
async def initialize_database(db_path: Optional[str] = None) -> Manager
```

**Parameters:**
- `db_path` (Optional[str]): Path to SQLite database file. Defaults to `$ELF_BASE_PATH/memory/index.db`.

**Returns:** Configured `Manager` instance

**Example:**

```python
from query.models import initialize_database, get_manager

# Initialize with default path
await initialize_database()

# Or with custom path
await initialize_database("/custom/path/index.db")

# Get manager for queries
manager = get_manager()
```

### get_manager()

Get the current manager instance.

```python
def get_manager() -> Manager
```

**Returns:** Current `Manager` instance

**Raises:** `RuntimeError` if database not initialized

### create_tables()

Create all database tables if they don't exist.

**Since:** v2.0.0

```python
async def create_tables() -> None
```

**Example:**

```python
from query.models import initialize_database, create_tables

await initialize_database()
await create_tables()
```

### Usage Pattern

All models support async operations using `peewee-aio`:

```python
from query.models import get_manager, Heuristic

manager = get_manager()
async with manager:
    async with manager.connection():
        # Create
        h = await Heuristic.create(
            domain="debugging",
            rule="Always check logs first",
            explanation="Logs reveal the actual error",
            confidence=0.8
        )

        # Query
        async for heuristic in Heuristic.select().where(Heuristic.is_golden == True):
            print(heuristic.rule)

        # Update
        h.confidence = 0.9
        await h.aio_save()

        # Delete
        await h.aio_delete()
```

---

## Core Learning Models

### Learning

Core learning records capturing failures, successes, observations, etc.

**Table:** `learnings`

**Fields:**

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | AutoField | Primary Key | Auto-incrementing ID |
| type | TextField | NOT NULL, CHECK | Type of learning. One of: `"failure"`, `"success"`, `"heuristic"`, `"experiment"`, `"observation"` |
| filepath | TextField | NOT NULL | Path to the markdown file |
| title | TextField | NOT NULL | Title of the learning |
| summary | TextField | Nullable | Brief summary |
| tags | TextField | Nullable | Comma-separated tags |
| domain | TextField | Nullable, Indexed | Domain (e.g., "debugging", "security") |
| severity | Integer | Default: 3, CHECK | Severity level (1-5, where 5 is most severe) |
| created_at | DateTime | Default: utcnow, Indexed | Creation timestamp |
| updated_at | DateTime | Default: utcnow | Last update timestamp |

**Indexes:**
- `domain` (single column)
- `type` (single column)
- `tags` (single column)
- `created_at` (single column)
- `(domain, created_at)` (composite)

**Valid Types:**

```python
Learning.VALID_TYPES = ('failure', 'success', 'heuristic', 'experiment', 'observation')
```

**Example:**

```python
from query.models import Learning, get_manager

manager = get_manager()
async with manager:
    async with manager.connection():
        # Create a failure learning
        learning = await Learning.create(
            type='failure',
            filepath='failure-analysis/2025-01-05-auth-bug.md',
            title='OAuth2 token refresh race condition',
            summary='Token refresh fails when concurrent requests occur',
            tags='oauth,race-condition,authentication',
            domain='security',
            severity=4
        )

        # Query recent failures
        recent_failures = []
        async for l in Learning.select().where(Learning.type == 'failure').order_by(Learning.created_at.desc()).limit(10):
            recent_failures.append(l)
```

---

### Heuristic

Extracted heuristics (learned patterns and rules).

**Table:** `heuristics`

**Fields:**

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | AutoField | Primary Key | Auto-incrementing ID |
| domain | TextField | NOT NULL, Indexed | Domain (e.g., "git", "testing") |
| rule | TextField | NOT NULL | The heuristic rule statement |
| explanation | TextField | Nullable | Why this rule works |
| source_type | TextField | Nullable | Type of source (e.g., "learning", "manual") |
| source_id | Integer | Nullable | ID of source record |
| confidence | Float | Default: 0.5, CHECK | Confidence score (0.0 to 1.0) |
| times_validated | Integer | Default: 0, CHECK | Number of times validated |
| times_violated | Integer | Default: 0, CHECK | Number of times violated |
| is_golden | Boolean | Default: False, Indexed | Is this a golden rule? |
| project_path | TextField | Nullable, Default: NULL, Indexed | Project location (NULL = global) |
| created_at | DateTime | Default: utcnow, Indexed | Creation timestamp |
| updated_at | DateTime | Default: utcnow | Last update timestamp |

**Indexes:**
- `domain` (single column)
- `is_golden` (single column)
- `confidence` (single column)
- `created_at` (single column)
- `(domain, confidence)` (composite)
- `project_path` (single column)

**Location-Aware Heuristics:**

- `project_path = NULL`: Global heuristic (applies everywhere)
- `project_path = "/path/to/project"`: Project-specific heuristic

**Example:**

```python
from query.models import Heuristic, get_manager

manager = get_manager()
async with manager:
    async with manager.connection():
        # Create a global heuristic
        h = await Heuristic.create(
            domain="git",
            rule="Never force push to main branch",
            explanation="Force push overwrites history and breaks team workflow",
            confidence=0.95,
            times_validated=50,
            is_golden=True,
            project_path=None  # Global
        )

        # Create a project-specific heuristic
        project_h = await Heuristic.create(
            domain="react",
            rule="Use custom hook useAuth for all authentication",
            explanation="Centralizes auth logic in this project",
            confidence=0.8,
            project_path="/workspace/my-app"
        )

        # Query golden rules
        golden_rules = []
        async for h in Heuristic.select().where(Heuristic.is_golden == True):
            golden_rules.append(h)
```

---

### Experiment

Active experiments tracking.

**Table:** `experiments`

**Fields:**

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | AutoField | Primary Key | Auto-incrementing ID |
| name | TextField | NOT NULL, UNIQUE | Experiment name |
| hypothesis | TextField | Nullable | What we're testing |
| status | TextField | Default: 'active', Indexed | Status (e.g., "active", "completed") |
| cycles_run | Integer | Default: 0 | Number of TRY-BREAK-ANALYZE cycles |
| folder_path | TextField | Nullable | Path to experiment folder |
| created_at | DateTime | Default: utcnow | Creation timestamp |
| updated_at | DateTime | Default: utcnow | Last update timestamp |

**Indexes:**
- `status` (single column)

**Example:**

```python
from query.models import Experiment

# Create experiment
exp = await Experiment.create(
    name="TDD-workflow-optimization",
    hypothesis="Test-driven development reduces debugging time by 40%",
    status="active",
    cycles_run=0,
    folder_path="experiments/tdd-workflow"
)

# Update cycle count
exp.cycles_run += 1
await exp.aio_save()
```

---

### CeoReview

CEO escalation requests for decisions beyond agent scope.

**Table:** `ceo_reviews`

**Fields:**

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | AutoField | Primary Key | Auto-incrementing ID |
| title | TextField | NOT NULL | Title of the escalation |
| context | TextField | Nullable | Context and background |
| recommendation | TextField | Nullable | Agent's recommendation |
| status | TextField | Default: 'pending', Indexed | Status (pending, approved, rejected) |
| created_at | DateTime | Default: utcnow | Creation timestamp |
| reviewed_at | DateTime | Nullable | When CEO reviewed it |

**Indexes:**
- `status` (single column)

**Example:**

```python
from query.models import CeoReview

# Create escalation
review = await CeoReview.create(
    title="Conflicting golden rules for error handling",
    context="Rule 5 says 'fail fast' but Rule 12 says 'graceful degradation'",
    recommendation="Merge rules: fail fast in dev, graceful in production",
    status="pending"
)
```

---

### Cycle

Experiment cycles (TRY-BREAK-ANALYZE-LEARN iterations).

**Table:** `cycles`

**Fields:**

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | AutoField | Primary Key | Auto-incrementing ID |
| experiment | ForeignKey | Nullable, ON DELETE SET NULL | Reference to Experiment |
| cycle_number | Integer | Nullable | Cycle number in experiment |
| try_summary | TextField | Nullable | What was tried |
| break_summary | TextField | Nullable | What broke |
| analysis | TextField | Nullable | Why it broke |
| learning_extracted | TextField | Nullable | What was learned |
| heuristic | ForeignKey | Nullable, ON DELETE SET NULL | Reference to extracted Heuristic |
| created_at | DateTime | Default: utcnow | Creation timestamp |

**Example:**

```python
from query.models import Cycle, Experiment, Heuristic

# Get experiment
exp = await Experiment.aio_get(Experiment.name == "TDD-workflow-optimization")

# Record cycle
cycle = await Cycle.create(
    experiment=exp,
    cycle_number=1,
    try_summary="Write tests first, then implement feature",
    break_summary="Tests passed but production bug occurred",
    analysis="Integration tests were missing edge case",
    learning_extracted="Unit tests alone insufficient for API endpoints"
)
```

---

### Decision

Architecture Decision Records (ADRs).

**Table:** `decisions`

**Fields:**

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | AutoField | Primary Key | Auto-incrementing ID |
| title | TextField | NOT NULL | Decision title |
| context | TextField | NOT NULL | Problem/situation requiring decision |
| options_considered | TextField | Nullable | Alternative options evaluated |
| decision | TextField | NOT NULL | The decision made |
| rationale | TextField | NOT NULL | Why this decision |
| files_touched | TextField | Nullable | Files modified by this decision |
| tests_added | TextField | Nullable | Tests added for this decision |
| status | TextField | Default: 'accepted', Indexed | Status (accepted, proposed, deprecated, superseded) |
| domain | TextField | Nullable, Indexed | Domain |
| superseded_by | ForeignKey | Nullable, ON DELETE SET NULL | Reference to newer Decision |
| created_at | DateTime | Default: utcnow, Indexed | Creation timestamp |
| updated_at | DateTime | Default: utcnow | Last update timestamp |

**Indexes:**
- `domain` (single column)
- `status` (single column)
- `created_at` (single column)
- `superseded_by` (single column)

**Example:**

```python
from query.models import Decision

# Record architectural decision
decision = await Decision.create(
    title="Use JWT for authentication",
    context="Need stateless authentication for microservices",
    options_considered="Session cookies, OAuth2, API keys, JWT",
    decision="Implement JWT with RS256 signing",
    rationale="Stateless, supports distributed systems, industry standard",
    files_touched="src/auth/jwt.py, src/middleware/auth.py",
    tests_added="tests/test_jwt_auth.py",
    status="accepted",
    domain="security"
)
```

---

### Invariant

Invariants - statements about what must ALWAYS be true.

**Table:** `invariants`

**Fields:**

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | AutoField | Primary Key | Auto-incrementing ID |
| statement | TextField | NOT NULL | The invariant statement |
| rationale | TextField | NOT NULL | Why this must be true |
| domain | TextField | Nullable, Indexed | Domain |
| scope | TextField | Default: 'codebase' | Scope (codebase, module, function, runtime) |
| validation_type | TextField | Nullable | How to validate (manual, automated, test) |
| validation_code | TextField | Nullable | Code/script to validate |
| severity | TextField | Default: 'error', Indexed | Severity (error, warning, info) |
| status | TextField | Default: 'active', Indexed | Status (active, deprecated, violated) |
| violation_count | Integer | Default: 0 | Number of violations detected |
| last_validated_at | DateTime | Nullable | Last validation timestamp |
| last_violated_at | DateTime | Nullable | Last violation timestamp |
| created_at | DateTime | Default: utcnow | Creation timestamp |
| updated_at | DateTime | Default: utcnow | Last update timestamp |

**Indexes:**
- `domain` (single column)
- `status` (single column)
- `severity` (single column)

**Example:**

```python
from query.models import Invariant

# Define invariant
inv = await Invariant.create(
    statement="All API endpoints must have authentication middleware",
    rationale="Prevents unauthorized access and data breaches",
    domain="security",
    scope="codebase",
    validation_type="automated",
    validation_code="scripts/validate_auth.py",
    severity="error",
    status="active"
)
```

---

### Violation

Golden rule violations (accountability tracking).

**Table:** `violations`

**Fields:**

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | AutoField | Primary Key | Auto-incrementing ID |
| rule_id | Integer | NOT NULL, Indexed | ID of violated rule |
| rule_name | TextField | NOT NULL | Name of violated rule |
| violation_date | DateTime | Default: utcnow, Indexed | When violation occurred |
| description | TextField | Nullable | Description of violation |
| session_id | TextField | Nullable | Session ID where it occurred |
| acknowledged | Boolean | Default: False, Indexed | Has user acknowledged? |

**Indexes:**
- `violation_date` (single column)
- `rule_id` (single column)
- `acknowledged` (single column)

**Example:**

```python
from query.models import Violation

# Record violation
v = await Violation.create(
    rule_id=5,
    rule_name="Never commit directly to main",
    violation_date=datetime.utcnow(),
    description="Emergency hotfix committed directly to main branch",
    session_id="session_2025_01_05_urgent",
    acknowledged=False
)
```

---

### SpikeReport

Time-boxed research investigations.

**Table:** `spike_reports`

**Fields:**

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | AutoField | Primary Key | Auto-incrementing ID |
| title | TextField | NOT NULL | Spike title |
| topic | TextField | Nullable, Indexed | Research topic |
| question | TextField | Nullable | Question being investigated |
| findings | TextField | Nullable | What was discovered |
| gotchas | TextField | Nullable | Pitfalls and warnings |
| resources | TextField | Nullable | Useful links/docs |
| time_invested_minutes | Integer | Nullable | Time spent on research |
| domain | TextField | Nullable, Indexed | Domain |
| tags | TextField | Nullable | Comma-separated tags |
| usefulness_score | Float | Default: 0, Indexed | Usefulness rating (0-5) |
| access_count | Integer | Default: 0 | Times accessed |
| created_at | DateTime | Default: utcnow, Indexed | Creation timestamp |
| updated_at | DateTime | Default: utcnow | Last update timestamp |

**Indexes:**
- `domain` (single column)
- `topic` (single column)
- `created_at` (single column)
- `usefulness_score` (single column)

**Example:**

```python
from query.models import SpikeReport

# Record research spike
spike = await SpikeReport.create(
    title="GraphQL N+1 Query Problem",
    topic="GraphQL performance",
    question="How to solve N+1 queries in GraphQL resolvers?",
    findings="Use DataLoader pattern to batch database queries",
    gotchas="Must create new DataLoader instance per request, not globally",
    resources="https://github.com/graphql/dataloader",
    time_invested_minutes=120,
    domain="performance",
    tags="graphql,optimization,database",
    usefulness_score=4.5
)
```

---

### Assumption

Hypotheses to verify or challenge.

**Table:** `assumptions`

**Fields:**

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | AutoField | Primary Key | Auto-incrementing ID |
| assumption | TextField | NOT NULL | The assumption statement |
| context | TextField | Nullable | Context where assumption applies |
| source | TextField | Nullable | Source of assumption |
| confidence | Float | Default: 0.5, CHECK, Indexed | Confidence (0.0 to 1.0) |
| status | TextField | Default: 'active', CHECK, Indexed | Status (active, verified, challenged, invalidated) |
| domain | TextField | Nullable, Indexed | Domain |
| verified_count | Integer | Default: 0 | Times verified |
| challenged_count | Integer | Default: 0 | Times challenged |
| last_verified_at | DateTime | Nullable | Last verification timestamp |
| created_at | DateTime | Default: utcnow, Indexed | Creation timestamp |
| updated_at | DateTime | Default: utcnow | Last update timestamp |

**Valid Statuses:**

```python
Assumption.VALID_STATUSES = ('active', 'verified', 'challenged', 'invalidated')
```

**Indexes:**
- `domain` (single column)
- `status` (single column)
- `confidence` (single column)
- `created_at` (single column)

**Example:**

```python
from query.models import Assumption

# Record assumption
assumption = await Assumption.create(
    assumption="React hooks must be called in same order on every render",
    context="React rendering behavior",
    source="React documentation",
    confidence=0.9,
    status="verified",
    domain="react",
    verified_count=25
)

# Challenge assumption
assumption.status = "challenged"
assumption.challenged_count += 1
assumption.confidence = 0.6
await assumption.aio_save()
```

---

## Metrics & Health Models

### Metric

Real-time metrics for system monitoring.

**Table:** `metrics`

**Fields:**

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | AutoField | Primary Key | Auto-incrementing ID |
| timestamp | DateTime | Default: utcnow, Indexed | When metric was recorded |
| metric_type | TextField | NOT NULL, Indexed | Type (e.g., "query", "validation") |
| metric_name | TextField | NOT NULL, Indexed | Metric name |
| metric_value | Float | NOT NULL | Metric value |
| tags | TextField | Nullable | Comma-separated tags |
| context | TextField | Nullable | Additional context JSON |

**Indexes:**
- `timestamp` (single column)
- `metric_type` (single column)
- `metric_name` (single column)
- `(metric_type, metric_name, timestamp)` (composite)

**Example:**

```python
from query.models import Metric

# Record metric
m = await Metric.create(
    metric_type="query",
    metric_name="avg_confidence",
    metric_value=0.78,
    tags="domain:debugging",
    context='{"heuristic_count": 25}'
)
```

---

### SystemHealth

System health snapshots.

**Table:** `system_health`

**Fields:**

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | AutoField | Primary Key | Auto-incrementing ID |
| timestamp | DateTime | Default: utcnow, Indexed | Snapshot timestamp |
| status | TextField | NOT NULL, Indexed | Overall status (healthy, degraded, critical) |
| db_integrity | TextField | Nullable | Database integrity check result |
| db_size_mb | Float | Nullable | Database size in MB |
| disk_free_mb | Float | Nullable | Free disk space in MB |
| git_status | TextField | Nullable | Git repository status |
| stale_locks | Integer | Default: 0 | Number of stale locks |
| details | TextField | Nullable | Additional details JSON |

**Indexes:**
- `timestamp` (single column)
- `status` (single column)

---

### SchemaVersion

Schema version tracking for migrations.

**Table:** `schema_version`

**Fields:**

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| version | Integer | PRIMARY KEY | Schema version number |
| applied_at | DateTime | Default: utcnow | When migration applied |
| description | TextField | Nullable | Migration description |

---

### DbOperations

Database operation tracking (singleton record).

**Table:** `db_operations`

**Fields:**

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | Integer | PRIMARY KEY, CHECK (id = 1) | Always 1 (singleton) |
| operation_count | Integer | Default: 0 | Total operations count |
| last_vacuum | DateTime | Nullable | Last VACUUM timestamp |
| last_analyze | DateTime | Nullable | Last ANALYZE timestamp |
| total_vacuums | Integer | Default: 0 | Total VACUUMs performed |
| total_analyzes | Integer | Default: 0 | Total ANALYZEs performed |

**Utility Functions:**

```python
async def get_or_create_db_operations() -> DbOperations
async def increment_operation_count() -> int
```

---

## Workflow Models

Models for conductor/swarm orchestration.

### Workflow

Workflow definitions.

**Table:** `workflows`

**Fields:**

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | AutoField | Primary Key | Auto-incrementing ID |
| name | TextField | NOT NULL, UNIQUE, Indexed | Workflow name |
| description | TextField | Nullable | Workflow description |
| nodes_json | TextField | Default: '[]' | JSON array of node definitions |
| config_json | TextField | Default: '{}' | JSON configuration object |
| created_at | DateTime | Default: utcnow | Creation timestamp |
| updated_at | DateTime | Default: utcnow | Last update timestamp |

---

### WorkflowEdge

Workflow edges (transitions between nodes).

**Table:** `workflow_edges`

**Fields:**

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | AutoField | Primary Key | Auto-incrementing ID |
| workflow | ForeignKey | NOT NULL, ON DELETE CASCADE, Indexed | Reference to Workflow |
| from_node | TextField | NOT NULL, Indexed | Source node ID |
| to_node | TextField | NOT NULL, Indexed | Target node ID |
| condition | TextField | Default: '' | Transition condition |
| priority | Integer | Default: 100 | Edge priority |
| created_at | DateTime | Default: utcnow | Creation timestamp |

---

### WorkflowRun

Workflow execution runs.

**Table:** `workflow_runs`

**Fields:**

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | AutoField | Primary Key | Auto-incrementing ID |
| workflow | ForeignKey | Nullable, ON DELETE SET NULL, Indexed | Reference to Workflow |
| workflow_name | TextField | Nullable | Workflow name (cached) |
| status | TextField | Default: 'pending', Indexed | Status (pending, running, completed, failed) |
| phase | TextField | Default: 'init' | Current phase |
| input_json | TextField | Default: '{}' | Input parameters JSON |
| output_json | TextField | Default: '{}' | Output results JSON |
| context_json | TextField | Default: '{}' | Execution context JSON |
| total_nodes | Integer | Default: 0 | Total nodes to execute |
| completed_nodes | Integer | Default: 0 | Nodes completed |
| failed_nodes | Integer | Default: 0 | Nodes failed |
| started_at | DateTime | Nullable | Run start time |
| completed_at | DateTime | Nullable | Run completion time |
| created_at | DateTime | Default: utcnow, Indexed | Creation timestamp |
| error_message | TextField | Nullable | Error message if failed |

---

### NodeExecution

Individual node executions within a workflow run.

**Table:** `node_executions`

**Fields:**

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | AutoField | Primary Key | Auto-incrementing ID |
| run | ForeignKey | NOT NULL, ON DELETE CASCADE, Indexed | Reference to WorkflowRun |
| node_id | TextField | NOT NULL, Indexed | Node identifier |
| node_name | TextField | Nullable | Human-readable node name |
| node_type | TextField | Default: 'single' | Node type (single, parallel) |
| agent_id | TextField | Nullable, Indexed | Agent ID if delegated |
| session_id | TextField | Nullable | Session ID |
| prompt | TextField | Nullable | Prompt sent to agent |
| prompt_hash | TextField | Nullable, Indexed | Hash for deduplication |
| status | TextField | Default: 'pending', Indexed | Status (pending, running, completed, failed) |
| result_json | TextField | Default: '{}' | Result data JSON |
| result_text | TextField | Nullable | Text result |
| findings_json | TextField | Default: '[]' | Findings array JSON |
| files_modified | TextField | Default: '[]' | Modified files array JSON |
| duration_ms | Integer | Nullable | Execution duration in ms |
| token_count | Integer | Nullable | Tokens used |
| retry_count | Integer | Default: 0 | Number of retries |
| started_at | DateTime | Nullable | Start time |
| completed_at | DateTime | Nullable | Completion time |
| created_at | DateTime | Default: utcnow, Indexed | Creation timestamp |
| error_message | TextField | Nullable | Error message |
| error_type | TextField | Nullable | Error type |

---

### Trail

Pheromone trails (agent breadcrumbs).

**Table:** `trails`

**Fields:**

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | AutoField | Primary Key | Auto-incrementing ID |
| run | ForeignKey | Nullable, ON DELETE SET NULL, Indexed | Reference to WorkflowRun |
| location | TextField | NOT NULL, Indexed | File/location path |
| location_type | TextField | Default: 'file' | Location type (file, url, etc.) |
| scent | TextField | NOT NULL, Indexed | Scent identifier |
| strength | Float | Default: 1.0, Indexed | Trail strength (0.0-1.0) |
| agent_id | TextField | Nullable, Indexed | Agent that left trail |
| node_id | TextField | Nullable | Node ID |
| message | TextField | Nullable | Trail message/note |
| tags | TextField | Nullable | Comma-separated tags |
| created_at | DateTime | Default: utcnow, Indexed | Creation timestamp |
| expires_at | DateTime | Nullable | Expiration timestamp |

---

### ConductorDecision

Conductor decisions log.

**Table:** `conductor_decisions`

**Fields:**

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | AutoField | Primary Key | Auto-incrementing ID |
| run | ForeignKey | NOT NULL, ON DELETE CASCADE, Indexed | Reference to WorkflowRun |
| decision_type | TextField | NOT NULL, Indexed | Decision type (route, retry, abort) |
| decision_data | TextField | Default: '{}' | Decision data JSON |
| reason | TextField | Nullable | Decision reasoning |
| created_at | DateTime | Default: utcnow | Creation timestamp |

---

## Query & Session Models

### BuildingQuery

Building query logging - tracks all queries to the framework.

**Table:** `building_queries`

**Fields:**

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | AutoField | Primary Key | Auto-incrementing ID |
| query_type | TextField | NOT NULL, Indexed | Query type (e.g., "build_context") |
| session_id | TextField | Nullable, Indexed | Session ID |
| agent_id | TextField | Nullable | Agent ID |
| domain | TextField | Nullable | Domain queried |
| tags | TextField | Nullable | Tags queried |
| limit_requested | Integer | Nullable | Limit parameter |
| max_tokens_requested | Integer | Nullable | Max tokens parameter |
| results_returned | Integer | Nullable | Number of results returned |
| tokens_approximated | Integer | Nullable | Approximate tokens used |
| duration_ms | Integer | Nullable | Query duration in ms |
| status | TextField | Default: 'success', Indexed | Status (success, error, timeout) |
| error_message | TextField | Nullable | Error message if failed |
| error_code | TextField | Nullable | Error code (e.g., QS001) |
| golden_rules_returned | Integer | Default: 0 | If golden rules included |
| heuristics_count | Integer | Default: 0 | Heuristics returned |
| learnings_count | Integer | Default: 0 | Learnings returned |
| experiments_count | Integer | Default: 0 | Experiments returned |
| ceo_reviews_count | Integer | Default: 0 | CEO reviews returned |
| query_summary | TextField | Nullable | Human-readable summary |
| created_at | DateTime | Default: utcnow, Indexed | Query start time |
| completed_at | DateTime | Nullable | Query completion time |

**Indexes:**
- `query_type` (single column)
- `session_id` (single column)
- `created_at` (single column)
- `status` (single column)

**Usage:** Automatically logged by all QuerySystem methods.

---

### SessionSummary

Haiku-generated summaries of Claude sessions.

**Table:** `session_summaries`

**Fields:**

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | AutoField | Primary Key | Auto-incrementing ID |
| session_id | TextField | NOT NULL, UNIQUE, Indexed | Session identifier |
| project | TextField | NOT NULL, Indexed | Project name |
| tool_summary | TextField | Nullable | Tool usage summary |
| content_summary | TextField | Nullable | Content summary |
| conversation_summary | TextField | Nullable | Conversation summary |
| files_touched | TextField | Default: '[]' | JSON array of files |
| tool_counts | TextField | Default: '{}' | JSON object of tool counts |
| message_count | Integer | Default: 0 | Number of messages |
| session_file_path | TextField | Nullable | Path to session file |
| session_file_size | Integer | Nullable | Session file size in bytes |
| session_last_modified | DateTime | Nullable | Session file last modified |
| summarized_at | DateTime | Default: utcnow, Indexed | Summary creation time |
| summarizer_model | TextField | Default: 'haiku' | Model used for summarization |
| summary_version | Integer | Default: 1 | Summary schema version |
| is_stale | Boolean | Default: False, Indexed | Is summary outdated? |
| needs_resummarize | Boolean | Default: False | Needs re-summarization? |

**Indexes:**
- `session_id` (single column)
- `project` (single column)
- `summarized_at` (single column)
- `is_stale` (single column)

---

## Common Patterns

### Creating Records

```python
# Simple create
record = await Model.create(field1=value1, field2=value2)

# Create with relationships
cycle = await Cycle.create(
    experiment=experiment_instance,
    cycle_number=1
)
```

### Querying Records

```python
# Get single record
record = await Model.aio_get(Model.field == value)

# Iterate over results
async for record in Model.select().where(Model.status == 'active'):
    print(record.field)

# Collect to list
results = []
async for record in Model.select().limit(10):
    results.append(record)
```

### Updating Records

```python
# Update single field
record.field = new_value
await record.aio_save()

# Update multiple fields
record.field1 = value1
record.field2 = value2
await record.aio_save()
```

### Deleting Records

```python
# Delete single record
await record.aio_delete()

# Delete query results
await Model.delete().where(Model.status == 'obsolete').aio_execute()
```

### Converting to Dict

```python
# All models inherit to_dict()
data = record.to_dict()
# Returns: dict with all field values
```

---

## See Also

- [QuerySystem API Reference](./QuerySystem.md)
- [API Overview](./index.md)
- [Database Schema](../schema.md)
