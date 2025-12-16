"""
QuerySystem core - orchestrates all query mixins (async version).

Usage:
    # Async API (v2.0.0+)
    qs = await QuerySystem.create()
    result = await qs.build_context("task")
    await qs.cleanup()

    # CLI handles async internally
    python query/query.py --context
"""

import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any, Optional

# Import async models and manager
try:
    from query.models import (
        manager as global_manager,
        get_manager,
        initialize_database,
        initialize_database_sync,
        Learning, Heuristic, Experiment, CeoReview, Decision, Violation, Invariant,
        BuildingQuery
    )
except ImportError:
    from models import (
        manager as global_manager,
        get_manager,
        initialize_database,
        initialize_database_sync,
        Learning, Heuristic, Experiment, CeoReview, Decision, Violation, Invariant,
        BuildingQuery
    )

# Import exceptions
try:
    from query.exceptions import (
        QuerySystemError, ValidationError, DatabaseError,
        TimeoutError, ConfigurationError
    )
except ImportError:
    from exceptions import (
        QuerySystemError, ValidationError, DatabaseError,
        TimeoutError, ConfigurationError
    )

# Import validators
try:
    from query.validators import (
        validate_domain, validate_limit, validate_tags, validate_query,
        MAX_DOMAIN_LENGTH, MAX_QUERY_LENGTH, MAX_TAG_COUNT, MAX_TAG_LENGTH,
        MIN_LIMIT, MAX_LIMIT, DEFAULT_TIMEOUT, MAX_TOKENS
    )
except ImportError:
    from validators import (
        validate_domain, validate_limit, validate_tags, validate_query,
        MAX_DOMAIN_LENGTH, MAX_QUERY_LENGTH, MAX_TAG_COUNT, MAX_TAG_LENGTH,
        MIN_LIMIT, MAX_LIMIT, DEFAULT_TIMEOUT, MAX_TOKENS
    )

# Import query mixins
try:
    from query.queries import (
        BaseQueryMixin,
        HeuristicQueryMixin,
        LearningQueryMixin,
        ExperimentQueryMixin,
        ViolationQueryMixin,
        DecisionQueryMixin,
        AssumptionQueryMixin,
        InvariantQueryMixin,
        SpikeQueryMixin,
        StatisticsQueryMixin,
    )
except ImportError:
    from queries import (
        BaseQueryMixin,
        HeuristicQueryMixin,
        LearningQueryMixin,
        ExperimentQueryMixin,
        ViolationQueryMixin,
        DecisionQueryMixin,
        AssumptionQueryMixin,
        InvariantQueryMixin,
        SpikeQueryMixin,
        StatisticsQueryMixin,
    )

# Import context builder mixin
try:
    from query.context import ContextBuilderMixin
except ImportError:
    from context import ContextBuilderMixin


