"""
Peewee ORM models for the Emergent Learning Framework.

This module defines all database models using Peewee ORM, matching the existing
SQLite schema exactly. Designed for incremental migration from raw sqlite3.

Usage:
    from models import db, initialize_database, Learning, Heuristic, ...

    # Initialize with path
    initialize_database('~/.claude/emergent-learning/memory/index.db')

    # Query examples
    recent = Heuristic.select().where(Heuristic.is_golden == True).limit(10)
    learning = Learning.get_by_id(1)
"""

from peewee import (
    SqliteDatabase,
    Model,
    AutoField,
    TextField,
    IntegerField,
    FloatField,
    DateTimeField,
    BooleanField,
    ForeignKeyField,
    Check,
    SQL,
)
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
import os

# -----------------------------------------------------------------------------
# Database Configuration
# -----------------------------------------------------------------------------

# Deferred database - bound at runtime via initialize_database()
db = SqliteDatabase(None)


def initialize_database(db_path: Optional[str] = None, pragmas: Optional[Dict] = None) -> SqliteDatabase:
    """
    Initialize the database connection.

    Args:
        db_path: Path to SQLite database file. Defaults to ~/.claude/emergent-learning/memory/index.db
        pragmas: Optional dict of SQLite pragmas to set

    Returns:
        Configured SqliteDatabase instance
    """
    if db_path is None:
        db_path = Path.home() / ".claude" / "emergent-learning" / "memory" / "index.db"
    else:
        db_path = Path(db_path).expanduser()

    # Ensure parent directory exists
    db_path.parent.mkdir(parents=True, exist_ok=True)

    # Default pragmas for performance and safety
    default_pragmas = {
        'journal_mode': 'wal',
        'cache_size': -64000,  # 64MB cache
        'foreign_keys': 1,
        'synchronous': 1,  # NORMAL - good balance of safety and speed
    }

    if pragmas:
        default_pragmas.update(pragmas)

    db.init(str(db_path), pragmas=default_pragmas)
    return db


def create_tables():
    """Create all tables if they don't exist."""
    with db:
        db.create_tables([
            Learning,
            Heuristic,
            Experiment,
            CeoReview,
            Cycle,
            Metric,
            SystemHealth,
            Violation,
            SchemaVersion,
            DbOperations,
            Workflow,
            WorkflowEdge,
            WorkflowRun,
            NodeExecution,
            Trail,
            ConductorDecision,
            BuildingQuery,
            SpikeReport,
            Assumption,
            SessionSummary,
            Decision,
            Invariant,
        ])


# -----------------------------------------------------------------------------
# Base Model
# -----------------------------------------------------------------------------

class BaseModel(Model):
    """Base model class with common configuration."""

    class Meta:
        database = db

    def to_dict(self) -> Dict[str, Any]:
        """Convert model instance to dictionary."""
        return self.__data__.copy()


# -----------------------------------------------------------------------------
# Core Learning Models
# -----------------------------------------------------------------------------

class Learning(BaseModel):
    """Core learning records (failures, successes, observations)."""

    VALID_TYPES = ('failure', 'success', 'heuristic', 'experiment', 'observation')

    id = AutoField()
    type = TextField(
        null=False,
        constraints=[Check("type IN ('failure', 'success', 'heuristic', 'experiment', 'observation')")]
    )
    filepath = TextField(null=False)
    title = TextField(null=False)
    summary = TextField(null=True)
    tags = TextField(null=True)  # Comma-separated
    domain = TextField(null=True)
    severity = IntegerField(
        default=3,
        constraints=[Check("severity >= 1 AND severity <= 5")]
    )
    created_at = DateTimeField(default=datetime.utcnow)
    updated_at = DateTimeField(default=datetime.utcnow)

    class Meta:
        table_name = 'learnings'
        indexes = (
            (('domain',), False),
            (('type',), False),
            (('tags',), False),
            (('created_at',), False),
            (('domain', 'created_at'), False),
        )


