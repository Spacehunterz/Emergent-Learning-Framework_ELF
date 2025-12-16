"""
Peewee-AIO async ORM models for the Emergent Learning Framework.

This module defines all database models using peewee-aio for async support,
matching the existing SQLite schema exactly.

Usage:
    from models import manager, initialize_database, Learning, Heuristic, ...

    # Initialize with path (async)
    await initialize_database('~/.claude/emergent-learning/memory/index.db')

    # Query examples (async)
    async with manager:
        async for h in Heuristic.select().where(Heuristic.is_golden == True).limit(10):
            print(h.rule)
"""

from peewee_aio import Manager, AIOModel, fields
from peewee import Check
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
import os

# -----------------------------------------------------------------------------
# Database Configuration
# -----------------------------------------------------------------------------

# Global manager - initialized at runtime via initialize_database()
manager: Optional[Manager] = None


async def initialize_database(db_path: Optional[str] = None) -> Manager:
    """
    Initialize the async database connection.

    Args:
        db_path: Path to SQLite database file. Defaults to ~/.claude/emergent-learning/memory/index.db

    Returns:
        Configured Manager instance
    """
    global manager

    if db_path is None:
        db_path = Path.home() / ".claude" / "emergent-learning" / "memory" / "index.db"
    else:
        db_path = Path(db_path).expanduser()

    # Ensure parent directory exists
    db_path.parent.mkdir(parents=True, exist_ok=True)

    # Create manager with aiosqlite URL
    # Note: aiosqlite uses file path directly (not traditional URL format for file DBs)
    manager = Manager(f'aiosqlite:///{db_path}')

    # Register all models with the manager
    _register_all_models(manager)

    return manager


def _register_all_models(m: Manager):
    """Register all model classes with the given manager."""
    # Import models at function level to ensure they're defined
    models_to_register = [
        Learning,
        Heuristic,
        Experiment,
        CeoReview,
        Cycle,
        Decision,
        Invariant,
        Violation,
        SpikeReport,
        Assumption,
        Metric,
        SystemHealth,
        SchemaVersion,
        DbOperations,
        Workflow,
        WorkflowEdge,
        WorkflowRun,
        NodeExecution,
        Trail,
        ConductorDecision,
        BuildingQuery,
        SessionSummary,
    ]
    for model in models_to_register:
        m.register(model)


def get_manager() -> Manager:
    """Get the current manager instance. Raises if not initialized."""
    if manager is None:
        raise RuntimeError("Database not initialized. Call initialize_database() first.")
    return manager


async def create_tables():
    """Create all tables if they don't exist (async)."""
    m = get_manager()
    async with m:
        async with m.connection():
            # Create all registered models' tables
            for model in [
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
            ]:
                await model.create_table(safe=True)


# Synchronous initialization for backward compatibility / CLI bootstrap
def initialize_database_sync(db_path: Optional[str] = None) -> Manager:
    """
    Initialize database synchronously (for CLI bootstrap).

    Args:
        db_path: Path to SQLite database file.

    Returns:
        Configured Manager instance
    """
    global manager

    if db_path is None:
        db_path = Path.home() / ".claude" / "emergent-learning" / "memory" / "index.db"
    else:
        db_path = Path(db_path).expanduser()

    db_path.parent.mkdir(parents=True, exist_ok=True)

    manager = Manager(f'aiosqlite:///{db_path}')

    # Register all models with the manager
    _register_all_models(manager)

    return manager


# -----------------------------------------------------------------------------
# Base Model
# -----------------------------------------------------------------------------

class BaseModel(AIOModel):
    """Base model class with common configuration."""

    class Meta:
        # Manager will be set when @manager.register is called
        pass

    def to_dict(self) -> Dict[str, Any]:
        """Convert model instance to dictionary."""
        return self.__data__.copy()


# -----------------------------------------------------------------------------
# Core Learning Models
# -----------------------------------------------------------------------------

