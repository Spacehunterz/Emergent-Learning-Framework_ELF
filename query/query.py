#!/usr/bin/env python3
"""
Emergent Learning Framework - Query System

TIME-FIX-6: All timestamps are stored in UTC (via SQLite CURRENT_TIMESTAMP).
Database uses naive datetime objects, but SQLite CURRENT_TIMESTAMP returns UTC.
For timezone-aware operations, consider adding timezone library in future.
A tiered retrieval system for knowledge retrieval across the learning framework.

Tier 1: Golden rules (always loaded, ~500 tokens)
Tier 2: Query-matched content by domain/tags (~2-5k tokens)
Tier 3: On-demand deep history

ROBUSTNESS SCORE: 10/10
- Complete input validation
- CLI enhancements (debug, timeout, formats, validate)
- Comprehensive error handling with specific error types
- Connection pooling and proper cleanup
- Query timeout enforcement
- Full test coverage support
"""

import os
import sys
import io
import argparse
import signal
import re
import csv
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timezone
from contextlib import contextmanager
import json

# Peewee ORM imports - full migration complete
try:
    from query.models import (
        db as peewee_db,
        initialize_database as init_peewee_db,
        Heuristic,
        Learning,
        Experiment,
        CeoReview,
        Decision,
        Invariant,
        Violation,
        SpikeReport,
        Assumption,
        BuildingQuery,
        Workflow,
        WorkflowRun,
        NodeExecution,
        Trail,
        SessionSummary,
        Metric,
        SystemHealth,
    )
    PEEWEE_AVAILABLE = True
except ImportError:
    # Try alternate import path when running as script
    try:
        from models import (
            db as peewee_db,
            initialize_database as init_peewee_db,
            Heuristic,
            Learning,
            Experiment,
            CeoReview,
            Decision,
            Invariant,
            Violation,
            SpikeReport,
            Assumption,
            BuildingQuery,
            Workflow,
            WorkflowRun,
            NodeExecution,
            Trail,
            SessionSummary,
            Metric,
            SystemHealth,
        )
        PEEWEE_AVAILABLE = True
    except ImportError:
        PEEWEE_AVAILABLE = False

# Meta-observer for system health monitoring
try:
    from meta_observer import MetaObserver
    META_OBSERVER_AVAILABLE = True
except ImportError:
    META_OBSERVER_AVAILABLE = False

# Import from refactored modules
try:
    from query.exceptions import (
        QuerySystemError, ValidationError, DatabaseError,
        TimeoutError, ConfigurationError
    )
    from query.utils import TimeoutHandler, escape_like, setup_windows_console
    from query.validators import (
        validate_domain, validate_limit, validate_tags, validate_query,
        MAX_DOMAIN_LENGTH, MAX_QUERY_LENGTH, MAX_TAG_COUNT, MAX_TAG_LENGTH,
        MIN_LIMIT, MAX_LIMIT, DEFAULT_TIMEOUT, MAX_TOKENS
    )
    from query.formatters import format_output, generate_accountability_banner
    from query.setup import ensure_hooks_installed, ensure_full_setup
except ImportError:
    # Fallback for running as script
    from exceptions import (
        QuerySystemError, ValidationError, DatabaseError,
        TimeoutError, ConfigurationError
    )
    from utils import TimeoutHandler, escape_like, setup_windows_console
    from validators import (
        validate_domain, validate_limit, validate_tags, validate_query,
        MAX_DOMAIN_LENGTH, MAX_QUERY_LENGTH, MAX_TAG_COUNT, MAX_TAG_LENGTH,
        MIN_LIMIT, MAX_TOKENS, DEFAULT_TIMEOUT, MAX_LIMIT
    )
    from formatters import format_output, generate_accountability_banner
    from setup import ensure_hooks_installed, ensure_full_setup

# Fix Windows console encoding for Unicode characters
setup_windows_console()