class Heuristic(BaseModel):
    """Extracted heuristics (learned patterns)."""

    id = AutoField()
    domain = TextField(null=False)
    rule = TextField(null=False)
    explanation = TextField(null=True)
    source_type = TextField(null=True)
    source_id = IntegerField(null=True)
    confidence = FloatField(
        default=0.5,
        constraints=[Check("confidence >= 0.0 AND confidence <= 1.0")]
    )
    times_validated = IntegerField(
        default=0,
        constraints=[Check("times_validated >= 0")]
    )
    times_violated = IntegerField(
        default=0,
        constraints=[Check("times_violated >= 0")]
    )
    is_golden = BooleanField(default=False)
    created_at = DateTimeField(default=datetime.utcnow)
    updated_at = DateTimeField(default=datetime.utcnow)

    class Meta:
        table_name = 'heuristics'
        indexes = (
            (('domain',), False),
            (('is_golden',), False),
            (('confidence',), False),
            (('created_at',), False),
            (('domain', 'confidence'), False),
        )


class Experiment(BaseModel):
    """Active experiments."""

    id = AutoField()
    name = TextField(null=False, unique=True)
    hypothesis = TextField(null=True)
    status = TextField(default='active')
    cycles_run = IntegerField(default=0)
    folder_path = TextField(null=True)
    created_at = DateTimeField(default=datetime.utcnow)
    updated_at = DateTimeField(default=datetime.utcnow)

    class Meta:
        table_name = 'experiments'
        indexes = (
            (('status',), False),
        )


class CeoReview(BaseModel):
    """CEO escalation requests."""

    id = AutoField()
    title = TextField(null=False)
    context = TextField(null=True)
    recommendation = TextField(null=True)
    status = TextField(default='pending')
    created_at = DateTimeField(default=datetime.utcnow)
    reviewed_at = DateTimeField(null=True)

    class Meta:
        table_name = 'ceo_reviews'
        indexes = (
            (('status',), False),
        )


class Cycle(BaseModel):
    """Experiment cycles."""

    id = AutoField()
    experiment = ForeignKeyField(Experiment, backref='cycles', null=True, on_delete='SET NULL')
    cycle_number = IntegerField(null=True)
    try_summary = TextField(null=True)
    break_summary = TextField(null=True)
    analysis = TextField(null=True)
    learning_extracted = TextField(null=True)
    heuristic = ForeignKeyField(Heuristic, backref='cycles', null=True, on_delete='SET NULL')
    created_at = DateTimeField(default=datetime.utcnow)

    class Meta:
        table_name = 'cycles'


class Decision(BaseModel):
    """Architecture Decision Records (ADRs)."""

    id = AutoField()
    title = TextField(null=False)
    context = TextField(null=False)
    options_considered = TextField(null=True)
    decision = TextField(null=False)
    rationale = TextField(null=False)
    files_touched = TextField(null=True)
    tests_added = TextField(null=True)
    status = TextField(default='accepted')
    domain = TextField(null=True)
    superseded_by = ForeignKeyField('self', backref='supersedes', null=True, on_delete='SET NULL')
    created_at = DateTimeField(default=datetime.utcnow)
    updated_at = DateTimeField(default=datetime.utcnow)

    class Meta:
        table_name = 'decisions'
        indexes = (
            (('domain',), False),
            (('status',), False),
            (('created_at',), False),
            (('superseded_by',), False),
        )


class Invariant(BaseModel):
    """Invariants - statements about what must always be true."""

    id = AutoField()
    statement = TextField(null=False)
    rationale = TextField(null=False)
    domain = TextField(null=True)
    scope = TextField(default='codebase')  # codebase, module, function, runtime
    validation_type = TextField(null=True)  # manual, automated, test
    validation_code = TextField(null=True)
    severity = TextField(default='error')  # error, warning, info
    status = TextField(default='active')
    violation_count = IntegerField(default=0)
    last_validated_at = DateTimeField(null=True)
    last_violated_at = DateTimeField(null=True)
    created_at = DateTimeField(default=datetime.utcnow)
    updated_at = DateTimeField(default=datetime.utcnow)

    class Meta:
        table_name = 'invariants'
        indexes = (
            (('domain',), False),
            (('status',), False),
            (('severity',), False),
        )