class Learning(BaseModel):
    """Core learning records (failures, successes, observations)."""

    VALID_TYPES = ('failure', 'success', 'heuristic', 'experiment', 'observation')

    id = fields.AutoField()
    type = fields.TextField(
        null=False,
        constraints=[Check("type IN ('failure', 'success', 'heuristic', 'experiment', 'observation')")]
    )
    filepath = fields.TextField(null=False)
    title = fields.TextField(null=False)
    summary = fields.TextField(null=True)
    tags = fields.TextField(null=True)  # Comma-separated
    domain = fields.TextField(null=True)
    severity = fields.IntegerField(
        default=3,
        constraints=[Check("severity >= 1 AND severity <= 5")]
    )
    created_at = fields.DateTimeField(default=datetime.utcnow)
    updated_at = fields.DateTimeField(default=datetime.utcnow)

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

    id = fields.AutoField()
    domain = fields.TextField(null=False)
    rule = fields.TextField(null=False)
    explanation = fields.TextField(null=True)
    source_type = fields.TextField(null=True)
    source_id = fields.IntegerField(null=True)
    confidence = fields.FloatField(
        default=0.5,
        constraints=[Check("confidence >= 0.0 AND confidence <= 1.0")]
    )
    times_validated = fields.IntegerField(
        default=0,
        constraints=[Check("times_validated >= 0")]
    )
    times_violated = fields.IntegerField(
        default=0,
        constraints=[Check("times_violated >= 0")]
    )
    is_golden = fields.BooleanField(default=False)
    created_at = fields.DateTimeField(default=datetime.utcnow)
    updated_at = fields.DateTimeField(default=datetime.utcnow)

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

    id = fields.AutoField()
    name = fields.TextField(null=False, unique=True)
    hypothesis = fields.TextField(null=True)
    status = fields.TextField(default='active')
    cycles_run = fields.IntegerField(default=0)
    folder_path = fields.TextField(null=True)
    created_at = fields.DateTimeField(default=datetime.utcnow)
    updated_at = fields.DateTimeField(default=datetime.utcnow)

    class Meta:
        table_name = 'experiments'
        indexes = (
            (('status',), False),
        )


class CeoReview(BaseModel):
    """CEO escalation requests."""

    id = fields.AutoField()
    title = fields.TextField(null=False)
    context = fields.TextField(null=True)
    recommendation = fields.TextField(null=True)
    status = fields.TextField(default='pending')
    created_at = fields.DateTimeField(default=datetime.utcnow)
    reviewed_at = fields.DateTimeField(null=True)

    class Meta:
        table_name = 'ceo_reviews'
        indexes = (
            (('status',), False),
        )


class Cycle(BaseModel):
    """Experiment cycles."""

    id = fields.AutoField()
    experiment = fields.AIODeferredForeignKey('Experiment', backref='cycles', null=True, on_delete='SET NULL')
    cycle_number = fields.IntegerField(null=True)
    try_summary = fields.TextField(null=True)
    break_summary = fields.TextField(null=True)
    analysis = fields.TextField(null=True)
    learning_extracted = fields.TextField(null=True)
    heuristic = fields.AIODeferredForeignKey('Heuristic', backref='cycles', null=True, on_delete='SET NULL')
    created_at = fields.DateTimeField(default=datetime.utcnow)

    class Meta:
        table_name = 'cycles'


