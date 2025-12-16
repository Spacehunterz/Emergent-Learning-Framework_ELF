"""
QuerySystem core - orchestrates all query mixins.
"""

import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any, Optional

# Import Peewee models and database
PEEWEE_AVAILABLE = False
try:
    from query.models import (
        db as peewee_db,
        initialize_database as init_peewee_db,
        Learning, Heuristic, Experiment, CeoReview, Decision, Violation, Invariant,
        BuildingQuery
    )
    PEEWEE_AVAILABLE = True
except ImportError:
    try:
        from models import (
            db as peewee_db,
            initialize_database as init_peewee_db,
            Learning, Heuristic, Experiment, CeoReview, Decision, Violation, Invariant,
            BuildingQuery
        )
        PEEWEE_AVAILABLE = True
    except ImportError:
        pass

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
    Main QuerySystem class - orchestrates all query operations.

    Inherits query methods from mixins:
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

    def __init__(self, base_path: Optional[str] = None, debug: bool = False,
                 session_id: Optional[str] = None, agent_id: Optional[str] = None):
        """
        Initialize the query system.

        Args:
            base_path: Base path to the emergent-learning directory.
                      Defaults to ~/.claude/emergent-learning
            debug: Enable debug logging
            session_id: Optional session ID for query logging (fallback to CLAUDE_SESSION_ID env var)
            agent_id: Optional agent ID for query logging (fallback to CLAUDE_AGENT_ID env var)
        """
        self.debug = debug

        # Set session_id and agent_id with fallbacks
        self.session_id = session_id or os.environ.get('CLAUDE_SESSION_ID')
        self.agent_id = agent_id or os.environ.get('CLAUDE_AGENT_ID')

        if base_path is None:
            home = Path.home()
            self.base_path = home / ".claude" / "emergent-learning"
        else:
            self.base_path = Path(base_path)

        self.memory_path = self.base_path / "memory"
        self.db_path = self.memory_path / "index.db"
        self.golden_rules_path = self.memory_path / "golden-rules.md"

        # Ensure directories exist
        try:
            self.memory_path.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            raise ConfigurationError(
                f"Failed to create memory directory at {self.memory_path}. "
                f"Check permissions. Error: {e} [QS004]"
            )

        # Initialize Peewee ORM first (required for _init_database)
        if PEEWEE_AVAILABLE:
            init_peewee_db(str(self.db_path))
            self._log_debug("Peewee ORM initialized")

        # Initialize database tables (now uses Peewee)
        self._init_database()

        self._log_debug(f"QuerySystem initialized with base_path: {self.base_path}")

    def _log_debug(self, message: str):
        """Log debug message if debug mode is enabled."""
        if self.debug:
            print(f"[DEBUG] {message}", file=sys.stderr)

    def _get_current_time_ms(self) -> int:
        """Get current time in milliseconds since epoch."""
        return int(datetime.now().timestamp() * 1000)

    def _log_query(
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
        **kwargs  # Accept additional kwargs for flexibility
    ):
        """
        Log a query to the building_queries table.

        This is a non-blocking operation - if logging fails, it will not raise an exception.
        """
        try:
            BuildingQuery.create(
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
    # Delegates to validators module functions

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

    def _init_database(self):
        """Initialize the database with required schema if it does not exist."""
        # SECURITY: Check if database file was just created, set secure permissions
        db_just_created = not self.db_path.exists()

        # Create core tables using Peewee models (includes indexes defined in Meta)
        core_models = [
            Learning,
            Heuristic,
            Experiment,
            CeoReview,
            Decision,
            Violation,
            Invariant,
        ]
        peewee_db.create_tables(core_models, safe=True)

        # Run ANALYZE for query planner
        peewee_db.execute_sql("ANALYZE")

        self._log_debug("Database tables created/verified via Peewee")

        # SECURITY: Set secure file permissions on database file (owner read/write only)
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

    def validate_database(self) -> Dict[str, Any]:
        """
        Validate database integrity.

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
            # Check PRAGMA integrity
            integrity_result = peewee_db.execute_sql("PRAGMA integrity_check").fetchone()
            integrity = integrity_result[0] if integrity_result else 'unknown'
            results['checks']['integrity'] = integrity
            if integrity != 'ok':
                results['valid'] = False
                results['errors'].append(f"Database integrity check failed: {integrity}")

            # Check foreign keys
            fk_result = peewee_db.execute_sql("PRAGMA foreign_key_check").fetchall()
            if fk_result:
                results['valid'] = False
                results['errors'].append(f"Foreign key violations: {len(fk_result)}")
                results['checks']['foreign_keys'] = fk_result

            # Check table existence using Peewee
            required_tables = ['learnings', 'heuristics', 'experiments', 'ceo_reviews']
            existing_tables = peewee_db.get_tables()

            for table in required_tables:
                if table not in existing_tables:
                    results['valid'] = False
                    results['errors'].append(f"Required table '{table}' is missing")

            results['checks']['tables'] = existing_tables

            # Check index existence
            indexes_result = peewee_db.execute_sql(
                "SELECT name FROM sqlite_master WHERE type='index'"
            ).fetchall()
            indexes = [row[0] for row in indexes_result]
            results['checks']['indexes'] = indexes

            if not any('idx_learnings_domain' in idx for idx in indexes):
                results['warnings'].append("Some indexes may be missing")

            # Get table row counts using Peewee models
            model_map = {
                'learnings': Learning,
                'heuristics': Heuristic,
                'experiments': Experiment,
                'ceo_reviews': CeoReview
            }
            for table in required_tables:
                if table in existing_tables and table in model_map:
                    count = model_map[table].select().count()
                    results['checks'][f'{table}_count'] = count

        except Exception as e:
            results['valid'] = False
            results['errors'].append(f"Validation failed: {str(e)}")

        return results

    def cleanup(self):
        """Clean up resources. Call this when done with the query system."""
        try:
            # Close Peewee database if it's open
            if PEEWEE_AVAILABLE and peewee_db and not peewee_db.is_closed():
                peewee_db.close()
        except Exception:
            pass  # Ignore errors during cleanup
        self._log_debug("QuerySystem cleanup complete")

    def __del__(self):
        """Ensure cleanup on deletion."""
        try:
            self.cleanup()
        except Exception:
            pass  # Ignore errors during garbage collection