class Violation(BaseModel):
    """Golden rule violations (accountability tracking)."""

    id = AutoField()
    rule_id = IntegerField(null=False)
    rule_name = TextField(null=False)
    violation_date = DateTimeField(default=datetime.utcnow)
    description = TextField(null=True)
    session_id = TextField(null=True)
    acknowledged = BooleanField(default=False)

    class Meta:
        table_name = 'violations'
        indexes = (
            (('violation_date',), False),
            (('rule_id',), False),
            (('acknowledged',), False),
        )


class SpikeReport(BaseModel):
    """Time-boxed research investigations."""

    id = AutoField()
    title = TextField(null=False)
    topic = TextField(null=True)
    question = TextField(null=True)
    findings = TextField(null=True)
    gotchas = TextField(null=True)
    resources = TextField(null=True)
    time_invested_minutes = IntegerField(null=True)
    domain = TextField(null=True)
    tags = TextField(null=True)
    usefulness_score = FloatField(default=0)
    access_count = IntegerField(default=0)
    created_at = DateTimeField(default=datetime.utcnow)
    updated_at = DateTimeField(default=datetime.utcnow)

    class Meta:
        table_name = 'spike_reports'
        indexes = (
            (('domain',), False),
            (('topic',), False),
            (('created_at',), False),
            (('usefulness_score',), False),
        )


class Assumption(BaseModel):
    """Hypotheses to verify or challenge."""

    VALID_STATUSES = ('active', 'verified', 'challenged', 'invalidated')

    id = AutoField()
    assumption = TextField(null=False)
    context = TextField(null=True)
    source = TextField(null=True)
    confidence = FloatField(
        default=0.5,
        constraints=[Check("confidence >= 0.0 AND confidence <= 1.0")]
    )
    status = TextField(
        default='active',
        constraints=[Check("status IN ('active', 'verified', 'challenged', 'invalidated')")]
    )
    domain = TextField(null=True)
    verified_count = IntegerField(default=0)
    challenged_count = IntegerField(default=0)
    last_verified_at = DateTimeField(null=True)
    created_at = DateTimeField(default=datetime.utcnow)
    updated_at = DateTimeField(default=datetime.utcnow)

    class Meta:
        table_name = 'assumptions'
        indexes = (
            (('domain',), False),
            (('status',), False),
            (('confidence',), False),
            (('created_at',), False),
        )


# -----------------------------------------------------------------------------
# Metrics & Health Models
# -----------------------------------------------------------------------------

class Metric(BaseModel):
    """Real-time metrics."""

    id = AutoField()
    timestamp = DateTimeField(default=datetime.utcnow)
    metric_type = TextField(null=False)
    metric_name = TextField(null=False)
    metric_value = FloatField(null=False)
    tags = TextField(null=True)
    context = TextField(null=True)

    class Meta:
        table_name = 'metrics'
        indexes = (
            (('timestamp',), False),
            (('metric_type',), False),
            (('metric_name',), False),
            (('metric_type', 'metric_name', 'timestamp'), False),
        )


class SystemHealth(BaseModel):
    """System health snapshots."""

    id = AutoField()
    timestamp = DateTimeField(default=datetime.utcnow)
    status = TextField(null=False)
    db_integrity = TextField(null=True)
    db_size_mb = FloatField(null=True)
    disk_free_mb = FloatField(null=True)
    git_status = TextField(null=True)
    stale_locks = IntegerField(default=0)
    details = TextField(null=True)

    class Meta:
        table_name = 'system_health'
        indexes = (
            (('timestamp',), False),
            (('status',), False),
        )


class SchemaVersion(BaseModel):
    """Schema version tracking."""

    version = IntegerField(primary_key=True)
    applied_at = DateTimeField(default=datetime.utcnow)
    description = TextField(null=True)

    class Meta:
        table_name = 'schema_version'


class DbOperations(BaseModel):
    """Database operation tracking (singleton)."""

    id = IntegerField(primary_key=True, constraints=[Check("id = 1")])
    operation_count = IntegerField(default=0)
    last_vacuum = DateTimeField(null=True)
    last_analyze = DateTimeField(null=True)
    total_vacuums = IntegerField(default=0)
    total_analyzes = IntegerField(default=0)

    class Meta:
        table_name = 'db_operations'