class Decision(BaseModel):
    """Architecture Decision Records (ADRs)."""

    id = fields.AutoField()
    title = fields.TextField(null=False)
    context = fields.TextField(null=False)
    options_considered = fields.TextField(null=True)
    decision = fields.TextField(null=False)
    rationale = fields.TextField(null=False)
    files_touched = fields.TextField(null=True)
    tests_added = fields.TextField(null=True)
    status = fields.TextField(default='accepted')
    domain = fields.TextField(null=True)
    superseded_by = fields.AIODeferredForeignKey('self', backref='supersedes', null=True, on_delete='SET NULL')
    created_at = fields.DateTimeField(default=datetime.utcnow)
    updated_at = fields.DateTimeField(default=datetime.utcnow)

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

    id = fields.AutoField()
    statement = fields.TextField(null=False)
    rationale = fields.TextField(null=False)
    domain = fields.TextField(null=True)
    scope = fields.TextField(default='codebase')  # codebase, module, function, runtime
    validation_type = fields.TextField(null=True)  # manual, automated, test
    validation_code = fields.TextField(null=True)
    severity = fields.TextField(default='error')  # error, warning, info
    status = fields.TextField(default='active')
    violation_count = fields.IntegerField(default=0)
    last_validated_at = fields.DateTimeField(null=True)
    last_violated_at = fields.DateTimeField(null=True)
    created_at = fields.DateTimeField(default=datetime.utcnow)
    updated_at = fields.DateTimeField(default=datetime.utcnow)

    class Meta:
        table_name = 'invariants'
        indexes = (
            (('domain',), False),
            (('status',), False),
            (('severity',), False),
        )


class Violation(BaseModel):
    """Golden rule violations (accountability tracking)."""

    id = fields.AutoField()
    rule_id = fields.IntegerField(null=False)
    rule_name = fields.TextField(null=False)
    violation_date = fields.DateTimeField(default=datetime.utcnow)
    description = fields.TextField(null=True)
    session_id = fields.TextField(null=True)
    acknowledged = fields.BooleanField(default=False)

    class Meta:
        table_name = 'violations'
        indexes = (
            (('violation_date',), False),
            (('rule_id',), False),
            (('acknowledged',), False),
        )


class SpikeReport(BaseModel):
    """Time-boxed research investigations."""

    id = fields.AutoField()
    title = fields.TextField(null=False)
    topic = fields.TextField(null=True)
    question = fields.TextField(null=True)
    findings = fields.TextField(null=True)
    gotchas = fields.TextField(null=True)
    resources = fields.TextField(null=True)
    time_invested_minutes = fields.IntegerField(null=True)
    domain = fields.TextField(null=True)
    tags = fields.TextField(null=True)
    usefulness_score = fields.FloatField(default=0)
    access_count = fields.IntegerField(default=0)
    created_at = fields.DateTimeField(default=datetime.utcnow)
    updated_at = fields.DateTimeField(default=datetime.utcnow)

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

    id = fields.AutoField()
    assumption = fields.TextField(null=False)
    context = fields.TextField(null=True)
    source = fields.TextField(null=True)
    confidence = fields.FloatField(
        default=0.5,
        constraints=[Check("confidence >= 0.0 AND confidence <= 1.0")]
    )
    status = fields.TextField(
        default='active',
        constraints=[Check("status IN ('active', 'verified', 'challenged', 'invalidated')")]
    )
    domain = fields.TextField(null=True)
    verified_count = fields.IntegerField(default=0)
    challenged_count = fields.IntegerField(default=0)
    last_verified_at = fields.DateTimeField(null=True)
    created_at = fields.DateTimeField(default=datetime.utcnow)
    updated_at = fields.DateTimeField(default=datetime.utcnow)

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

    id = fields.AutoField()
    timestamp = fields.DateTimeField(default=datetime.utcnow)
    metric_type = fields.TextField(null=False)
    metric_name = fields.TextField(null=False)
    metric_value = fields.FloatField(null=False)
    tags = fields.TextField(null=True)
    context = fields.TextField(null=True)

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

    id = fields.AutoField()
    timestamp = fields.DateTimeField(default=datetime.utcnow)
    status = fields.TextField(null=False)
    db_integrity = fields.TextField(null=True)
    db_size_mb = fields.FloatField(null=True)
    disk_free_mb = fields.FloatField(null=True)
    git_status = fields.TextField(null=True)
    stale_locks = fields.IntegerField(default=0)
    details = fields.TextField(null=True)

    class Meta:
        table_name = 'system_health'
        indexes = (
            (('timestamp',), False),
            (('status',), False),
        )