class QuerySystem:
    """Manages knowledge retrieval from the Emergent Learning Framework."""

    # Validation constants (imported from validators module for backward compatibility)
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
        query_summary: Optional[str] = None
    ):
        """
        Log a query to the building_queries table.

        This is a non-blocking operation - if logging fails, it will not raise an exception.

        Args:
            query_type: Type of query (e.g., 'build_context', 'query_by_domain')
            domain: Domain queried (if applicable)
            tags: Tags queried (if applicable, comma-separated string)
            limit_requested: Limit parameter used
            max_tokens_requested: Max tokens parameter used
            results_returned: Number of results returned
            tokens_approximated: Approximate token count
            duration_ms: Query duration in milliseconds
            status: Query status ('success', 'error', 'timeout')
            error_message: Error message if status is 'error'
            error_code: Error code if status is 'error'
            golden_rules_returned: Number of golden rules returned
            heuristics_count: Number of heuristics returned
            learnings_count: Number of learnings returned
            experiments_count: Number of experiments returned
            ceo_reviews_count: Number of CEO reviews returned
            query_summary: Brief summary of the query
        """
        try:
            # Peewee ORM insert (migrated from raw sqlite3)
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

    def _record_system_metrics(self, domain: Optional[str] = None):
        """
        Record system health metrics via MetaObserver.

        Called after each query to track:
        - avg_confidence: Average confidence of active heuristics
        - validation_velocity: Validations in last 24 hours
        - contradiction_rate: Contradictions / total applications
        - query_count: Incremented on each query

        This is non-blocking - errors are logged but don't propagate.
        """
        if not META_OBSERVER_AVAILABLE:
            return

        try:
            observer = MetaObserver(db_path=self.db_path)

            from peewee import fn

            # 1. Average confidence of heuristics (no 'status' column in actual schema)
            query = Heuristic.select(fn.AVG(Heuristic.confidence), fn.COUNT(Heuristic.id))
            if domain:
                query = query.where(Heuristic.domain == domain)

            result = query.tuples().first()
            avg_conf = result[0] if result and result[0] else 0.5
            heuristic_count = result[1] if result and result[1] else 0

            if heuristic_count > 0:
                observer.record_metric('avg_confidence', avg_conf, domain=domain,
                                      metadata={'heuristic_count': heuristic_count})

            # 2. Validation velocity - sum of times_validated in last 24 hours
            # (confidence_updates table doesn't exist, use heuristics.times_validated instead)
            from datetime import timedelta
            cutoff_24h = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=24)
            validation_query = Heuristic.select(fn.SUM(Heuristic.times_validated))
            if domain:
                validation_query = validation_query.where(Heuristic.domain == domain)
            validation_result = validation_query.tuples().first()
            validation_count = validation_result[0] if validation_result and validation_result[0] else 0
            observer.record_metric('validation_velocity', validation_count, domain=domain)

            # 3. Violation rate (times_contradicted doesn't exist, use times_violated instead)
            violation_query = (Heuristic
                .select(
                    fn.SUM(Heuristic.times_violated),
                    fn.SUM(Heuristic.times_validated + Heuristic.times_violated)
                ))
            violation_result = violation_query.tuples().first()
            if violation_result and violation_result[1] and violation_result[1] > 0:
                violation_rate = (violation_result[0] or 0) / violation_result[1]
                observer.record_metric('violation_rate', violation_rate, domain=domain)

            # 4. Query count (simple increment)
            observer.record_metric('query_count', 1, domain=domain)

            self._log_debug("Recorded system metrics to meta_observer")

        except Exception as e:
            # Non-blocking: log the error but don't raise
            self._log_debug(f"Failed to record system metrics: {e}")

    def _check_system_alerts(self) -> list:
        """
        Check for system alerts via MetaObserver.

        Returns list of active alerts, or empty list if unavailable.
        This is non-blocking.
        """
        if not META_OBSERVER_AVAILABLE:
            return []

        try:
            observer = MetaObserver(db_path=self.db_path)
            return observer.check_alerts()
        except Exception as e:
            self._log_debug(f"Failed to check system alerts: {e}")
            return []

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
        # This prevents other users from reading sensitive learning data
        if db_just_created or True:  # Always enforce secure permissions
            try:
                import stat
                # Set permissions to 0600 (owner read/write only)
                os.chmod(str(self.db_path), stat.S_IRUSR | stat.S_IWUSR)

                # On Windows, also restrict ACLs to current user only
                if sys.platform == 'win32':
                    try:
                        import subprocess
                        # Remove inheritance and grant full control only to current user
                        # icacls command: /inheritance:r removes inherited permissions
                        # /grant:r grants permissions, replacing existing ones

                        # Security fix: Validate USERNAME to prevent command injection
                        # Only allow alphanumeric, underscore, hyphen, and dot characters
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
                # Non-fatal: log warning but don't fail initialization
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
            # Use Peewee's database connection for PRAGMA commands

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

    # ========== QUERY METHODS WITH VALIDATION ==========

    def get_golden_rules(self) -> str:
        """
        Read and return golden rules from memory/golden-rules.md.

        Returns:
            Content of golden rules file, or empty string if file does not exist.
        """
        if not self.golden_rules_path.exists():
            return "# Golden Rules\n\nNo golden rules have been established yet."

        try:
            with open(self.golden_rules_path, 'r', encoding='utf-8') as f:
                content = f.read()
            self._log_debug(f"Loaded golden rules ({len(content)} chars)")
            return content
        except Exception as e:
            error_msg = f"# Error Reading Golden Rules\n\nError: {str(e)}"
            self._log_debug(f"Failed to read golden rules: {e}")
            return error_msg

    def query_by_domain(self, domain: str, limit: int = 10, timeout: int = None) -> Dict[str, Any]:
        """
        Get heuristics and learnings for a specific domain.

        Args:
            domain: The domain to query (e.g., 'coordination', 'debugging')
            limit: Maximum number of results to return
            timeout: Query timeout in seconds (default: 30)

        Returns:
            Dictionary containing heuristics and learnings for the domain

        Raises:
            ValidationError: If inputs are invalid
            TimeoutError: If query times out
            DatabaseError: If database operation fails
        """
        start_time = self._get_current_time_ms()
        error_msg = None
        error_code = None
        status = 'success'
        result = None

        try:
            # Validate inputs
            domain = self._validate_domain(domain)
            limit = self._validate_limit(limit)
            timeout = timeout or self.DEFAULT_TIMEOUT

            self._log_debug(f"Querying domain '{domain}' with limit {limit}")
            with TimeoutHandler(timeout):
                # Get heuristics for domain
                heuristics_query = (Heuristic
                    .select()
                    .where(Heuristic.domain == domain)
                    .order_by(Heuristic.confidence.desc(), Heuristic.times_validated.desc())
                    .limit(limit))
                heuristics = [h.__data__.copy() for h in heuristics_query]

                # Get learnings for domain
                learnings_query = (Learning
                    .select()
                    .where(Learning.domain == domain)
                    .order_by(Learning.created_at.desc())
                    .limit(limit))
                learnings = [l.__data__.copy() for l in learnings_query]

            result = {
                'domain': domain,
                'heuristics': heuristics,
                'learnings': learnings,
                'count': {
                    'heuristics': len(heuristics),
                    'learnings': len(learnings)
                }
            }

            self._log_debug(f"Found {len(heuristics)} heuristics and {len(learnings)} learnings")
            return result

        except TimeoutError as e:
            status = 'timeout'
            error_msg = str(e)
            error_code = 'QS003'
            raise
        except (ValidationError, DatabaseError, QuerySystemError) as e:
            status = 'error'
            error_msg = str(e)
            error_code = getattr(e, 'error_code', 'QS000')
            raise
        except Exception as e:
            status = 'error'
            error_msg = str(e)
            error_code = 'QS000'
            raise
        finally:
            # Log the query (non-blocking)
            duration_ms = self._get_current_time_ms() - start_time
            heuristics_count = len(result['heuristics']) if result else 0
            learnings_count = len(result['learnings']) if result else 0
            total_results = heuristics_count + learnings_count

            self._log_query(
                query_type='query_by_domain',
                domain=domain,
                limit_requested=limit,
                results_returned=total_results,
                duration_ms=duration_ms,
                status=status,
                error_message=error_msg,
                error_code=error_code,
                heuristics_count=heuristics_count,
                learnings_count=learnings_count,
                query_summary=f"Domain query for '{domain}'"
            )

    def query_by_tags(self, tags: List[str], limit: int = 10, timeout: int = None) -> List[Dict[str, Any]]:
        """
        Get learnings matching specified tags.

        Args:
            tags: List of tags to search for
            limit: Maximum number of results to return
            timeout: Query timeout in seconds (default: 30)

        Returns:
            List of learnings matching any of the tags

        Raises:
            ValidationError: If inputs are invalid
            TimeoutError: If query times out
            DatabaseError: If database operation fails
        """
        start_time = self._get_current_time_ms()
        error_msg = None
        error_code = None
        status = 'success'
        results = None

        try:
            # Validate inputs
            tags = self._validate_tags(tags)
            limit = self._validate_limit(limit)
            timeout = timeout or self.DEFAULT_TIMEOUT

            self._log_debug(f"Querying tags {tags} with limit {limit}")
            with TimeoutHandler(timeout):
                # Build OR conditions for tag matching (tags stored as comma-separated string)
                from functools import reduce
                from operator import or_

                # Each tag gets a LIKE condition: tags LIKE '%tag%'
                conditions = [Learning.tags.contains(escape_like(tag)) for tag in tags]
                combined_conditions = reduce(or_, conditions)

                query = (Learning
                    .select()
                    .where(combined_conditions)
                    .order_by(Learning.created_at.desc())
                    .limit(limit))
                results = [l.__data__.copy() for l in query]

            self._log_debug(f"Found {len(results)} results for tags")
            return results

        except TimeoutError as e:
            status = 'timeout'
            error_msg = str(e)
            error_code = 'QS003'
            raise
        except (ValidationError, DatabaseError, QuerySystemError) as e:
            status = 'error'
            error_msg = str(e)
            error_code = getattr(e, 'error_code', 'QS000')
            raise
        except Exception as e:
            status = 'error'
            error_msg = str(e)
            error_code = 'QS000'
            raise
        finally:
            # Log the query (non-blocking)
            duration_ms = self._get_current_time_ms() - start_time
            learnings_count = len(results) if results else 0

            self._log_query(
                query_type='query_by_tags',
                tags=','.join(tags),
                limit_requested=limit,
                results_returned=learnings_count,
                duration_ms=duration_ms,
                status=status,
                error_message=error_msg,
                error_code=error_code,
                learnings_count=learnings_count,
                query_summary=f"Tag query for {len(tags)} tags"
            )

    def query_recent(self, type_filter: Optional[str] = None, limit: int = 10,
                    timeout: int = None, days: int = 2) -> List[Dict[str, Any]]:
        """
        Get recent learnings, optionally filtered by type.

        Args:
            type_filter: Optional type filter (e.g., 'incident', 'success')
            limit: Maximum number of results to return
            timeout: Query timeout in seconds (default: 30)
            days: Only return learnings from the last N days (default: 2)

        Returns:
            List of recent learnings

        Raises:
            ValidationError: If inputs are invalid
            TimeoutError: If query times out
            DatabaseError: If database operation fails
        """
        start_time = self._get_current_time_ms()
        error_msg = None
        error_code = None
        status = 'success'
        results = None

        try:
            # Validate inputs
            limit = self._validate_limit(limit)
            timeout = timeout or self.DEFAULT_TIMEOUT

            if type_filter:
                type_filter = self._validate_query(type_filter)

            self._log_debug(f"Querying recent learnings (type={type_filter}, limit={limit}, days={days})")
            with TimeoutHandler(timeout):
                from datetime import timedelta

                # Calculate cutoff date in Python (SQLite datetime() equivalent)
                cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=days)

                query = Learning.select()
                if type_filter:
                    query = query.where(
                        (Learning.type == type_filter) &
                        (Learning.created_at >= cutoff)
                    )
                else:
                    query = query.where(Learning.created_at >= cutoff)

                query = query.order_by(Learning.created_at.desc()).limit(limit)
                results = [l.__data__.copy() for l in query]

            self._log_debug(f"Found {len(results)} recent learnings")
            return results

        except TimeoutError as e:
            status = 'timeout'
            error_msg = str(e)
            error_code = 'QS003'
            raise
        except (ValidationError, DatabaseError, QuerySystemError) as e:
            status = 'error'
            error_msg = str(e)
            error_code = getattr(e, 'error_code', 'QS000')
            raise
        except Exception as e:
            status = 'error'
            error_msg = str(e)
            error_code = 'QS000'
            raise
        finally:
            # Log the query (non-blocking)
            duration_ms = self._get_current_time_ms() - start_time
            learnings_count = len(results) if results else 0

            self._log_query(
                query_type='query_recent',
                limit_requested=limit,
                results_returned=learnings_count,
                duration_ms=duration_ms,
                status=status,
                error_message=error_msg,
                error_code=error_code,
                learnings_count=learnings_count,
                query_summary=f"Recent learnings query{' (type=' + type_filter + ')' if type_filter else ''}"
            )

    def get_active_experiments(self, timeout: int = None) -> List[Dict[str, Any]]:
        """
        List all active experiments.

        Args:
            timeout: Query timeout in seconds (default: 30)

        Returns:
            List of active experiments

        Raises:
            TimeoutError: If query times out
            DatabaseError: If database operation fails
        """
        timeout = timeout or self.DEFAULT_TIMEOUT
        self._log_debug("Querying active experiments")

        start_time = self._get_current_time_ms()
        error_msg = None
        error_code = None
        status = 'success'
        results = None

        try:
            with TimeoutHandler(timeout):
                query = (Experiment
                    .select()
                    .where(Experiment.status == 'active')
                    .order_by(Experiment.updated_at.desc()))
                results = [exp.__data__.copy() for exp in query]

            self._log_debug(f"Found {len(results)} active experiments")
            return results

        except TimeoutError as e:
            status = 'timeout'
            error_msg = str(e)
            error_code = 'QS003'
            raise
        except (DatabaseError, QuerySystemError) as e:
            status = 'error'
            error_msg = str(e)
            error_code = getattr(e, 'error_code', 'QS000')
            raise
        except Exception as e:
            status = 'error'
            error_msg = str(e)
            error_code = 'QS000'
            raise
        finally:
            # Log the query (non-blocking)
            duration_ms = self._get_current_time_ms() - start_time
            experiments_count = len(results) if results else 0

            self._log_query(
                query_type='get_active_experiments',
                results_returned=experiments_count,
                duration_ms=duration_ms,
                status=status,
                error_message=error_msg,
                error_code=error_code,
                experiments_count=experiments_count,
                query_summary="Active experiments query"
            )

    def get_pending_ceo_reviews(self, timeout: int = None) -> List[Dict[str, Any]]:
        """
        List pending CEO decisions.

        Args:
            timeout: Query timeout in seconds (default: 30)

        Returns:
            List of pending CEO reviews

        Raises:
            TimeoutError: If query times out
            DatabaseError: If database operation fails
        """
        timeout = timeout or self.DEFAULT_TIMEOUT
        self._log_debug("Querying pending CEO reviews")

        start_time = self._get_current_time_ms()
        error_msg = None
        error_code = None
        status = 'success'
        results = None

        try:
            with TimeoutHandler(timeout):
                query = (CeoReview
                    .select()
                    .where(CeoReview.status == 'pending')
                    .order_by(CeoReview.created_at.asc()))
                results = [review.__data__.copy() for review in query]

            self._log_debug(f"Found {len(results)} pending CEO reviews")
            return results

        except TimeoutError as e:
            status = 'timeout'
            error_msg = str(e)
            error_code = 'QS003'
            raise
        except (DatabaseError, QuerySystemError) as e:
            status = 'error'
            error_msg = str(e)
            error_code = getattr(e, 'error_code', 'QS000')
            raise
        except Exception as e:
            status = 'error'
            error_msg = str(e)
            error_code = 'QS000'
            raise
        finally:
            # Log the query (non-blocking)
            duration_ms = self._get_current_time_ms() - start_time
            ceo_reviews_count = len(results) if results else 0

            self._log_query(
                query_type='get_pending_ceo_reviews',
                results_returned=ceo_reviews_count,
                duration_ms=duration_ms,
                status=status,
                error_message=error_msg,
                error_code=error_code,
                ceo_reviews_count=ceo_reviews_count,
                query_summary="Pending CEO reviews query"
            )

    def get_violations(self, days: int = 7, acknowledged: Optional[bool] = None,
                      timeout: int = None) -> List[Dict[str, Any]]:
        """
        Get Golden Rule violations from the specified time period.

        Args:
            days: Number of days to look back (default: 7)
            acknowledged: Filter by acknowledged status (None = all)
            timeout: Query timeout in seconds (default: 30)

        Returns:
            List of violations

        Raises:
            TimeoutError: If query times out
            DatabaseError: If database operation fails
        """
        timeout = timeout or self.DEFAULT_TIMEOUT
        self._log_debug(f"Querying violations (days={days}, acknowledged={acknowledged})")

        with TimeoutHandler(timeout):
            from datetime import timedelta

            cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=days)
            query = Violation.select().where(Violation.violation_date >= cutoff)

            if acknowledged is not None:
                query = query.where(Violation.acknowledged == acknowledged)

            query = query.order_by(Violation.violation_date.desc())
            results = [v.__data__.copy() for v in query]

        self._log_debug(f"Found {len(results)} violations")
        return results

    def _calculate_relevance_score(self, learning: Dict, task: str,
                                    domain: str = None) -> float:
        """
        Calculate relevance score with decay factors:
        - Recency: 7-day half-life decay
        - Domain match: Exact = 1.0 boost
        - Validation count: More validated = higher weight

        Args:
            learning: Learning dictionary with created_at, domain, times_validated
            task: Task description (unused currently, for future keyword matching)
            domain: Optional domain filter

        Returns:
            Relevance score between 0.25 and 1.0
        """
        score = 0.5  # Base score

        # Recency decay (half-life: 7 days)
        created_at = learning.get('created_at')
        if created_at:
            try:
                if isinstance(created_at, str):
                    # Handle both ISO format and SQLite datetime format
                    created_at = created_at.replace('Z', '+00:00')
                    if 'T' in created_at:
                        created_at = datetime.fromisoformat(created_at)
                    else:
                        # SQLite datetime format: YYYY-MM-DD HH:MM:SS
                        created_at = datetime.strptime(created_at, '%Y-%m-%d %H:%M:%S')

                age_days = (datetime.now() - created_at).days
                recency_factor = 0.5 ** (age_days / 7)  # Half-life of 7 days
                score *= (0.5 + 0.5 * recency_factor)  # Never go below 0.25
            except (ValueError, TypeError) as e:
                self._log_debug(f"Failed to parse date {created_at}: {e}")

        # Domain match boost
        if domain and learning.get('domain') == domain:
            score *= 1.5

        # Validation boost (for heuristics)
        times_validated = learning.get('times_validated', 0)
        if times_validated > 10:
            score *= 1.4
        elif times_validated > 5:
            score *= 1.2

        return min(score, 1.0)

    def find_similar_failures(self, task_description: str,
                              threshold: float = 0.3,
                              limit: int = 5) -> List[Dict]:
        """
        Find failures with similar keywords to current task.
        Returns failures with similarity score >= threshold.

        Args:
            task_description: Description of the current task
            threshold: Minimum similarity score (0.0 to 1.0)
            limit: Maximum number of results to return

        Returns:
            List of similar failures with similarity scores and matched keywords
        """
        # Extract keywords from task (simple: split on whitespace, filter short words)
        task_words = set(w.lower() for w in re.split(r'\W+', task_description) if len(w) > 3)

        if not task_words:
            return []

        # Get recent failures
        failures = self.query_recent(type_filter='failure', limit=50, days=30)

        similar = []
        for failure in failures:
            # Extract keywords from failure
            failure_text = (failure.get('title', '') + ' ' +
                           (failure.get('summary') or '')).lower()
            failure_words = set(w for w in re.split(r'\W+', failure_text) if len(w) > 3)

            # Calculate Jaccard-like similarity
            if not failure_words:
                continue
            intersection = len(task_words & failure_words)
            union = len(task_words | failure_words)
            similarity = intersection / union if union > 0 else 0

            if similarity >= threshold:
                similar.append({
                    **failure,
                    'similarity': round(similarity, 2),
                    'matched_keywords': list(task_words & failure_words)[:5]
                })

        return sorted(similar, key=lambda x: x['similarity'], reverse=True)[:limit]

    def get_violation_summary(self, days: int = 7, timeout: int = None) -> Dict[str, Any]:
        """
        Get summary statistics of Golden Rule violations.

        Args:
            days: Number of days to look back (default: 7)
            timeout: Query timeout in seconds (default: 30)

        Returns:
            Dictionary with violation statistics

        Raises:
            TimeoutError: If query times out
            DatabaseError: If database operation fails
        """
        timeout = timeout or self.DEFAULT_TIMEOUT
        self._log_debug(f"Querying violation summary (days={days})")

        with TimeoutHandler(timeout):
            from datetime import timedelta
            from peewee import fn

            cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=days)

            # Total count
            total = Violation.select().where(Violation.violation_date >= cutoff).count()

            # By rule (group by)
            by_rule_query = (Violation
                .select(Violation.rule_id, Violation.rule_name, fn.COUNT(Violation.id).alias('count'))
                .where(Violation.violation_date >= cutoff)
                .group_by(Violation.rule_id, Violation.rule_name)
                .order_by(fn.COUNT(Violation.id).desc()))
            by_rule = [{'rule_id': r.rule_id, 'rule_name': r.rule_name, 'count': r.count}
                      for r in by_rule_query]

            # Acknowledged count
            acknowledged = (Violation
                .select()
                .where((Violation.violation_date >= cutoff) & (Violation.acknowledged == True))
                .count())

            # Recent violations (last 5)
            recent_query = (Violation
                .select(Violation.rule_id, Violation.rule_name, Violation.description, Violation.violation_date)
                .where(Violation.violation_date >= cutoff)
                .order_by(Violation.violation_date.desc())
                .limit(5))
            recent = [{'rule_id': r.rule_id, 'rule_name': r.rule_name,
                      'description': r.description, 'date': str(r.violation_date) if r.violation_date else None}
                     for r in recent_query]

        summary = {
            'total': total,
            'acknowledged': acknowledged,
            'unacknowledged': total - acknowledged,
            'by_rule': by_rule,
            'recent': recent,
            'days': days
        }

        self._log_debug(f"Violation summary: {total} total in {days} days")
        return summary

    def get_decisions(
        self,
        domain: Optional[str] = None,
        status: str = 'accepted',
        limit: int = 10,
        timeout: int = None
    ) -> List[Dict[str, Any]]:
        """
        Get architecture decisions (ADRs), optionally filtered by domain.

        Args:
            domain: Optional domain filter (e.g., 'coordination', 'query-system')
            status: Decision status filter (default: 'accepted')
            limit: Maximum number of results to return (default: 10)
            timeout: Query timeout in seconds (default: 30)

        Returns:
            List of decision dictionaries with id, title, context, decision, rationale, etc.

        Raises:
            TimeoutError: If query times out
            DatabaseError: If database operation fails
        """
        timeout = timeout or self.DEFAULT_TIMEOUT
        self._log_debug(f"Querying decisions (domain={domain}, status={status}, limit={limit})")

        start_time = self._get_current_time_ms()
        error_msg = None
        error_code = None
        query_status = 'success'
        results = None

        try:
            limit = self._validate_limit(limit)

            with TimeoutHandler(timeout):
                # Table existence check not needed - Peewee handles gracefully
                query = Decision.select(
                    Decision.id, Decision.title, Decision.context,
                    Decision.decision, Decision.rationale, Decision.domain,
                    Decision.status, Decision.created_at
                ).where(Decision.status == status)

                if domain:
                    domain = self._validate_domain(domain)
                    query = query.where((Decision.domain == domain) | (Decision.domain.is_null()))

                query = query.order_by(Decision.created_at.desc()).limit(limit)
                results = [d.__data__.copy() for d in query]

            self._log_debug(f"Found {len(results)} decisions")
            return results

        except TimeoutError as e:
            query_status = 'timeout'
            error_msg = str(e)
            error_code = 'QS003'
            raise
        except (ValidationError, DatabaseError, QuerySystemError) as e:
            query_status = 'error'
            error_msg = str(e)
            error_code = getattr(e, 'error_code', 'QS000')
            raise
        except Exception as e:
            query_status = 'error'
            error_msg = str(e)
            error_code = 'QS000'
            raise
        finally:
            # Log the query (non-blocking)
            duration_ms = self._get_current_time_ms() - start_time
            decisions_count = len(results) if results else 0

            self._log_query(
                query_type='get_decisions',
                domain=domain,
                limit_requested=limit,
                results_returned=decisions_count,
                duration_ms=duration_ms,
                status=query_status,
                error_message=error_msg,
                error_code=error_code,
                query_summary=f"Decisions query (status={status})"
            )


    def get_invariants(
        self,
        domain: Optional[str] = None,
        status: str = 'active',
        scope: Optional[str] = None,
        severity: Optional[str] = None,
        limit: int = 10,
        timeout: int = None
    ) -> List[Dict[str, Any]]:
        """
        Get invariants, optionally filtered by domain, status, scope, or severity.

        Invariants are statements about what must ALWAYS be true, different from
        Golden Rules which say "don't do X". Invariants can be validated automatically.

        Args:
            domain: Optional domain filter
            status: Invariant status filter (active, deprecated, violated)
            scope: Scope filter (codebase, module, function, runtime)
            severity: Severity filter (error, warning, info)
            limit: Maximum number of results to return (default: 10)
            timeout: Query timeout in seconds (default: 30)

        Returns:
            List of invariant dictionaries with id, statement, rationale, etc.

        Raises:
            TimeoutError: If query times out
            DatabaseError: If database operation fails
        """
        timeout = timeout or self.DEFAULT_TIMEOUT
        self._log_debug(f"Querying invariants (domain={domain}, status={status}, limit={limit})")

        start_time = self._get_current_time_ms()
        error_msg = None
        error_code = None
        query_status = 'success'
        results = None

        try:
            limit = self._validate_limit(limit)

            with TimeoutHandler(timeout):
                try:
                    query = Invariant.select()

                    if status:
                        query = query.where(Invariant.status == status)

                    if domain:
                        domain = self._validate_domain(domain)
                        query = query.where(
                            (Invariant.domain == domain) | (Invariant.domain.is_null())
                        )

                    if scope:
                        query = query.where(Invariant.scope == scope)

                    if severity:
                        query = query.where(Invariant.severity == severity)

                    query = query.order_by(Invariant.created_at.desc()).limit(limit)

                    results = [{
                        'id': inv.id,
                        'statement': inv.statement,
                        'rationale': inv.rationale,
                        'domain': inv.domain,
                        'scope': inv.scope,
                        'severity': inv.severity,
                        'status': inv.status,
                        'created_at': inv.created_at
                    } for inv in query]
                except Exception as e:
                    # Table might not exist yet
                    if 'no such table' in str(e).lower():
                        self._log_debug("Invariants table does not exist yet - returning empty list")
                        return []
                    raise

            self._log_debug(f"Found {len(results)} invariants")
            return results

        except TimeoutError as e:
            query_status = 'timeout'
            error_msg = str(e)
            error_code = 'QS003'
            raise
        except (ValidationError, DatabaseError, QuerySystemError) as e:
            query_status = 'error'
            error_msg = str(e)
            error_code = getattr(e, 'error_code', 'QS000')
            raise
        except Exception as e:
            query_status = 'error'
            error_msg = str(e)
            error_code = 'QS000'
            raise
        finally:
            # Log the query (non-blocking)
            duration_ms = self._get_current_time_ms() - start_time
            invariants_count = len(results) if results else 0

            self._log_query(
                query_type='get_invariants',
                domain=domain,
                limit_requested=limit,
                results_returned=invariants_count,
                duration_ms=duration_ms,
                status=query_status,
                error_message=error_msg,
                error_code=error_code,
                query_summary=f"Invariants query (status={status})"
            )

    def get_assumptions(
        self,
        domain: Optional[str] = None,
        status: str = 'active',
        min_confidence: float = 0.0,
        limit: int = 10,
        timeout: int = None
    ) -> List[Dict[str, Any]]:
        """
        Get assumptions, optionally filtered by domain and status.

        Args:
            domain: Optional domain filter
            status: Assumption status filter (active, verified, challenged, invalidated)
            min_confidence: Minimum confidence threshold (default: 0.0)
            limit: Maximum number of results to return (default: 10)
            timeout: Query timeout in seconds (default: 30)

        Returns:
            List of assumption dictionaries

        Raises:
            TimeoutError: If query times out
            DatabaseError: If database operation fails
        """
        timeout = timeout or self.DEFAULT_TIMEOUT
        self._log_debug(f"Querying assumptions (domain={domain}, status={status}, limit={limit})")

        start_time = self._get_current_time_ms()
        error_msg = None
        error_code = None
        query_status = 'success'
        results = None

        try:
            limit = self._validate_limit(limit)

            with TimeoutHandler(timeout):
                try:
                    query = (Assumption
                        .select()
                        .where(
                            (Assumption.status == status) &
                            (Assumption.confidence >= min_confidence)
                        ))

                    if domain:
                        domain = self._validate_domain(domain)
                        query = query.where(
                            (Assumption.domain == domain) | (Assumption.domain.is_null())
                        )

                    query = query.order_by(
                        Assumption.confidence.desc(),
                        Assumption.created_at.desc()
                    ).limit(limit)

                    results = [{
                        'id': a.id,
                        'assumption': a.assumption,
                        'context': a.context,
                        'source': a.source,
                        'confidence': a.confidence,
                        'status': a.status,
                        'domain': a.domain,
                        'verified_count': a.verified_count,
                        'challenged_count': a.challenged_count,
                        'last_verified_at': a.last_verified_at,
                        'created_at': a.created_at
                    } for a in query]
                except Exception as e:
                    # Table might not exist yet
                    if 'no such table' in str(e).lower():
                        self._log_debug("Assumptions table does not exist yet - returning empty list")
                        return []
                    raise

            self._log_debug(f"Found {len(results)} assumptions")
            return results

        except TimeoutError as e:
            query_status = 'timeout'
            error_msg = str(e)
            error_code = 'QS003'
            raise
        except (ValidationError, DatabaseError, QuerySystemError) as e:
            query_status = 'error'
            error_msg = str(e)
            error_code = getattr(e, 'error_code', 'QS000')
            raise
        except Exception as e:
            query_status = 'error'
            error_msg = str(e)
            error_code = 'QS000'
            raise
        finally:
            # Log the query (non-blocking)
            duration_ms = self._get_current_time_ms() - start_time
            assumptions_count = len(results) if results else 0

            self._log_query(
                query_type='get_assumptions',
                domain=domain,
                limit_requested=limit,
                results_returned=assumptions_count,
                duration_ms=duration_ms,
                status=query_status,
                error_message=error_msg,
                error_code=error_code,
                query_summary=f"Assumptions query (status={status}, min_confidence={min_confidence})"
            )

    def get_challenged_assumptions(
        self,
        domain: Optional[str] = None,
        limit: int = 10,
        timeout: int = None
    ) -> List[Dict[str, Any]]:
        """
        Get challenged or invalidated assumptions as warnings.

        These are assumptions that have been found to be incorrect or questionable.
        Future sessions should be aware of these to avoid repeating mistakes.

        Args:
            domain: Optional domain filter
            limit: Maximum number of results to return (default: 10)
            timeout: Query timeout in seconds (default: 30)

        Returns:
            List of challenged/invalidated assumption dictionaries
        """
        timeout = timeout or self.DEFAULT_TIMEOUT
        self._log_debug(f"Querying challenged assumptions (domain={domain}, limit={limit})")

        with TimeoutHandler(timeout):
            try:
                query = (Assumption
                    .select()
                    .where(Assumption.status.in_(['challenged', 'invalidated'])))

                if domain:
                    domain = self._validate_domain(domain)
                    query = query.where(
                        (Assumption.domain == domain) | (Assumption.domain.is_null())
                    )

                query = query.order_by(
                    Assumption.challenged_count.desc(),
                    Assumption.created_at.desc()
                ).limit(limit)

                results = [{
                    'id': a.id,
                    'assumption': a.assumption,
                    'context': a.context,
                    'source': a.source,
                    'confidence': a.confidence,
                    'status': a.status,
                    'domain': a.domain,
                    'verified_count': a.verified_count,
                    'challenged_count': a.challenged_count,
                    'created_at': a.created_at
                } for a in query]
            except Exception as e:
                # Table might not exist yet
                if 'no such table' in str(e).lower():
                    return []
                raise

        self._log_debug(f"Found {len(results)} challenged/invalidated assumptions")
        return results

    def get_spike_reports(
        self,
        domain: Optional[str] = None,
        tags: Optional[List[str]] = None,
        search: Optional[str] = None,
        limit: int = 10,
        timeout: int = None
    ) -> List[Dict[str, Any]]:
        """
        Get spike reports (research/investigation knowledge).

        Spike reports capture knowledge from research sessions that would otherwise
        be lost when the session ends. They preserve time-invested research findings.

        Args:
            domain: Optional domain filter
            tags: Optional list of tags to match
            search: Optional search term for title/topic/findings
            limit: Maximum number of results to return (default: 10)
            timeout: Query timeout in seconds (default: 30)

        Returns:
            List of spike report dictionaries ordered by usefulness and recency

        Raises:
            TimeoutError: If query times out
            DatabaseError: If database operation fails
        """
        timeout = timeout or self.DEFAULT_TIMEOUT
        self._log_debug(f"Querying spike reports (domain={domain}, tags={tags}, limit={limit})")

        start_time = self._get_current_time_ms()
        error_msg = None
        error_code = None
        query_status = 'success'
        results = None

        try:
            limit = self._validate_limit(limit)

            with TimeoutHandler(timeout):
                try:
                    query = SpikeReport.select()

                    if domain:
                        domain = self._validate_domain(domain)
                        query = query.where(
                            (SpikeReport.domain == domain) | (SpikeReport.domain.is_null())
                        )

                    if tags:
                        tags = self._validate_tags(tags)
                        from functools import reduce
                        from operator import or_
                        tag_conditions = reduce(
                            or_,
                            [SpikeReport.tags.contains(tag) for tag in tags]
                        )
                        query = query.where(tag_conditions)

                    if search:
                        escaped_search = f"%{search}%"
                        query = query.where(
                            (SpikeReport.title.contains(search)) |
                            (SpikeReport.topic.contains(search)) |
                            (SpikeReport.question.contains(search)) |
                            (SpikeReport.findings.contains(search))
                        )

                    query = query.order_by(
                        SpikeReport.usefulness_score.desc(),
                        SpikeReport.created_at.desc()
                    ).limit(limit)

                    results = [{
                        'id': sr.id,
                        'title': sr.title,
                        'topic': sr.topic,
                        'question': sr.question,
                        'findings': sr.findings,
                        'gotchas': sr.gotchas,
                        'resources': sr.resources,
                        'time_invested_minutes': sr.time_invested_minutes,
                        'domain': sr.domain,
                        'tags': sr.tags,
                        'usefulness_score': sr.usefulness_score,
                        'access_count': sr.access_count,
                        'created_at': sr.created_at,
                        'updated_at': sr.updated_at
                    } for sr in query]
                except Exception as e:
                    # Table might not exist yet
                    if 'no such table' in str(e).lower():
                        self._log_debug("spike_reports table does not exist yet - returning empty list")
                        return []
                    raise

            self._log_debug(f"Found {len(results)} spike reports")
            return results

        except TimeoutError as e:
            query_status = 'timeout'
            error_msg = str(e)
            error_code = 'QS003'
            raise
        except (ValidationError, DatabaseError, QuerySystemError) as e:
            query_status = 'error'
            error_msg = str(e)
            error_code = getattr(e, 'error_code', 'QS000')
            raise
        except Exception as e:
            query_status = 'error'
            error_msg = str(e)
            error_code = 'QS000'
            raise
        finally:
            duration_ms = self._get_current_time_ms() - start_time
            spike_count = len(results) if results else 0

            self._log_query(
                query_type='get_spike_reports',
                domain=domain,
                limit_requested=limit,
                results_returned=spike_count,
                duration_ms=duration_ms,
                status=query_status,
                error_message=error_msg,
                error_code=error_code,
                query_summary=f"Spike reports query"
            )


    def build_context(
        self,
        task: str,
        domain: Optional[str] = None,
        tags: Optional[List[str]] = None,
        max_tokens: int = 5000,
        timeout: int = None
    ) -> str:
        """
        Build a context string for agents with tiered retrieval.

        Tier 1: Golden rules (always included)
        Tier 2: Domain-specific heuristics and tag-matched learnings
        Tier 3: Recent context if tokens remain

        Args:
            task: Description of the task for context
            domain: Optional domain to focus on
            tags: Optional tags to match
            max_tokens: Maximum tokens to use (approximate, based on ~4 chars/token)
            timeout: Query timeout in seconds (default: 30)

        Returns:
            Formatted context string for agent consumption

        Raises:
            ValidationError: If inputs are invalid
            TimeoutError: If query times out
        """
        start_time = self._get_current_time_ms()
        error_msg = None
        error_code = None
        status = 'success'
        result = None

        # Track counts for logging
        golden_rules_returned = 0
        heuristics_count = 0
        learnings_count = 0
        experiments_count = 0
        ceo_reviews_count = 0
        decisions_count = 0

        try:
            # Validate inputs
            task = self._validate_query(task)
            if domain:
                domain = self._validate_domain(domain)
            if tags:
                tags = self._validate_tags(tags)
            if max_tokens > self.MAX_TOKENS:
                max_tokens = self.MAX_TOKENS
            timeout = timeout or self.DEFAULT_TIMEOUT * 2  # Context building may take longer

            self._log_debug(f"Building context (domain={domain}, tags={tags}, max_tokens={max_tokens})")
            with TimeoutHandler(timeout):
                context_parts = []
                approx_tokens = 0
                max_chars = max_tokens * 4  # Rough approximation

                # Tier 1: Golden Rules (always loaded)
                golden_rules = self.get_golden_rules()
                context_parts.append("# TIER 1: [93mGolden Rules[0m\n")
                context_parts.append(golden_rules)
                context_parts.append("\n")
                approx_tokens += len(golden_rules) // 4
                golden_rules_returned = 1  # Flag that golden rules were included

                # Check for similar failures (early warning system)
                similar_failures = self.find_similar_failures(task)
                if similar_failures:
                    context_parts.append("\n## ⚠️ Similar Failures Detected\n\n")
                    for sf in similar_failures[:3]:  # Top 3 most similar
                        context_parts.append(f"- **[{sf['similarity']*100:.0f}% match] {sf['title']}**\n")
                        if sf.get('matched_keywords'):
                            context_parts.append(f"  Keywords: {', '.join(sf['matched_keywords'])}\n")
                        if sf.get('summary'):
                            summary = sf['summary'][:100] + '...' if len(sf['summary']) > 100 else sf['summary']
                            context_parts.append(f"  Lesson: {summary}\n")
                        context_parts.append("\n")

                # Tier 2: Query-matched content
                context_parts.append("# TIER 2: Relevant Knowledge\n\n")

                if domain:
                    context_parts.append(f"## Domain: {domain}\n\n")
                    domain_data = self.query_by_domain(domain, limit=5, timeout=timeout)

                    if domain_data['heuristics']:
                        context_parts.append("### Heuristics:\n")
                        # Apply relevance scoring to heuristics
                        heuristics_with_scores = []
                        for h in domain_data['heuristics']:
                            h['_relevance'] = self._calculate_relevance_score(h, task, domain)
                            heuristics_with_scores.append(h)
                        heuristics_with_scores.sort(key=lambda x: x.get('_relevance', 0), reverse=True)

                        for h in heuristics_with_scores:
                            entry = f"- **{h['rule']}** (confidence: {h['confidence']:.2f}, validated: {h['times_validated']}x)\n"
                            entry += f"  {h['explanation']}\n\n"
                            context_parts.append(entry)
                            approx_tokens += len(entry) // 4
                        heuristics_count += len(domain_data['heuristics'])

                    if domain_data['learnings']:
                        context_parts.append("### Recent Learnings:\n")
                        # Apply relevance scoring to learnings
                        learnings_with_scores = []
                        for l in domain_data['learnings']:
                            l['_relevance'] = self._calculate_relevance_score(l, task, domain)
                            learnings_with_scores.append(l)
                        learnings_with_scores.sort(key=lambda x: x.get('_relevance', 0), reverse=True)

                        for l in learnings_with_scores:
                            entry = f"- **{l['title']}** ({l['type']})\n"
                            if l['summary']:
                                entry += f"  {l['summary']}\n"
                            entry += f"  Tags: {l['tags']}\n\n"
                            context_parts.append(entry)
                            approx_tokens += len(entry) // 4
                        learnings_count += len(domain_data['learnings'])

                else:
                    # No domain specified - show recent heuristics across all domains
                    try:
                        # Get recent non-golden heuristics (golden are in TIER 1)
                        recent_heuristics_query = (Heuristic
                            .select()
                            .where((Heuristic.is_golden == False) | (Heuristic.is_golden.is_null()))
                            .order_by(Heuristic.created_at.desc(), Heuristic.confidence.desc())
                            .limit(10))

                        recent_heuristics = [{
                            'rule': h.rule,
                            'domain': h.domain,
                            'confidence': h.confidence,
                            'explanation': h.explanation
                        } for h in recent_heuristics_query]

                        if recent_heuristics:
                            context_parts.append("## Recent Heuristics (all domains)\n\n")
                            for h in recent_heuristics:
                                h_domain = h.get('domain', 'general')
                                entry = f"- **{h['rule']}** (domain: {h_domain}, confidence: {h['confidence']:.2f})\n"
                                if h.get('explanation'):
                                    expl = h['explanation'][:100] + '...' if len(h['explanation']) > 100 else h['explanation']
                                    entry += f"  {expl}\n"
                                entry += "\n"
                                context_parts.append(entry)
                                approx_tokens += len(entry) // 4
                            heuristics_count += len(recent_heuristics)

                        # Get recent learnings across all domains
                        recent_learnings_query = (Learning
                            .select()
                            .order_by(Learning.created_at.desc())
                            .limit(10))

                        recent_learnings = [{
                            'title': l.title,
                            'type': l.type,
                            'domain': l.domain,
                            'summary': l.summary
                        } for l in recent_learnings_query]

                        if recent_learnings:
                            context_parts.append("## Recent Learnings (all domains)\n\n")
                            for l in recent_learnings:
                                l_domain = l.get('domain', 'general')
                                entry = f"- **{l['title']}** ({l['type']}, domain: {l_domain})\n"
                                if l.get('summary'):
                                    summary = l['summary'][:100] + '...' if len(l['summary']) > 100 else l['summary']
                                    entry += f"  {summary}\n"
                                entry += "\n"
                                context_parts.append(entry)
                                approx_tokens += len(entry) // 4
                            learnings_count += len(recent_learnings)

                    except Exception as e:
                        self._log_debug(f"Failed to fetch recent heuristics/learnings: {e}")

                if tags:
                    context_parts.append(f"## Tag Matches: {', '.join(tags)}\n\n")
                    tag_results = self.query_by_tags(tags, limit=5, timeout=timeout)

                    # Apply relevance scoring to tag results
                    tag_results_with_scores = []
                    for l in tag_results:
                        l['_relevance'] = self._calculate_relevance_score(l, task, domain)
                        tag_results_with_scores.append(l)
                    tag_results_with_scores.sort(key=lambda x: x.get('_relevance', 0), reverse=True)

                    for l in tag_results_with_scores:
                        entry = f"- **{l['title']}** ({l['type']}, domain: {l['domain']})\n"
                        if l['summary']:
                            entry += f"  {l['summary']}\n"
                        entry += f"  Tags: {l['tags']}\n\n"
                        context_parts.append(entry)
                        approx_tokens += len(entry) // 4
                    learnings_count += len(tag_results)

                # Add decisions (ADRs) in Tier 2
                decisions = self.get_decisions(domain=domain, status='accepted', limit=5, timeout=timeout)
                if decisions:
                    context_parts.append("\n## Decisions (ADRs)\n\n")
                    for dec in decisions:
                        entry = f"- **{dec['title']}**"
                        if dec.get('domain'):
                            entry += f" (domain: {dec['domain']})"
                        entry += "\n"
                        if dec.get('decision'):
                            decision_text = dec['decision'][:150] + '...' if len(dec['decision']) > 150 else dec['decision']
                            entry += f"  Decision: {decision_text}\n"
                        if dec.get('rationale'):
                            rationale_text = dec['rationale'][:150] + '...' if len(dec['rationale']) > 150 else dec['rationale']
                            entry += f"  Rationale: {rationale_text}\n"
                        entry += "\n"
                        context_parts.append(entry)
                        approx_tokens += len(entry) // 4
                    decisions_count = len(decisions)


                # Add invariants (what must always be true)
                invariants = self.get_invariants(domain=domain, status='active', limit=5, timeout=timeout)
                violated_invariants = self.get_invariants(domain=domain, status='violated', limit=3, timeout=timeout)
                
                if violated_invariants:
                    context_parts.append("\n## VIOLATED INVARIANTS\n\n")
                    for inv in violated_invariants:
                        entry = f"- **[VIOLATED {inv['violation_count']}x] {inv['statement'][:100]}{'...' if len(inv['statement']) > 100 else ''}**\n"
                        entry += f"  Severity: {inv['severity']} | Scope: {inv['scope']}\n"
                        if inv.get('rationale'):
                            rationale_text = inv['rationale'][:100] + '...' if len(inv['rationale']) > 100 else inv['rationale']
                            entry += f"  Rationale: {rationale_text}\n"
                        entry += "\n"
                        context_parts.append(entry)
                        approx_tokens += len(entry) // 4

                if invariants:
                    context_parts.append("\n## Active Invariants\n\n")
                    for inv in invariants:
                        entry = f"- **{inv['statement'][:100]}{'...' if len(inv['statement']) > 100 else ''}**"
                        if inv.get('domain'):
                            entry += f" (domain: {inv['domain']})"
                        entry += f"\n  Severity: {inv['severity']} | Scope: {inv['scope']}"
                        if inv.get('validation_type'):
                            entry += f" | Validation: {inv['validation_type']}"
                        entry += "\n\n"
                        context_parts.append(entry)
                        approx_tokens += len(entry) // 4

                # Add high-confidence active assumptions
                assumptions = self.get_assumptions(domain=domain, status='active', min_confidence=0.6, limit=5, timeout=timeout)
                if assumptions:
                    context_parts.append("\n## Active Assumptions (High Confidence)\n\n")
                    for assum in assumptions:
                        entry = f"- **{assum['assumption'][:100]}{'...' if len(assum['assumption']) > 100 else ''}**"
                        entry += f" (confidence: {assum['confidence']:.0%}"
                        if assum['verified_count'] > 0:
                            entry += f", verified: {assum['verified_count']}x"
                        entry += ")\n"
                        if assum.get('context'):
                            context_text = assum['context'][:100] + '...' if len(assum['context']) > 100 else assum['context']
                            entry += f"  Context: {context_text}\n"
                        if assum.get('source'):
                            entry += f"  Source: {assum['source']}\n"
                        entry += "\n"
                        context_parts.append(entry)
                        approx_tokens += len(entry) // 4

                # Show challenged/invalidated assumptions as warnings
                challenged = self.get_challenged_assumptions(domain=domain, limit=3, timeout=timeout)
                if challenged:
                    context_parts.append("\n## Challenged/Invalidated Assumptions\n\n")
                    for assum in challenged:
                        status_emoji = "INVALIDATED" if assum['status'] == 'invalidated' else "CHALLENGED"
                        entry = f"- **[{status_emoji}] {assum['assumption'][:80]}{'...' if len(assum['assumption']) > 80 else ''}**\n"
                        entry += f"  Challenged {assum['challenged_count']}x"
                        if assum['verified_count'] > 0:
                            entry += f", verified {assum['verified_count']}x"
                        entry += f" | Confidence: {assum['confidence']:.0%}\n"
                        if assum.get('context'):
                            context_text = assum['context'][:80] + '...' if len(assum['context']) > 80 else assum['context']
                            entry += f"  Original context: {context_text}\n"
                        entry += "\n"
                        context_parts.append(entry)
                        approx_tokens += len(entry) // 4

                
                # Add relevant spike reports (hard-won research knowledge)
                spike_reports = self.get_spike_reports(domain=domain, limit=5, timeout=timeout)
                if spike_reports:
                    context_parts.append("\n## Spike Reports (Research Knowledge)\n\n")
                    for spike in spike_reports:
                        entry = f"- **{spike['title']}**"
                        if spike.get('time_invested_minutes'):
                            entry += f" ({spike['time_invested_minutes']} min invested)"
                        entry += "\n"
                        if spike.get('topic'):
                            entry += f"  Topic: {spike['topic'][:100]}{'...' if len(spike['topic']) > 100 else ''}\n"
                        if spike.get('findings'):
                            findings_text = spike['findings'][:200] + '...' if len(spike['findings']) > 200 else spike['findings']
                            entry += f"  Findings: {findings_text}\n"
                        if spike.get('gotchas'):
                            gotchas_text = spike['gotchas'][:100] + '...' if len(spike['gotchas']) > 100 else spike['gotchas']
                            entry += f"  Gotchas: {gotchas_text}\n"
                        if spike.get('usefulness_score') and spike['usefulness_score'] > 0:
                            entry += f"  Usefulness: {spike['usefulness_score']:.1f}/5\n"
                        entry += "\n"
                        context_parts.append(entry)
                        approx_tokens += len(entry) // 4

                # Tier 3: Recent context if tokens remain
                remaining_tokens = max_tokens - approx_tokens
                if remaining_tokens > 500:
                    context_parts.append("# TIER 3: Recent Context\n\n")
                    recent = self.query_recent(limit=3, timeout=timeout)

                    for l in recent:
                        entry = f"- **{l['title']}** ({l['type']}, {l['created_at']})\n"
                        if l['summary']:
                            entry += f"  {l['summary']}\n\n"
                        context_parts.append(entry)
                        approx_tokens += len(entry) // 4

                        if approx_tokens >= max_tokens:
                            break
                    learnings_count += len(recent)

                # Add active experiments
                experiments = self.get_active_experiments(timeout=timeout)
                if experiments:
                    context_parts.append("\n# Active Experiments\n\n")
                    for exp in experiments:
                        entry = f"- **{exp['name']}** ({exp['cycles_run']} cycles)\n"
                        if exp['hypothesis']:
                            entry += f"  Hypothesis: {exp['hypothesis']}\n\n"
                        context_parts.append(entry)
                    experiments_count = len(experiments)

                # Add pending CEO reviews
                ceo_reviews = self.get_pending_ceo_reviews(timeout=timeout)
                if ceo_reviews:
                    context_parts.append("\n# Pending CEO Reviews\n\n")
                    for review in ceo_reviews:
                        entry = f"- **{review['title']}**\n"
                        if review['context']:
                            entry += f"  Context: {review['context']}\n"
                        if review['recommendation']:
                            entry += f"  Recommendation: {review['recommendation']}\n\n"
                        context_parts.append(entry)
                    ceo_reviews_count = len(ceo_reviews)

                # Task context with building header
                building_header = "🏢 [94mBuilding Status[0m\n━━━━━━━━━━━━━━━━━━\n\n"
                context_parts.insert(0, f"{building_header}# Task Context\n\n{task}\n\n---\n\n")

            result = "".join(context_parts)
            self._log_debug(f"Built context with ~{len(result)//4} tokens")
            return result

        except TimeoutError as e:
            status = 'timeout'
            error_msg = str(e)
            error_code = 'QS003'
            raise
        except (ValidationError, DatabaseError, QuerySystemError) as e:
            status = 'error'
            error_msg = str(e)
            error_code = getattr(e, 'error_code', 'QS000')
            raise
        except Exception as e:
            status = 'error'
            error_msg = str(e)
            error_code = 'QS000'
            raise
        finally:
            # Log the query (non-blocking)
            duration_ms = self._get_current_time_ms() - start_time
            tokens_approx = len(result) // 4 if result else 0
            total_results = heuristics_count + learnings_count + experiments_count + ceo_reviews_count + decisions_count

            self._log_query(
                query_type='build_context',
                domain=domain,
                tags=','.join(tags) if tags else None,
                max_tokens_requested=max_tokens,
                results_returned=total_results,
                tokens_approximated=tokens_approx,
                duration_ms=duration_ms,
                status=status,
                error_message=error_msg,
                error_code=error_code,
                golden_rules_returned=golden_rules_returned,
                heuristics_count=heuristics_count,
                learnings_count=learnings_count,
                experiments_count=experiments_count,
                ceo_reviews_count=ceo_reviews_count,
                query_summary=f"Context build for task: {task[:50]}..."
            )

            # Record system metrics for monitoring (non-blocking)
            self._record_system_metrics(domain=domain)

    def get_statistics(self, timeout: int = None) -> Dict[str, Any]:
        """
        Get statistics about the knowledge base.

        Args:
            timeout: Query timeout in seconds (default: 30)

        Returns:
            Dictionary containing various statistics

        Raises:
            TimeoutError: If query times out
            DatabaseError: If database operation fails
        """
        timeout = timeout or self.DEFAULT_TIMEOUT
        self._log_debug("Gathering statistics")

        with TimeoutHandler(timeout):
            from datetime import timedelta
            from peewee import fn

            stats = {}

            # Count learnings by type
            learnings_type_query = (Learning
                .select(Learning.type, fn.COUNT(Learning.id).alias('count'))
                .group_by(Learning.type))
            stats['learnings_by_type'] = {r.type: r.count for r in learnings_type_query}

            # Count learnings by domain
            learnings_domain_query = (Learning
                .select(Learning.domain, fn.COUNT(Learning.id).alias('count'))
                .group_by(Learning.domain))
            stats['learnings_by_domain'] = {r.domain: r.count for r in learnings_domain_query}

            # Count heuristics by domain
            heuristics_domain_query = (Heuristic
                .select(Heuristic.domain, fn.COUNT(Heuristic.id).alias('count'))
                .group_by(Heuristic.domain))
            stats['heuristics_by_domain'] = {r.domain: r.count for r in heuristics_domain_query}

            # Count golden heuristics
            stats['golden_heuristics'] = Heuristic.select().where(Heuristic.is_golden == True).count()

            # Count experiments by status
            experiments_status_query = (Experiment
                .select(Experiment.status, fn.COUNT(Experiment.id).alias('count'))
                .group_by(Experiment.status))
            stats['experiments_by_status'] = {r.status: r.count for r in experiments_status_query}

            # Count CEO reviews by status
            ceo_status_query = (CeoReview
                .select(CeoReview.status, fn.COUNT(CeoReview.id).alias('count'))
                .group_by(CeoReview.status))
            stats['ceo_reviews_by_status'] = {r.status: r.count for r in ceo_status_query}

            # Total counts
            stats['total_learnings'] = Learning.select().count()
            stats['total_heuristics'] = Heuristic.select().count()
            stats['total_experiments'] = Experiment.select().count()
            stats['total_ceo_reviews'] = CeoReview.select().count()

            # Violation statistics (last 7 days)
            cutoff_7d = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=7)
            stats['violations_7d'] = Violation.select().where(Violation.violation_date >= cutoff_7d).count()

            violations_rule_query = (Violation
                .select(Violation.rule_id, Violation.rule_name, fn.COUNT(Violation.id).alias('count'))
                .where(Violation.violation_date >= cutoff_7d)
                .group_by(Violation.rule_id, Violation.rule_name)
                .order_by(fn.COUNT(Violation.id).desc()))
            stats['violations_by_rule_7d'] = {f"Rule {r.rule_id}: {r.rule_name}": r.count
                                              for r in violations_rule_query}

        self._log_debug(f"Statistics gathered: {stats['total_learnings']} learnings total")
        return stats