# -----------------------------------------------------------------------------
# Workflow Models (Conductor/Swarm)
# -----------------------------------------------------------------------------

class Workflow(BaseModel):
    """Workflow definitions."""

    id = AutoField()
    name = TextField(null=False, unique=True)
    description = TextField(null=True)
    nodes_json = TextField(default='[]')
    config_json = TextField(default='{}')
    created_at = DateTimeField(default=datetime.utcnow)
    updated_at = DateTimeField(default=datetime.utcnow)

    class Meta:
        table_name = 'workflows'
        indexes = (
            (('name',), False),
        )


class WorkflowEdge(BaseModel):
    """Workflow edges (transitions between nodes)."""

    id = AutoField()
    workflow = ForeignKeyField(Workflow, backref='edges', null=False, on_delete='CASCADE')
    from_node = TextField(null=False)
    to_node = TextField(null=False)
    condition = TextField(default='')
    priority = IntegerField(default=100)
    created_at = DateTimeField(default=datetime.utcnow)

    class Meta:
        table_name = 'workflow_edges'
        indexes = (
            (('workflow',), False),
            (('from_node',), False),
            (('to_node',), False),
        )


class WorkflowRun(BaseModel):
    """Workflow execution runs."""

    id = AutoField()
    workflow = ForeignKeyField(Workflow, backref='runs', null=True, on_delete='SET NULL')
    workflow_name = TextField(null=True)
    status = TextField(null=False, default='pending')
    phase = TextField(default='init')
    input_json = TextField(default='{}')
    output_json = TextField(default='{}')
    context_json = TextField(default='{}')
    total_nodes = IntegerField(default=0)
    completed_nodes = IntegerField(default=0)
    failed_nodes = IntegerField(default=0)
    started_at = DateTimeField(null=True)
    completed_at = DateTimeField(null=True)
    created_at = DateTimeField(default=datetime.utcnow)
    error_message = TextField(null=True)

    class Meta:
        table_name = 'workflow_runs'
        indexes = (
            (('workflow',), False),
            (('status',), False),
            (('created_at',), False),
        )


class NodeExecution(BaseModel):
    """Individual node executions within a workflow run."""

    id = AutoField()
    run = ForeignKeyField(WorkflowRun, backref='node_executions', null=False, on_delete='CASCADE')
    node_id = TextField(null=False)
    node_name = TextField(null=True)
    node_type = TextField(null=False, default='single')
    agent_id = TextField(null=True)
    session_id = TextField(null=True)
    prompt = TextField(null=True)
    prompt_hash = TextField(null=True)
    status = TextField(null=False, default='pending')
    result_json = TextField(default='{}')
    result_text = TextField(null=True)
    findings_json = TextField(default='[]')
    files_modified = TextField(default='[]')
    duration_ms = IntegerField(null=True)
    token_count = IntegerField(null=True)
    retry_count = IntegerField(default=0)
    started_at = DateTimeField(null=True)
    completed_at = DateTimeField(null=True)
    created_at = DateTimeField(default=datetime.utcnow)
    error_message = TextField(null=True)
    error_type = TextField(null=True)

    class Meta:
        table_name = 'node_executions'
        indexes = (
            (('run',), False),
            (('agent_id',), False),
            (('status',), False),
            (('created_at',), False),
            (('node_id',), False),
            (('prompt_hash',), False),
        )


class Trail(BaseModel):
    """Pheromone trails (agent breadcrumbs)."""

    id = AutoField()
    run = ForeignKeyField(WorkflowRun, backref='trails', null=True, on_delete='SET NULL')
    location = TextField(null=False)
    location_type = TextField(default='file')
    scent = TextField(null=False)
    strength = FloatField(default=1.0)
    agent_id = TextField(null=True)
    node_id = TextField(null=True)
    message = TextField(null=True)
    tags = TextField(null=True)
    created_at = DateTimeField(default=datetime.utcnow)
    expires_at = DateTimeField(null=True)

    class Meta:
        table_name = 'trails'
        indexes = (
            (('run',), False),
            (('location',), False),
            (('scent',), False),
            (('strength',), False),
            (('created_at',), False),
            (('agent_id',), False),
        )