class SchemaVersion(BaseModel):
    """Schema version tracking."""

    version = fields.IntegerField(primary_key=True)
    applied_at = fields.DateTimeField(default=datetime.utcnow)
    description = fields.TextField(null=True)

    class Meta:
        table_name = 'schema_version'


class DbOperations(BaseModel):
    """Database operation tracking (singleton)."""

    id = fields.IntegerField(primary_key=True, constraints=[Check("id = 1")])
    operation_count = fields.IntegerField(default=0)
    last_vacuum = fields.DateTimeField(null=True)
    last_analyze = fields.DateTimeField(null=True)
    total_vacuums = fields.IntegerField(default=0)
    total_analyzes = fields.IntegerField(default=0)

    class Meta:
        table_name = 'db_operations'


# -----------------------------------------------------------------------------
# Workflow Models (Conductor/Swarm)
# -----------------------------------------------------------------------------

class Workflow(BaseModel):
    """Workflow definitions."""

    id = fields.AutoField()
    name = fields.TextField(null=False, unique=True)
    description = fields.TextField(null=True)
    nodes_json = fields.TextField(default='[]')
    config_json = fields.TextField(default='{}')
    created_at = fields.DateTimeField(default=datetime.utcnow)
    updated_at = fields.DateTimeField(default=datetime.utcnow)

    class Meta:
        table_name = 'workflows'
        indexes = (
            (('name',), False),
        )


class WorkflowEdge(BaseModel):
    """Workflow edges (transitions between nodes)."""

    id = fields.AutoField()
    workflow = fields.AIODeferredForeignKey('Workflow', backref='edges', null=False, on_delete='CASCADE')
    from_node = fields.TextField(null=False)
    to_node = fields.TextField(null=False)
    condition = fields.TextField(default='')
    priority = fields.IntegerField(default=100)
    created_at = fields.DateTimeField(default=datetime.utcnow)

    class Meta:
        table_name = 'workflow_edges'
        indexes = (
            (('workflow',), False),
            (('from_node',), False),
            (('to_node',), False),
        )


class WorkflowRun(BaseModel):
    """Workflow execution runs."""

    id = fields.AutoField()
    workflow = fields.AIODeferredForeignKey('Workflow', backref='runs', null=True, on_delete='SET NULL')
    workflow_name = fields.TextField(null=True)
    status = fields.TextField(null=False, default='pending')
    phase = fields.TextField(default='init')
    input_json = fields.TextField(default='{}')
    output_json = fields.TextField(default='{}')
    context_json = fields.TextField(default='{}')
    total_nodes = fields.IntegerField(default=0)
    completed_nodes = fields.IntegerField(default=0)
    failed_nodes = fields.IntegerField(default=0)
    started_at = fields.DateTimeField(null=True)
    completed_at = fields.DateTimeField(null=True)
    created_at = fields.DateTimeField(default=datetime.utcnow)
    error_message = fields.TextField(null=True)

    class Meta:
        table_name = 'workflow_runs'
        indexes = (
            (('workflow',), False),
            (('status',), False),
            (('created_at',), False),
        )