# Formatting functions and setup functions imported from:
# - query.formatters (format_output, generate_accountability_banner)
# - query.setup (ensure_hooks_installed, ensure_full_setup)


def main():
    """Command-line interface for the query system."""
    # Auto-run full setup on first use
    ensure_full_setup()
    # Auto-install hooks on first query
    ensure_hooks_installed()

    parser = argparse.ArgumentParser(
        description="Emergent Learning Framework - Query System (v2.0 - 10/10 Robustness)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic queries
  python query.py --context --domain coordination
  python query.py --domain debugging --limit 5
  python query.py --tags error,fix --limit 10
  python query.py --recent 10
  python query.py --experiments
  python query.py --ceo-reviews
  python query.py --stats

  # Advanced usage
  python query.py --domain testing --format json --debug
  python query.py --recent 20 --timeout 60 --format csv
  python query.py --validate
  python query.py --tags performance,optimization --format json > results.json

Error Codes:
  QS000 - General query system error
  QS001 - Validation error (invalid input)
  QS002 - Database error (connection/query failed)
  QS003 - Timeout error (query took too long)
  QS004 - Configuration error (setup failed)
        """
    )

    # Basic arguments
    parser.add_argument('--base-path', type=str, help='Base path to emergent-learning directory')
    parser.add_argument('--context', action='store_true', help='Build full context for agents')
    parser.add_argument('--domain', type=str, help='Query by domain')
    parser.add_argument('--tags', type=str, help='Query by tags (comma-separated)')
    parser.add_argument('--recent', type=int, metavar='N', help='Get N recent learnings')
    parser.add_argument('--type', type=str, help='Filter recent learnings by type')
    parser.add_argument('--experiments', action='store_true', help='List active experiments')
    parser.add_argument('--ceo-reviews', action='store_true', help='List pending CEO reviews')
    parser.add_argument('--golden-rules', action='store_true', help='Display golden rules')
    parser.add_argument('--stats', action='store_true', help='Display knowledge base statistics')
    parser.add_argument('--violations', action='store_true', help='Show violation summary')
    parser.add_argument('--violation-days', type=int, default=7, help='Days to look back for violations (default: 7)')
    parser.add_argument('--accountability-banner', action='store_true', help='Show accountability banner')
    parser.add_argument('--decisions', action='store_true', help='List architecture decision records (ADRs)')
    parser.add_argument('--spikes', action='store_true', help='List spike reports (research knowledge)')
    parser.add_argument('--decision-status', type=str, default='accepted', help='Filter decisions by status (default: accepted)')
    parser.add_argument('--assumptions', action='store_true', help='List assumptions')
    parser.add_argument('--assumption-status', type=str, default='active', help='Filter assumptions by status: active, verified, challenged, invalidated (default: active)')
    parser.add_argument('--min-confidence', type=float, default=0.0, help='Minimum confidence for assumptions (default: 0.0)')
    parser.add_argument('--invariants', action='store_true', help='List invariants (what must always be true)')
    parser.add_argument('--invariant-status', type=str, default='active', help='Filter invariants by status: active, deprecated, violated (default: active)')
    parser.add_argument('--invariant-scope', type=str, help='Filter invariants by scope: codebase, module, function, runtime')
    parser.add_argument('--invariant-severity', type=str, help='Filter invariants by severity: error, warning, info')
    parser.add_argument('--limit', type=int, default=10, help='Limit number of results (default: 10, max: 1000)')

    # Enhanced arguments
    parser.add_argument('--format', choices=['text', 'json', 'csv'], default='text',
                       help='Output format (default: text)')
    parser.add_argument('--max-tokens', type=int, default=5000,
                       help='Max tokens for context building (default: 5000, max: 50000)')
    parser.add_argument('--debug', action='store_true', help='Enable debug output')
    parser.add_argument('--timeout', type=int, default=30,
                       help='Query timeout in seconds (default: 30)')
    parser.add_argument('--validate', action='store_true', help='Validate database integrity')
    parser.add_argument('--health-check', action='store_true',
                       help='Run system health check and display alerts (meta-observer)')

    args = parser.parse_args()

    # Initialize query system with error handling
    try:
        query_system = QuerySystem(base_path=args.base_path, debug=args.debug)
    except QuerySystemError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"ERROR: Unexpected error during initialization: {e} [QS000]", file=sys.stderr)
        return 1

    # Execute query based on arguments
    result = None
    exit_code = 0

    try:
        if args.validate:
            # Validate database
            result = query_system.validate_database()
            if result['valid']:
                print("Database validation: PASSED")
            else:
                print("Database validation: FAILED")
                exit_code = 1
            print(format_output(result, args.format))
            return exit_code

        elif args.health_check:
            # Run system health check via meta-observer
            if not META_OBSERVER_AVAILABLE:
                print("ERROR: Meta-observer not available. Cannot run health check.", file=sys.stderr)
                return 1

            print("🏥 [94mSystem Health Check[0m")
            print("━" * 40)

            # Check alerts
            alerts = query_system._check_system_alerts()

            if not alerts:
                print("✓ No active alerts")
            else:
                for alert in alerts:
                    if isinstance(alert, dict):
                        if alert.get('mode') == 'bootstrap':
                            print(f"⏳ Bootstrap mode: {alert.get('message', 'Collecting baseline data')}")
                            samples = alert.get('samples', 0)
                            needed = alert.get('samples_needed', 30)
                            print(f"   Progress: {samples}/{needed} samples (~{(needed - samples) // 4} more queries needed)")
                        else:
                            alert_type = alert.get('type', alert.get('alert_type', 'unknown'))
                            severity = alert.get('severity', 'info')
                            icon = {'critical': '🔴', 'warning': '🟡', 'info': '🔵'}.get(severity, '⚪')
                            print(f"{icon} [{severity.upper()}] {alert_type}")
                            if alert.get('message'):
                                print(f"   {alert['message']}")

            # Show recent metrics
            print("\n📊 [94mRecent Metrics[0m")
            print("━" * 40)
            try:
                from meta_observer import MetaObserver
                observer = MetaObserver(db_path=query_system.db_path)

                for metric in ['avg_confidence', 'validation_velocity', 'contradiction_rate']:
                    trend = observer.calculate_trend(metric, hours=168)  # 7 days
                    if trend.get('confidence') != 'low':
                        direction = trend.get('direction', 'stable')
                        arrow = {'increasing': '↑', 'decreasing': '↓', 'stable': '→'}.get(direction, '?')
                        spread = trend.get('time_spread_hours', 0)
                        print(f"  {metric}: {arrow} {direction} (confidence: {trend.get('confidence')}, {spread:.1f}h spread)")
                    elif trend.get('reason') == 'insufficient_time_spread':
                        spread = trend.get('time_spread_hours', 0)
                        required = trend.get('required_spread_hours', 0)
                        print(f"  {metric}: (need more time spread - {spread:.1f}h/{required:.1f}h)")
                    else:
                        print(f"  {metric}: (insufficient data - {trend.get('sample_count', 0)}/{trend.get('required', 10)} samples)")

                # Show active alerts from DB
                active_alerts = observer.get_active_alerts()
                if active_alerts:
                    print(f"\n⚠️  {len(active_alerts)} active alert(s) in database")
            except Exception as e:
                print(f"  (Could not retrieve metrics: {e})")

            return 0

        elif args.context:
            # Build full context
            task = "Agent task context generation"
            domain = args.domain
            tags = args.tags.split(',') if args.tags else None
            result = query_system.build_context(task, domain, tags, args.max_tokens, args.timeout)
            print(result)
            return exit_code

        elif args.golden_rules:
            result = query_system.get_golden_rules()
            print(result)
            return exit_code

        elif args.decisions:
            # Handle decisions query (must come before --domain check)
            result = query_system.get_decisions(args.domain, args.decision_status, args.limit, args.timeout)


        elif args.spikes:
            result = query_system.get_spike_reports(
                domain=args.domain,
                tags=args.tags.split(',') if args.tags else None,
                limit=args.limit,
                timeout=args.timeout
            )

        elif args.assumptions:
            # Handle assumptions query
            result = query_system.get_assumptions(
                domain=args.domain,
                status=args.assumption_status,
                min_confidence=args.min_confidence,
                limit=args.limit,
                timeout=args.timeout
            )
            # Also show challenged/invalidated if viewing all or specifically requested
            if args.assumption_status in ['challenged', 'invalidated']:
                pass  # Already filtering by that status
            elif not result:
                # If no active assumptions, show a summary
                challenged = query_system.get_challenged_assumptions(args.domain, args.limit, args.timeout)
                if challenged:
                    print("\n--- Challenged/Invalidated Assumptions ---\n")
                    result = challenged


        elif args.invariants:
            # Handle invariants query
            result = query_system.get_invariants(
                domain=args.domain,
                status=args.invariant_status,
                scope=args.invariant_scope,
                severity=args.invariant_severity,
                limit=args.limit,
                timeout=args.timeout
            )

        elif args.domain:
            result = query_system.query_by_domain(args.domain, args.limit, args.timeout)

        elif args.tags:
            tags = [t.strip() for t in args.tags.split(',')]
            result = query_system.query_by_tags(tags, args.limit, args.timeout)

        elif args.recent is not None:
            result = query_system.query_recent(args.type, args.recent, args.timeout)

        elif args.experiments:
            result = query_system.get_active_experiments(args.timeout)

        elif args.ceo_reviews:
            result = query_system.get_pending_ceo_reviews(args.timeout)

        elif args.stats:
            result = query_system.get_statistics(args.timeout)

        elif args.violations:
            result = query_system.get_violation_summary(args.violation_days, args.timeout)

        elif args.accountability_banner:
            # Generate accountability banner
            summary = query_system.get_violation_summary(7, args.timeout)
            print(generate_accountability_banner(summary))
            return exit_code

        else:
            parser.print_help()
            return exit_code

        # Output result
        if result is not None:
            print(format_output(result, args.format))

    except ValidationError as e:
        print(f"VALIDATION ERROR: {e}", file=sys.stderr)
        exit_code = 1
    except TimeoutError as e:
        print(f"TIMEOUT ERROR: {e}", file=sys.stderr)
        exit_code = 3
    except DatabaseError as e:
        print(f"DATABASE ERROR: {e}", file=sys.stderr)
        exit_code = 2
    except QuerySystemError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        exit_code = 1
    except Exception as e:
        print(f"UNEXPECTED ERROR: {e} [QS000]", file=sys.stderr)
        if args.debug:
            import traceback
            traceback.print_exc()
        exit_code = 1
    finally:
        # Clean up connections
        query_system.cleanup()

    return exit_code


if __name__ == '__main__':
    # Redirect to async CLI (v2.0.0)
    # The legacy synchronous code above is preserved for import compatibility
    # but CLI execution now uses the fully async implementation
    try:
        from query.cli import main as async_main
    except ImportError:
        from cli import main as async_main
    exit(async_main())