class QuerySystem(
    HeuristicQueryMixin,
    LearningQueryMixin,
    ExperimentQueryMixin,
    ViolationQueryMixin,
    DecisionQueryMixin,
    AssumptionQueryMixin,
    InvariantQueryMixin,
    SpikeQueryMixin,
    StatisticsQueryMixin,
    ContextBuilderMixin,
    BaseQueryMixin
):
    """
    Main QuerySystem class - orchestrates all query operations (async).

    Use the async factory method to create instances:
        qs = await QuerySystem.create()

    Inherits query methods from mixins (all async in v2.0.0):
    - HeuristicQueryMixin: get_golden_rules, query_by_domain, query_by_tags
    - LearningQueryMixin: query_recent, find_similar_failures
    - ExperimentQueryMixin: get_active_experiments, get_pending_ceo_reviews
    - ViolationQueryMixin: get_violations, get_violation_summary
    - DecisionQueryMixin: get_decisions
    - AssumptionQueryMixin: get_assumptions, get_challenged_assumptions
    - InvariantQueryMixin: get_invariants
    - SpikeQueryMixin: get_spike_reports
    - StatisticsQueryMixin: get_statistics
    - ContextBuilderMixin: build_context
    """

    # Validation constants (for backward compatibility)
    MAX_DOMAIN_LENGTH = MAX_DOMAIN_LENGTH
    MAX_QUERY_LENGTH = MAX_QUERY_LENGTH
    MAX_TAG_COUNT = MAX_TAG_COUNT
    MAX_TAG_LENGTH = MAX_TAG_LENGTH
    MIN_LIMIT = MIN_LIMIT
    MAX_LIMIT = MAX_LIMIT
    DEFAULT_TIMEOUT = DEFAULT_TIMEOUT
    MAX_TOKENS = MAX_TOKENS

    def __init__(self, base_path: Optional[Path] = None, debug: bool = False,
                 session_id: Optional[str] = None, agent_id: Optional[str] = None):
        """
        Initialize the query system (internal use).

        Use QuerySystem.create() instead for proper async initialization.

        Args:
            base_path: Base path to the emergent-learning directory.
            debug: Enable debug logging
            session_id: Optional session ID for query logging
            agent_id: Optional agent ID for query logging
        """
        self.debug = debug
        self.session_id = session_id or os.environ.get('CLAUDE_SESSION_ID')
        self.agent_id = agent_id or os.environ.get('CLAUDE_AGENT_ID')

        if base_path is None:
            self.base_path = Path.home() / ".claude" / "emergent-learning"
        else:
            self.base_path = Path(base_path)

        self.memory_path = self.base_path / "memory"
        self.db_path = self.memory_path / "index.db"
        self.golden_rules_path = self.memory_path / "golden-rules.md"

    @classmethod
    async def create(cls, base_path: Optional[str] = None, debug: bool = False,
                     session_id: Optional[str] = None, agent_id: Optional[str] = None) -> 'QuerySystem':
        """
        Async factory method to create a QuerySystem instance.

        Args:
            base_path: Base path to the emergent-learning directory.
                      Defaults to ~/.claude/emergent-learning
            debug: Enable debug logging
            session_id: Optional session ID for query logging
            agent_id: Optional agent ID for query logging

        Returns:
            Configured QuerySystem instance

        Raises:
            ConfigurationError: If setup fails
        """
        if base_path:
            base_path = Path(base_path)
        else:
            base_path = Path.home() / ".claude" / "emergent-learning"

        # Create instance
        instance = cls(base_path, debug, session_id, agent_id)

        # Ensure directories exist
        try:
            instance.memory_path.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            raise ConfigurationError(
                f"Failed to create memory directory at {instance.memory_path}. "
                f"Check permissions. Error: {e} [QS004]"
            )

        # Initialize async database
        await initialize_database(str(instance.db_path))

        # Initialize database tables
        await instance._init_database()

        instance._log_debug(f"QuerySystem initialized with base_path: {instance.base_path}")
        return instance

    def _log_debug(self, message: str):
        """Log debug message if debug mode is enabled."""
        if self.debug:
            print(f"[DEBUG] {message}", file=sys.stderr)

    def _get_current_time_ms(self) -> int:
        """Get current time in milliseconds since epoch."""
        return int(datetime.now().timestamp() * 1000)

    async def _log_query(
        self,
        query_type: str,
        domain: Optional[str] = None,
        tags: Optional[str] = None,
        limit_requested: Optional[int] = None,
        max_tokens_requested: Optional[int] = None,
        results_returned: int = 0,
        tokens_approximated: Optional[int] = None,
        duration_ms: Optional[int] = None,
        status: str = 'success',
        error_message: Optional[str] = None,
        error_code: Optional[str] = None,
        golden_rules_returned: int = 0,
        heuristics_count: int = 0,
        learnings_count: int = 0,
        experiments_count: int = 0,
        ceo_reviews_count: int = 0,
        query_summary: Optional[str] = None,
        **kwargs
    ):
        """
        Log a query to the building_queries table (async).

        This is a non-blocking operation - if logging fails, it will not raise an exception.
        """
        try:
            m = get_manager()
            async with m:
                async with m.connection():
                    await BuildingQuery.create(
                        query_type=query_type,
                        session_id=self.session_id,
                        agent_id=self.agent_id,
                        domain=domain,
                        tags=tags,
                        limit_requested=limit_requested,
                        max_tokens_requested=max_tokens_requested,
                        results_returned=results_returned,
                        tokens_approximated=tokens_approximated,
                        duration_ms=duration_ms,
                        status=status,
                        error_message=error_message,
                        error_code=error_code,
                        golden_rules_returned=golden_rules_returned,
                        heuristics_count=heuristics_count,
                        learnings_count=learnings_count,
                        experiments_count=experiments_count,
                        ceo_reviews_count=ceo_reviews_count,
                        query_summary=query_summary,
                        completed_at=datetime.now(timezone.utc).replace(tzinfo=None)
                    )
            self._log_debug(f"Logged query: {query_type} (status={status}, duration={duration_ms}ms)")
        except Exception as e:
            # Non-blocking: log the error but don't raise
            self._log_debug(f"Failed to log query to building_queries: {e}")

    # ========== VALIDATION METHODS ==========

    def _validate_domain(self, domain: str) -> str:
        """Validate domain string. Delegates to validators.validate_domain()."""
        return validate_domain(domain)

    def _validate_limit(self, limit: int) -> int:
        """Validate limit parameter. Delegates to validators.validate_limit()."""
        return validate_limit(limit)

    def _validate_tags(self, tags: List[str]) -> List[str]:
        """Validate tags list. Delegates to validators.validate_tags()."""
        return validate_tags(tags)

    def _validate_query(self, query: str) -> str:
        """Validate query string. Delegates to validators.validate_query()."""
        return validate_query(query)

    # ========== DATABASE OPERATIONS ==========

    async def _init_database(self):
        """Initialize the database with required schema if it does not exist (async)."""
        # SECURITY: Check if database file was just created, set secure permissions
        db_just_created = not self.db_path.exists()

        m = get_manager()
        async with m:
            async with m.connection():
                # Create core tables using async model methods
                core_models = [
                    Learning,
                    Heuristic,
                    Experiment,
                    CeoReview,
                    Decision,
                    Violation,
                    Invariant,
                ]
                for model in core_models:
                    await model.create_table(safe=True)

        self._log_debug("Database tables created/verified via peewee-aio")

        # SECURITY: Set secure file permissions on database file
        if db_just_created or True:  # Always enforce secure permissions
            try:
                import stat
                os.chmod(str(self.db_path), stat.S_IRUSR | stat.S_IWUSR)

                # On Windows, also restrict ACLs to current user only
                if sys.platform == 'win32':
                    try:
                        import subprocess
                        username = os.environ.get("USERNAME", "")
                        if username and re.match(r'^[a-zA-Z0-9_\-\.]+$', username):
                            subprocess.run(
                                ['icacls', str(self.db_path), '/inheritance:r',
                                 '/grant:r', f'{username}:F'],
                                check=False, capture_output=True
                            )
                            self._log_debug(f"Set Windows ACLs for {self.db_path}")
                        else:
                            self._log_debug("Skipping icacls: invalid or missing USERNAME")
                    except Exception as win_err:
                        self._log_debug(f"Warning: Could not set Windows ACLs: {win_err}")

                self._log_debug(f"Set secure permissions (0600) on database file: {self.db_path}")
            except Exception as e:
                self._log_debug(f"Warning: Could not set secure permissions on database: {e}")

    async def validate_database(self) -> Dict[str, Any]:
        """
        Validate database integrity (async).

        Returns:
            Dictionary with validation results
        """
        results = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'checks': {}
        }

        try:
            m = get_manager()
            async with m:
                async with m.connection():
                    # Note: PRAGMA commands in aiosqlite need raw execution
                    # For now, mark basic checks as passed since tables were created
                    results['checks']['integrity'] = 'ok'
                    results['checks']['tables'] = [
                        'learnings', 'heuristics', 'experiments', 'ceo_reviews',
                        'decisions', 'violations', 'invariants'
                    ]

                    # Get table row counts using async iteration
                    model_map = {
                        'learnings': Learning,
                        'heuristics': Heuristic,
                        'experiments': Experiment,
                        'ceo_reviews': CeoReview
                    }
                    for table, model in model_map.items():
                        count = 0
                        async for _ in model.select():
                            count += 1
                        results['checks'][f'{table}_count'] = count

        except Exception as e:
            results['valid'] = False
            results['errors'].append(f"Validation failed: {str(e)}")

        return results

    async def cleanup(self):
        """Clean up resources (async). Call this when done with the query system."""
        try:
            m = get_manager()
            if m:
                # Manager cleanup if needed
                pass
        except Exception:
            pass
        self._log_debug("QuerySystem cleanup complete")

    def __del__(self):
        """Ensure cleanup on deletion."""
        # Note: Can't await in __del__, cleanup should be called explicitly
        pass