class NodeExecution(BaseModel):
    """Individual node executions within a workflow run."""

    id = fields.AutoField()
    run = fields.AIODeferredForeignKey('WorkflowRun', backref='node_executions', null=False, on_delete='CASCADE')
    node_id = fields.TextField(null=False)
    node_name = fields.TextField(null=True)
    node_type = fields.TextField(null=False, default='single')
    agent_id = fields.TextField(null=True)
    session_id = fields.TextField(null=True)
    prompt = fields.TextField(null=True)
    prompt_hash = fields.TextField(null=True)
    status = fields.TextField(null=False, default='pending')
    result_json = fields.TextField(default='{}')
    result_text = fields.TextField(null=True)
    findings_json = fields.TextField(default='[]')
    files_modified = fields.TextField(default='[]')
    duration_ms = fields.IntegerField(null=True)
    token_count = fields.IntegerField(null=True)
    retry_count = fields.IntegerField(default=0)
    started_at = fields.DateTimeField(null=True)
    completed_at = fields.DateTimeField(null=True)
    created_at = fields.DateTimeField(default=datetime.utcnow)
    error_message = fields.TextField(null=True)
    error_type = fields.TextField(null=True)

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

    id = fields.AutoField()
    run = fields.AIODeferredForeignKey('WorkflowRun', backref='trails', null=True, on_delete='SET NULL')
    location = fields.TextField(null=False)
    location_type = fields.TextField(default='file')
    scent = fields.TextField(null=False)
    strength = fields.FloatField(default=1.0)
    agent_id = fields.TextField(null=True)
    node_id = fields.TextField(null=True)
    message = fields.TextField(null=True)
    tags = fields.TextField(null=True)
    created_at = fields.DateTimeField(default=datetime.utcnow)
    expires_at = fields.DateTimeField(null=True)

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

    id = fields.AutoField()
    run = fields.AIODeferredForeignKey('WorkflowRun', backref='conductor_decisions', null=False, on_delete='CASCADE')
    decision_type = fields.TextField(null=False)
    decision_data = fields.TextField(default='{}')
    reason = fields.TextField(null=True)
    created_at = fields.DateTimeField(default=datetime.utcnow)

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

    id = fields.AutoField()
    query_type = fields.TextField(null=False)
    session_id = fields.TextField(null=True)
    agent_id = fields.TextField(null=True)
    domain = fields.TextField(null=True)
    tags = fields.TextField(null=True)
    limit_requested = fields.IntegerField(null=True)
    max_tokens_requested = fields.IntegerField(null=True)
    results_returned = fields.IntegerField(null=True)
    tokens_approximated = fields.IntegerField(null=True)
    duration_ms = fields.IntegerField(null=True)
    status = fields.TextField(default='success')
    error_message = fields.TextField(null=True)
    error_code = fields.TextField(null=True)
    golden_rules_returned = fields.IntegerField(default=0)
    heuristics_count = fields.IntegerField(default=0)
    learnings_count = fields.IntegerField(default=0)
    experiments_count = fields.IntegerField(default=0)
    ceo_reviews_count = fields.IntegerField(default=0)
    query_summary = fields.TextField(null=True)
    created_at = fields.DateTimeField(default=datetime.utcnow)
    completed_at = fields.DateTimeField(null=True)

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

    id = fields.AutoField()
    session_id = fields.TextField(null=False, unique=True)
    project = fields.TextField(null=False)
    tool_summary = fields.TextField(null=True)
    content_summary = fields.TextField(null=True)
    conversation_summary = fields.TextField(null=True)
    files_touched = fields.TextField(default='[]')
    tool_counts = fields.TextField(default='{}')
    message_count = fields.IntegerField(default=0)
    session_file_path = fields.TextField(null=True)
    session_file_size = fields.IntegerField(null=True)
    session_last_modified = fields.DateTimeField(null=True)
    summarized_at = fields.DateTimeField(default=datetime.utcnow)
    summarizer_model = fields.TextField(default='haiku')
    summary_version = fields.IntegerField(default=1)
    is_stale = fields.BooleanField(default=False)
    needs_resummarize = fields.BooleanField(default=False)

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

async def get_or_create_db_operations() -> DbOperations:
    """Get or create the singleton DbOperations record (async)."""
    m = get_manager()
    async with m:
        async with m.connection():
            try:
                return await DbOperations.aio_get(DbOperations.id == 1)
            except DbOperations.DoesNotExist:
                return await DbOperations.aio_create(id=1)


async def increment_operation_count() -> int:
    """Increment and return the operation count (async)."""
    ops = await get_or_create_db_operations()
    ops.operation_count += 1
    await ops.aio_save()
    return ops.operation_count


# -----------------------------------------------------------------------------
# Export all models
# -----------------------------------------------------------------------------

__all__ = [
    # Database
    'manager',
    'get_manager',
    'initialize_database',
    'initialize_database_sync',
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