class ConductorDecision(BaseModel):
    """Conductor decisions log."""

    id = AutoField()
    run = ForeignKeyField(WorkflowRun, backref='conductor_decisions', null=False, on_delete='CASCADE')
    decision_type = TextField(null=False)
    decision_data = TextField(default='{}')
    reason = TextField(null=True)
    created_at = DateTimeField(default=datetime.utcnow)

    class Meta:
        table_name = 'conductor_decisions'
        indexes = (
            (('run',), False),
            (('decision_type',), False),
        )


# -----------------------------------------------------------------------------
# Query & Session Tracking Models
# -----------------------------------------------------------------------------

class BuildingQuery(BaseModel):
    """Building query logging - tracks all queries to the framework."""

    id = AutoField()
    query_type = TextField(null=False)
    session_id = TextField(null=True)
    agent_id = TextField(null=True)
    domain = TextField(null=True)
    tags = TextField(null=True)
    limit_requested = IntegerField(null=True)
    max_tokens_requested = IntegerField(null=True)
    results_returned = IntegerField(null=True)
    tokens_approximated = IntegerField(null=True)
    duration_ms = IntegerField(null=True)
    status = TextField(default='success')
    error_message = TextField(null=True)
    error_code = TextField(null=True)
    golden_rules_returned = IntegerField(default=0)
    heuristics_count = IntegerField(default=0)
    learnings_count = IntegerField(default=0)
    experiments_count = IntegerField(default=0)
    ceo_reviews_count = IntegerField(default=0)
    query_summary = TextField(null=True)
    created_at = DateTimeField(default=datetime.utcnow)
    completed_at = DateTimeField(null=True)

    class Meta:
        table_name = 'building_queries'
        indexes = (
            (('query_type',), False),
            (('session_id',), False),
            (('created_at',), False),
            (('status',), False),
        )


class SessionSummary(BaseModel):
    """Haiku-generated summaries of Claude sessions."""

    id = AutoField()
    session_id = TextField(null=False, unique=True)
    project = TextField(null=False)
    tool_summary = TextField(null=True)
    content_summary = TextField(null=True)
    conversation_summary = TextField(null=True)
    files_touched = TextField(default='[]')
    tool_counts = TextField(default='{}')
    message_count = IntegerField(default=0)
    session_file_path = TextField(null=True)
    session_file_size = IntegerField(null=True)
    session_last_modified = DateTimeField(null=True)
    summarized_at = DateTimeField(default=datetime.utcnow)
    summarizer_model = TextField(default='haiku')
    summary_version = IntegerField(default=1)
    is_stale = BooleanField(default=False)
    needs_resummarize = BooleanField(default=False)

    class Meta:
        table_name = 'session_summaries'
        indexes = (
            (('session_id',), False),
            (('project',), False),
            (('summarized_at',), False),
            (('is_stale',), False),
        )


# -----------------------------------------------------------------------------
# Utility Functions
# -----------------------------------------------------------------------------

def get_or_create_db_operations() -> DbOperations:
    """Get or create the singleton DbOperations record."""
    try:
        return DbOperations.get_by_id(1)
    except DbOperations.DoesNotExist:
        return DbOperations.create(id=1)


def increment_operation_count() -> int:
    """Increment and return the operation count."""
    ops = get_or_create_db_operations()
    ops.operation_count += 1
    ops.save()
    return ops.operation_count


# -----------------------------------------------------------------------------
# Export all models
# -----------------------------------------------------------------------------

__all__ = [
    # Database
    'db',
    'initialize_database',
    'create_tables',

    # Core models
    'Learning',
    'Heuristic',
    'Experiment',
    'CeoReview',
    'Cycle',
    'Decision',
    'Invariant',
    'Violation',
    'SpikeReport',
    'Assumption',

    # Metrics & Health
    'Metric',
    'SystemHealth',
    'SchemaVersion',
    'DbOperations',

    # Workflow models
    'Workflow',
    'WorkflowEdge',
    'WorkflowRun',
    'NodeExecution',
    'Trail',
    'ConductorDecision',

    # Query & Session
    'BuildingQuery',
    'SessionSummary',

    # Utilities
    'get_or_create_db_operations',
    'increment_operation_count',
]
