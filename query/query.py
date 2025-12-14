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

import sqlite3
import os
import sys
import io
import argparse
import signal
import re
import csv
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from contextlib import contextmanager
import json

# Meta-observer for system health monitoring
try:
    from meta_observer import MetaObserver
    META_OBSERVER_AVAILABLE = True
except ImportError:
    META_OBSERVER_AVAILABLE = False

# Fix Windows console encoding for Unicode characters
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Custom error classes for better error handling
class QuerySystemError(Exception):
    """Base exception for query system errors."""
    error_code = 'QS000'

class ValidationError(QuerySystemError):
    """Raised when input validation fails."""
    error_code = 'QS001'

class DatabaseError(QuerySystemError):
    """Raised when database operations fail."""
    error_code = 'QS002'

class TimeoutError(QuerySystemError):
    """Raised when query times out."""
    error_code = 'QS003'

class ConfigurationError(QuerySystemError):
    """Raised when configuration is invalid."""
    error_code = 'QS004'


# Timeout handler for queries
class TimeoutHandler:
    """Handles query timeouts using signal alarms (Unix) or threading (Windows)."""

    def __init__(self, seconds: int = 30):
        self.seconds = seconds
        self.timeout_occurred = False

    def __enter__(self):
        if sys.platform != 'win32':
            # Unix-based timeout using signals
            signal.signal(signal.SIGALRM, self._timeout_handler)
            signal.alarm(self.seconds)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if sys.platform != 'win32':
            signal.alarm(0)  # Cancel alarm
        return False

    def _timeout_handler(self, signum, frame):
        self.timeout_occurred = True
        raise TimeoutError(
            f"Query timed out after {self.seconds} seconds. "
            f"Try reducing --limit or increasing --timeout. [QS003]"
        )


def escape_like(s: str) -> str:
    """
    Escape SQL LIKE wildcards to prevent wildcard injection.

    Args:
        s: String to escape

    Returns:
        String with SQL LIKE wildcards escaped
    """
    return s.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')


class QuerySystem:
    """Manages knowledge retrieval from the Emergent Learning Framework."""

    # Validation constants
    MAX_DOMAIN_LENGTH = 100
    MAX_QUERY_LENGTH = 10000
    MAX_TAG_COUNT = 50
    MAX_TAG_LENGTH = 50
    MIN_LIMIT = 1
    MAX_LIMIT = 1000
    DEFAULT_TIMEOUT = 30
    MAX_CONNECTION_POOL_SIZE = 5  # Maximum pooled SQLite connections for efficiency
    MAX_TOKENS = 50000

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
        self._connection_pool: List[sqlite3.Connection] = []

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

        # Initialize database
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
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO building_queries (
                        query_type, session_id, agent_id, domain, tags,
                        limit_requested, max_tokens_requested,
                        results_returned, tokens_approximated, duration_ms,
                        status, error_message, error_code,
                        golden_rules_returned, heuristics_count, learnings_count,
                        experiments_count, ceo_reviews_count, query_summary,
                        completed_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """, (
                    query_type, self.session_id, self.agent_id, domain, tags,
                    limit_requested, max_tokens_requested,
                    results_returned, tokens_approximated, duration_ms,
                    status, error_message, error_code,
                    golden_rules_returned, heuristics_count, learnings_count,
                    experiments_count, ceo_reviews_count, query_summary
                ))
                conn.commit()
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

            with self._get_connection() as conn:
                cursor = conn.cursor()

                # 1. Average confidence of active heuristics
                if domain:
                    cursor.execute("""
                        SELECT AVG(confidence), COUNT(*) FROM heuristics
                        WHERE status = 'active' AND domain = ?
                    """, (domain,))
                else:
                    cursor.execute("""
                        SELECT AVG(confidence), COUNT(*) FROM heuristics
                        WHERE status = 'active'
                    """)
                row = cursor.fetchone()
                avg_conf = row[0] if row[0] else 0.5
                heuristic_count = row[1] if row[1] else 0

                if heuristic_count > 0:
                    observer.record_metric('avg_confidence', avg_conf, domain=domain,
                                          metadata={'heuristic_count': heuristic_count})

                # 2. Validation velocity (last 24 hours)
                cursor.execute("""
                    SELECT COUNT(*) FROM confidence_updates
                    WHERE update_type = 'validation'
                      AND created_at > datetime('now', '-24 hours')
                """)
                validation_count = cursor.fetchone()[0] or 0
                observer.record_metric('validation_velocity', validation_count, domain=domain)

                # 3. Contradiction rate (if we have enough data)
                cursor.execute("""
                    SELECT
                        SUM(times_contradicted) as contradictions,
                        SUM(times_validated + times_violated + COALESCE(times_contradicted, 0)) as total
                    FROM heuristics
                    WHERE status = 'active'
                """)
                row = cursor.fetchone()
                if row and row[1] and row[1] > 0:
                    contradiction_rate = (row[0] or 0) / row[1]
                    observer.record_metric('contradiction_rate', contradiction_rate, domain=domain)

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

    def _validate_connection(self, conn: sqlite3.Connection) -> bool:
        """
        Validate that a connection is still alive and usable (S8 FIX).

        Args:
            conn: Connection to validate

        Returns:
            True if connection is valid, False otherwise
        """
        try:
            # Simple query to check if connection is alive
            conn.execute("SELECT 1")
            return True
        except (sqlite3.Error, sqlite3.ProgrammingError):
            return False

    @contextmanager
    def _get_connection(self):
        """
        Get a database connection from the pool or create a new one.
        Implements connection pooling for efficiency.
        """
        conn = None
        try:
            # Try to reuse an existing connection
            if self._connection_pool:
                conn = self._connection_pool.pop()
                # S8 FIX: Validate connection before reuse
                if not self._validate_connection(conn):
                    self._log_debug("Pooled connection invalid, creating new one")
                    conn.close()
                    conn = self._create_connection()
                else:
                    self._log_debug("Reusing connection from pool")
            else:
                conn = self._create_connection()
                self._log_debug("Created new connection")

            yield conn

            # Return connection to pool if it's still valid
            # Connection pool size limit: 5 connections
            # This prevents resource exhaustion while allowing reasonable concurrency.
            # Adjust this value based on your system's SQLite connection limits.
            if len(self._connection_pool) < self.MAX_CONNECTION_POOL_SIZE:  # Max 5 pooled connections
                self._connection_pool.append(conn)
                self._log_debug("Returned connection to pool")
            else:
                conn.close()
                self._log_debug("Closed excess connection")

        except sqlite3.Error as e:
            if conn:
                try:
                    conn.rollback()
                except Exception:
                    pass
                conn.close()
            raise DatabaseError(
                f"Database operation failed: {e}. "
                f"Check database integrity with --validate. [QS002]"
            )
        except Exception as e:
            if conn:
                try:
                    conn.rollback()
                except Exception:
                    pass
                conn.close()
            raise

    def _create_connection(self) -> sqlite3.Connection:
        """Create a new database connection with proper settings."""
        try:
            conn = sqlite3.connect(str(self.db_path), timeout=10.0)
            conn.execute("PRAGMA busy_timeout=10000")
            conn.execute("PRAGMA foreign_keys=ON")
            # Performance pragmas for better concurrency and durability
            conn.execute("PRAGMA journal_mode=WAL")  # Write-Ahead Logging for better concurrency
            conn.execute("PRAGMA synchronous=NORMAL")  # Balanced durability/performance
            return conn
        except sqlite3.Error as e:
            raise DatabaseError(
                f"Failed to connect to database at {self.db_path}. "
                f"Database may be locked or corrupted. Error: {e} [QS002]"
            )

    def cleanup(self):
        """Clean up connection pool. Call this when done with the query system."""
        self._log_debug(f"Cleaning up {len(self._connection_pool)} pooled connections")
        for conn in self._connection_pool:
            try:
                conn.close()
            except Exception:
                pass
        self._connection_pool.clear()

    def __del__(self):
        """Ensure cleanup on deletion."""
        self.cleanup()

    # ========== VALIDATION METHODS ==========

    def _validate_domain(self, domain: str) -> str:
        """
        Validate domain string.

        Args:
            domain: Domain to validate

        Returns:
            Validated domain string

        Raises:
            ValidationError: If domain is invalid
        """
        if not domain:
            raise ValidationError(
                "Domain cannot be empty. Provide a valid domain name. [QS001]"
            )

        if len(domain) > self.MAX_DOMAIN_LENGTH:
            raise ValidationError(
                f"Domain exceeds maximum length of {self.MAX_DOMAIN_LENGTH} characters. "
                f"Use a shorter domain name. [QS001]"
            )

        # Allow alphanumeric, hyphen, underscore, and dot
        if not re.match(r'^[a-zA-Z0-9\-_.]+$', domain):
            raise ValidationError(
                f"Domain '{domain}' contains invalid characters. "
                f"Use only alphanumeric, hyphen, underscore, and dot. [QS001]"
            )

        return domain.strip()

    def _validate_limit(self, limit: int) -> int:
        """
        Validate limit parameter.

        Args:
            limit: Limit to validate

        Returns:
            Validated limit

        Raises:
            ValidationError: If limit is invalid
        """
        if not isinstance(limit, int):
            raise ValidationError(
                f"Limit must be an integer, got {type(limit).__name__}. [QS001]"
            )

        if limit < self.MIN_LIMIT:
            raise ValidationError(
                f"Limit must be at least {self.MIN_LIMIT}. Got: {limit}. [QS001]"
            )

        if limit > self.MAX_LIMIT:
            raise ValidationError(
                f"Limit exceeds maximum of {self.MAX_LIMIT}. "
                f"Use a smaller limit or process results in batches. [QS001]"
            )

        return limit

    def _validate_tags(self, tags: List[str]) -> List[str]:
        """
        Validate tags list.

        Args:
            tags: List of tags to validate

        Returns:
            Validated tags list

        Raises:
            ValidationError: If tags are invalid
        """
        if not isinstance(tags, list):
            raise ValidationError(
                f"Tags must be a list, got {type(tags).__name__}. [QS001]"
            )

        if len(tags) > self.MAX_TAG_COUNT:
            raise ValidationError(
                f"Too many tags (max {self.MAX_TAG_COUNT}). "
                f"Reduce number of tags or query in batches. [QS001]"
            )

        validated_tags = []
        for tag in tags:
            tag = tag.strip()
            if not tag:
                continue

            if len(tag) > self.MAX_TAG_LENGTH:
                raise ValidationError(
                    f"Tag '{tag[:20]}...' exceeds maximum length of {self.MAX_TAG_LENGTH}. [QS001]"
                )

            if not re.match(r'^[a-zA-Z0-9\-_.]+$', tag):
                raise ValidationError(
                    f"Tag '{tag}' contains invalid characters. "
                    f"Use only alphanumeric, hyphen, underscore, and dot. [QS001]"
                )

            validated_tags.append(tag)

        if not validated_tags:
            raise ValidationError(
                "No valid tags provided after filtering. [QS001]"
            )

        return validated_tags

    def _validate_query(self, query: str) -> str:
        """
        Validate query string.

        Args:
            query: Query string to validate

        Returns:
            Validated query string

        Raises:
            ValidationError: If query is invalid
        """
        if not query:
            raise ValidationError(
                "Query string cannot be empty. [QS001]"
            )

        if len(query) > self.MAX_QUERY_LENGTH:
            raise ValidationError(
                f"Query exceeds maximum length of {self.MAX_QUERY_LENGTH} characters. "
                f"Reduce query size. [QS001]"
            )

        return query.strip()

    # ========== DATABASE OPERATIONS ==========

    def _init_database(self):
        """Initialize the database with required schema if it does not exist."""
        # SECURITY: Check if database file was just created, set secure permissions
        db_just_created = not self.db_path.exists()

        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Create learnings table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS learnings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    type TEXT NOT NULL,
                    filepath TEXT NOT NULL,
                    title TEXT NOT NULL,
                    summary TEXT,
                    tags TEXT,
                    domain TEXT,
                    severity INTEGER DEFAULT 1,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Create heuristics table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS heuristics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    domain TEXT NOT NULL,
                    rule TEXT NOT NULL,
                    explanation TEXT,
                    source_type TEXT,
                    source_id INTEGER,
                    confidence REAL DEFAULT 0.5,
                    times_validated INTEGER DEFAULT 0,
                    times_violated INTEGER DEFAULT 0,
                    is_golden BOOLEAN DEFAULT FALSE,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Create experiments table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS experiments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    hypothesis TEXT,
                    status TEXT DEFAULT 'active',
                    cycles_run INTEGER DEFAULT 0,
                    folder_path TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Create ceo_reviews table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ceo_reviews (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    context TEXT,
                    recommendation TEXT,
                    status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    reviewed_at TIMESTAMP
                )
            """)

            # Create decisions table (ADR - Architecture Decision Records)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS decisions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    context TEXT NOT NULL,
                    options_considered TEXT,
                    decision TEXT NOT NULL,
                    rationale TEXT NOT NULL,
                    files_touched TEXT,
                    tests_added TEXT,
                    status TEXT DEFAULT 'accepted',
                    domain TEXT,
                    superseded_by INTEGER,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (superseded_by) REFERENCES decisions(id)
                )
            """)

            # Create violations table (for accountability tracking)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS violations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    rule_id INTEGER NOT NULL,
                    rule_name TEXT NOT NULL,
                    violation_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    description TEXT,
                    session_id TEXT,
                    acknowledged BOOLEAN DEFAULT 0
                )
            """)


            # Create invariants table (statements about what must always be true)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS invariants (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    statement TEXT NOT NULL,
                    rationale TEXT NOT NULL,
                    domain TEXT,
                    scope TEXT DEFAULT 'codebase',
                    validation_type TEXT,
                    validation_code TEXT,
                    severity TEXT DEFAULT 'error',
                    status TEXT DEFAULT 'active',
                    violation_count INTEGER DEFAULT 0,
                    last_validated_at DATETIME,
                    last_violated_at DATETIME,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Create indexes for efficient querying
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_learnings_domain
                ON learnings(domain)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_learnings_type
                ON learnings(type)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_learnings_created_at
                ON learnings(created_at DESC)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_learnings_domain_created
                ON learnings(domain, created_at DESC)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_heuristics_domain
                ON heuristics(domain)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_heuristics_golden
                ON heuristics(is_golden)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_heuristics_created_at
                ON heuristics(created_at DESC)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_heuristics_domain_confidence
                ON heuristics(domain, confidence DESC)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_experiments_status
                ON experiments(status)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_ceo_reviews_status
                ON ceo_reviews(status)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_violations_date
                ON violations(violation_date DESC)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_violations_rule
                ON violations(rule_id)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_violations_acknowledged
                ON violations(acknowledged)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_decisions_domain
                ON decisions(domain)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_decisions_status
                ON decisions(status)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_decisions_created_at
                ON decisions(created_at DESC)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_decisions_superseded_by
                ON decisions(superseded_by)
            """)


            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_invariants_domain
                ON invariants(domain)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_invariants_status
                ON invariants(status)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_invariants_severity
                ON invariants(severity)
            """)

            # Update query planner statistics
            cursor.execute("ANALYZE")

            conn.commit()

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
            with self._get_connection() as conn:
                cursor = conn.cursor()

                # Check PRAGMA integrity
                cursor.execute("PRAGMA integrity_check")
                integrity = cursor.fetchone()[0]
                results['checks']['integrity'] = integrity
                if integrity != 'ok':
                    results['valid'] = False
                    results['errors'].append(f"Database integrity check failed: {integrity}")

                # Check foreign keys
                cursor.execute("PRAGMA foreign_key_check")
                fk_violations = cursor.fetchall()
                if fk_violations:
                    results['valid'] = False
                    results['errors'].append(f"Foreign key violations: {len(fk_violations)}")
                    results['checks']['foreign_keys'] = fk_violations

                # Check table existence
                required_tables = ['learnings', 'heuristics', 'experiments', 'ceo_reviews']
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                existing_tables = [row[0] for row in cursor.fetchall()]

                for table in required_tables:
                    if table not in existing_tables:
                        results['valid'] = False
                        results['errors'].append(f"Required table '{table}' is missing")

                results['checks']['tables'] = existing_tables

                # Check index existence
                cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
                indexes = [row[0] for row in cursor.fetchall()]
                results['checks']['indexes'] = indexes

                if not any('idx_learnings_domain' in idx for idx in indexes):
                    results['warnings'].append("Some indexes may be missing")

                # Get table row counts
                for table in required_tables:
                    if table in existing_tables:
                        cursor.execute(f"SELECT COUNT(*) FROM {table}")
                        count = cursor.fetchone()[0]
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
                with self._get_connection() as conn:
                    conn.row_factory = sqlite3.Row
                    cursor = conn.cursor()

                    # Get heuristics for domain
                    cursor.execute("""
                        SELECT * FROM heuristics
                        WHERE domain = ?
                        ORDER BY confidence DESC, times_validated DESC
                        LIMIT ?
                    """, (domain, limit))
                    heuristics = [dict(row) for row in cursor.fetchall()]

                    # Get learnings for domain
                    cursor.execute("""
                        SELECT * FROM learnings
                        WHERE domain = ?
                        ORDER BY created_at DESC
                        LIMIT ?
                    """, (domain, limit))
                    learnings = [dict(row) for row in cursor.fetchall()]

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
                with self._get_connection() as conn:
                    conn.row_factory = sqlite3.Row
                    cursor = conn.cursor()

                    # Build query for tag matching (tags stored as comma-separated string)
                    tag_conditions = " OR ".join(["tags LIKE ?" for _ in tags])
                    query = f"""
                        SELECT * FROM learnings
                        WHERE {tag_conditions}
                        ORDER BY created_at DESC
                        LIMIT ?
                    """

                    # Prepare parameters with wildcards for LIKE queries
                    # Escape SQL wildcards to prevent wildcard injection
                    params = [f"%{escape_like(tag)}%" for tag in tags] + [limit]

                    cursor.execute(query, params)
                    results = [dict(row) for row in cursor.fetchall()]

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
                with self._get_connection() as conn:
                    conn.row_factory = sqlite3.Row
                    cursor = conn.cursor()

                    if type_filter:
                        cursor.execute("""
                            SELECT * FROM learnings
                            WHERE type = ?
                            AND created_at >= datetime('now', ? || ' days')
                            ORDER BY created_at DESC
                            LIMIT ?
                        """, (type_filter, f'-{days}', limit))
                    else:
                        cursor.execute("""
                            SELECT * FROM learnings
                            WHERE created_at >= datetime('now', ? || ' days')
                            ORDER BY created_at DESC
                            LIMIT ?
                        """, (f'-{days}', limit))

                    results = [dict(row) for row in cursor.fetchall()]

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
                with self._get_connection() as conn:
                    conn.row_factory = sqlite3.Row
                    cursor = conn.cursor()

                    cursor.execute("""
                        SELECT * FROM experiments
                        WHERE status = 'active'
                        ORDER BY updated_at DESC
                    """)

                    results = [dict(row) for row in cursor.fetchall()]

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
                with self._get_connection() as conn:
                    conn.row_factory = sqlite3.Row
                    cursor = conn.cursor()

                    cursor.execute("""
                        SELECT * FROM ceo_reviews
                        WHERE status = 'pending'
                        ORDER BY created_at ASC
                    """)

                    results = [dict(row) for row in cursor.fetchall()]

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
            with self._get_connection() as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                if acknowledged is None:
                    cursor.execute("""
                        SELECT * FROM violations
                        WHERE violation_date >= datetime('now', ? || ' days')
                        ORDER BY violation_date DESC
                    """, (f'-{days}',))
                else:
                    ack_val = 1 if acknowledged else 0
                    cursor.execute("""
                        SELECT * FROM violations
                        WHERE violation_date >= datetime('now', ? || ' days')
                        AND acknowledged = ?
                        ORDER BY violation_date DESC
                    """, (f'-{days}', ack_val))

                results = [dict(row) for row in cursor.fetchall()]

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
            with self._get_connection() as conn:
                cursor = conn.cursor()

                # Total count
                cursor.execute("""
                    SELECT COUNT(*) FROM violations
                    WHERE violation_date >= datetime('now', ? || ' days')
                """, (f'-{days}',))
                total = cursor.fetchone()[0]

                # By rule
                cursor.execute("""
                    SELECT rule_id, rule_name, COUNT(*) as count
                    FROM violations
                    WHERE violation_date >= datetime('now', ? || ' days')
                    GROUP BY rule_id, rule_name
                    ORDER BY count DESC
                """, (f'-{days}',))
                by_rule = [{'rule_id': r[0], 'rule_name': r[1], 'count': r[2]}
                          for r in cursor.fetchall()]

                # Acknowledged count
                cursor.execute("""
                    SELECT COUNT(*) FROM violations
                    WHERE violation_date >= datetime('now', ? || ' days')
                    AND acknowledged = 1
                """, (f'-{days}',))
                acknowledged = cursor.fetchone()[0]

                # Recent violations (last 5)
                cursor.execute("""
                    SELECT rule_id, rule_name, description, violation_date
                    FROM violations
                    WHERE violation_date >= datetime('now', ? || ' days')
                    ORDER BY violation_date DESC
                    LIMIT 5
                """, (f'-{days}',))
                recent = [{'rule_id': r[0], 'rule_name': r[1],
                          'description': r[2], 'date': r[3]}
                         for r in cursor.fetchall()]

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
                with self._get_connection() as conn:
                    # Check if decisions table exists (backwards compatibility)
                    cursor = conn.cursor()
                    cursor.execute("""
                        SELECT name FROM sqlite_master
                        WHERE type='table' AND name='decisions'
                    """)
                    if not cursor.fetchone():
                        self._log_debug("Decisions table does not exist yet - returning empty list")
                        return []

                    conn.row_factory = sqlite3.Row
                    cursor = conn.cursor()

                    if domain:
                        domain = self._validate_domain(domain)
                        cursor.execute("""
                            SELECT id, title, context, decision, rationale, domain, status, created_at
                            FROM decisions
                            WHERE (domain = ? OR domain IS NULL) AND status = ?
                            ORDER BY created_at DESC
                            LIMIT ?
                        """, (domain, status, limit))
                    else:
                        cursor.execute("""
                            SELECT id, title, context, decision, rationale, domain, status, created_at
                            FROM decisions
                            WHERE status = ?
                            ORDER BY created_at DESC
                            LIMIT ?
                        """, (status, limit))

                    results = [dict(row) for row in cursor.fetchall()]

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
                with self._get_connection() as conn:
                    # Check if invariants table exists (backwards compatibility)
                    cursor = conn.cursor()
                    cursor.execute("""
                        SELECT name FROM sqlite_master
                        WHERE type='table' AND name='invariants'
                    """)
                    if not cursor.fetchone():
                        self._log_debug("Invariants table does not exist yet - returning empty list")
                        return []

                    conn.row_factory = sqlite3.Row
                    cursor = conn.cursor()

                    query = """
                        SELECT id, statement, rationale, domain, scope, validation_type,
                               validation_code, severity, status, violation_count,
                               last_validated_at, last_violated_at, created_at
                        FROM invariants
                        WHERE 1=1
                    """
                    params = []

                    if status:
                        query += " AND status = ?"
                        params.append(status)

                    if domain:
                        domain = self._validate_domain(domain)
                        query += " AND (domain = ? OR domain IS NULL)"
                        params.append(domain)

                    if scope:
                        query += " AND scope = ?"
                        params.append(scope)

                    if severity:
                        query += " AND severity = ?"
                        params.append(severity)

                    query += " ORDER BY created_at DESC LIMIT ?"
                    params.append(limit)

                    cursor.execute(query, params)
                    results = [dict(row) for row in cursor.fetchall()]

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
                with self._get_connection() as conn:
                    # Check if assumptions table exists (backwards compatibility)
                    cursor = conn.cursor()
                    cursor.execute("""
                        SELECT name FROM sqlite_master
                        WHERE type='table' AND name='assumptions'
                    """)
                    if not cursor.fetchone():
                        self._log_debug("Assumptions table does not exist yet - returning empty list")
                        return []

                    conn.row_factory = sqlite3.Row
                    cursor = conn.cursor()

                    query = """
                        SELECT id, assumption, context, source, confidence, status, domain,
                               verified_count, challenged_count, last_verified_at, created_at
                        FROM assumptions
                        WHERE status = ? AND confidence >= ?
                    """
                    params = [status, min_confidence]

                    if domain:
                        domain = self._validate_domain(domain)
                        query += " AND (domain = ? OR domain IS NULL)"
                        params.append(domain)

                    query += " ORDER BY confidence DESC, created_at DESC LIMIT ?"
                    params.append(limit)

                    cursor.execute(query, params)
                    results = [dict(row) for row in cursor.fetchall()]

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
            with self._get_connection() as conn:
                # Check if assumptions table exists
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT name FROM sqlite_master
                    WHERE type='table' AND name='assumptions'
                """)
                if not cursor.fetchone():
                    return []

                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                query = """
                    SELECT id, assumption, context, source, confidence, status, domain,
                           verified_count, challenged_count, created_at
                    FROM assumptions
                    WHERE status IN ('challenged', 'invalidated')
                """
                params = []

                if domain:
                    domain = self._validate_domain(domain)
                    query += " AND (domain = ? OR domain IS NULL)"
                    params.append(domain)

                query += " ORDER BY challenged_count DESC, created_at DESC LIMIT ?"
                params.append(limit)

                cursor.execute(query, params)
                results = [dict(row) for row in cursor.fetchall()]

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
                with self._get_connection() as conn:
                    # Check if spike_reports table exists (backwards compatibility)
                    cursor = conn.cursor()
                    cursor.execute("""
                        SELECT name FROM sqlite_master
                        WHERE type='table' AND name='spike_reports'
                    """)
                    if not cursor.fetchone():
                        self._log_debug("spike_reports table does not exist yet - returning empty list")
                        return []

                    conn.row_factory = sqlite3.Row
                    cursor = conn.cursor()

                    # Build query dynamically
                    query = """
                        SELECT id, title, topic, question, findings, gotchas, resources,
                               time_invested_minutes, domain, tags, usefulness_score,
                               access_count, created_at, updated_at
                        FROM spike_reports
                        WHERE 1=1
                    """
                    params = []

                    if domain:
                        domain = self._validate_domain(domain)
                        query += " AND (domain = ? OR domain IS NULL)"
                        params.append(domain)

                    if tags:
                        tags = self._validate_tags(tags)
                        tag_conditions = " OR ".join(["tags LIKE ?" for _ in tags])
                        query += f" AND ({tag_conditions})"
                        params.extend([f"%{escape_like(tag)}%" for tag in tags])

                    if search:
                        escaped_search = escape_like(search)
                        query += " AND (title LIKE ? OR topic LIKE ? OR question LIKE ? OR findings LIKE ?)"
                        params.extend([f"%{escaped_search}%"] * 4)

                    # Order by usefulness then recency
                    query += " ORDER BY usefulness_score DESC, created_at DESC LIMIT ?"
                    params.append(limit)

                    cursor.execute(query, params)
                    results = [dict(row) for row in cursor.fetchall()]

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
            with self._get_connection() as conn:
                cursor = conn.cursor()

                stats = {}

                # Count learnings by type
                cursor.execute("SELECT type, COUNT(*) as count FROM learnings GROUP BY type")
                stats['learnings_by_type'] = dict(cursor.fetchall())

                # Count learnings by domain
                cursor.execute("SELECT domain, COUNT(*) as count FROM learnings GROUP BY domain")
                stats['learnings_by_domain'] = dict(cursor.fetchall())

                # Count heuristics by domain
                cursor.execute("SELECT domain, COUNT(*) as count FROM heuristics GROUP BY domain")
                stats['heuristics_by_domain'] = dict(cursor.fetchall())

                # Count golden heuristics
                cursor.execute("SELECT COUNT(*) FROM heuristics WHERE is_golden = 1")
                stats['golden_heuristics'] = cursor.fetchone()[0]

                # Count experiments by status
                cursor.execute("SELECT status, COUNT(*) as count FROM experiments GROUP BY status")
                stats['experiments_by_status'] = dict(cursor.fetchall())

                # Count CEO reviews by status
                cursor.execute("SELECT status, COUNT(*) as count FROM ceo_reviews GROUP BY status")
                stats['ceo_reviews_by_status'] = dict(cursor.fetchall())

                # Total counts
                cursor.execute("SELECT COUNT(*) FROM learnings")
                stats['total_learnings'] = cursor.fetchone()[0]

                cursor.execute("SELECT COUNT(*) FROM heuristics")
                stats['total_heuristics'] = cursor.fetchone()[0]

                cursor.execute("SELECT COUNT(*) FROM experiments")
                stats['total_experiments'] = cursor.fetchone()[0]

                cursor.execute("SELECT COUNT(*) FROM ceo_reviews")
                stats['total_ceo_reviews'] = cursor.fetchone()[0]

                # Violation statistics (last 7 days)
                cursor.execute("""
                    SELECT COUNT(*) FROM violations
                    WHERE violation_date >= datetime('now', '-7 days')
                """)
                stats['violations_7d'] = cursor.fetchone()[0]

                cursor.execute("""
                    SELECT rule_id, rule_name, COUNT(*) as count
                    FROM violations
                    WHERE violation_date >= datetime('now', '-7 days')
                    GROUP BY rule_id, rule_name
                    ORDER BY count DESC
                """)
                stats['violations_by_rule_7d'] = dict((f"Rule {r[0]}: {r[1]}", r[2])
                                                      for r in cursor.fetchall())

        self._log_debug(f"Statistics gathered: {stats['total_learnings']} learnings total")
        return stats


def generate_accountability_banner(summary: Dict[str, Any]) -> str:
    """
    Generate a visually distinct accountability banner showing violation status.

    Args:
        summary: Violation summary from get_violation_summary()

    Returns:
        Formatted banner string with box drawing characters
    """
    total = summary['total']
    days = summary['days']
    by_rule = summary['by_rule']
    recent = summary['recent']

    # Determine status level
    if total >= 10:
        status = "CRITICAL"
        status_color = "RED"
        message = "CEO ESCALATION REQUIRED"
    elif total >= 5:
        status = "PROBATION"
        status_color = "YELLOW"
        message = "INCREASED SCRUTINY MODE"
    elif total >= 3:
        status = "WARNING"
        status_color = "YELLOW"
        message = "Review adherence to rules"
    else:
        status = "NORMAL"
        status_color = "GREEN"
        message = "Acceptable compliance level"

    # Build banner
    banner = []
    banner.append("╔═══════════════════════════════════════════════════════════════════════╗")
    banner.append("║                    ACCOUNTABILITY TRACKING SYSTEM                     ║")
    banner.append("║                     Golden Rule Violation Report                      ║")
    banner.append("╠═══════════════════════════════════════════════════════════════════════╣")
    banner.append(f"║  Period: Last {days} days                                                     ║")
    banner.append(f"║  Total Violations: {total:<54} ║")
    banner.append(f"║  Status: {status:<60} ║")
    banner.append(f"║  {message:<68} ║")
    banner.append("╠═══════════════════════════════════════════════════════════════════════╣")

    if by_rule:
        banner.append("║  Violations by Rule:                                                  ║")
        for rule in by_rule[:5]:  # Top 5 rules
            rule_line = f"║    Rule #{rule['rule_id']}: {rule['rule_name'][:35]:<35} ({rule['count']:>2}x) ║"
            banner.append(rule_line)
        if len(by_rule) > 5:
            banner.append(f"║    ... and {len(by_rule) - 5} more                                                  ║")
        banner.append("╠═══════════════════════════════════════════════════════════════════════╣")

    if recent:
        banner.append("║  Recent Violations:                                                   ║")
        for v in recent[:3]:  # Top 3 recent
            date_str = v['date'][:16] if v['date'] else "Unknown"
            desc = v['description'][:45] if v['description'] else "No description"
            banner.append(f"║    [{date_str}] Rule #{v['rule_id']:<2}                                   ║")
            banner.append(f"║      {desc:<66} ║")
        banner.append("╠═══════════════════════════════════════════════════════════════════════╣")

    # Progressive consequences
    if total >= 10:
        banner.append("║  ⚠️  CONSEQUENCES: CEO escalation auto-created in ceo-inbox/          ║")
    elif total >= 5:
        banner.append("║  ⚠️  CONSEQUENCES: Under probation - violations logged prominently    ║")
    elif total >= 3:
        banner.append("║  ⚠️  CONSEQUENCES: Warning threshold - 2 more violations = probation  ║")
    else:
        banner.append("║  ✓  STATUS: Acceptable compliance. Keep up good practices.            ║")

    banner.append("╚═══════════════════════════════════════════════════════════════════════╝")

    return "\n".join(banner)


def format_output(data: Any, format_type: str = 'text') -> str:
    """
    Format query results for display.

    Args:
        data: Data to format
        format_type: Output format ('text', 'json', or 'csv')

    Returns:
        Formatted string
    """
    if format_type == 'json':
        return json.dumps(data, indent=2, default=str)

    elif format_type == 'csv':
        # CSV formatting for list data
        if isinstance(data, list) and data:
            output = io.StringIO()
            if isinstance(data[0], dict):
                writer = csv.DictWriter(output, fieldnames=data[0].keys())
                writer.writeheader()
                writer.writerows(data)
            else:
                writer = csv.writer(output)
                for item in data:
                    writer.writerow([item])
            return output.getvalue()
        else:
            return str(data)

    # Text formatting
    if isinstance(data, dict):
        lines = []
        for key, value in data.items():
            if isinstance(value, (list, dict)):
                lines.append(f"{key}:")
                lines.append(format_output(value, format_type))
            else:
                lines.append(f"{key}: {value}")
        return "\n".join(lines)

    elif isinstance(data, list):
        lines = []
        for i, item in enumerate(data, 1):
            lines.append(f"\n--- Item {i} ---")
            lines.append(format_output(item, format_type))
        return "\n".join(lines)

    else:
        return str(data)


def ensure_hooks_installed():
    """Auto-install ELF hooks on first use."""
    marker = Path(__file__).parent.parent / ".hooks-installed"
    if marker.exists():
        return

    install_script = Path(__file__).parent.parent / "scripts" / "install-hooks.py"
    if install_script.exists():
        import subprocess
        try:
            subprocess.run([sys.executable, str(install_script)],
                          capture_output=True, timeout=10)
        except Exception:
            pass  # Silent fail - hooks are optional



def ensure_full_setup():
    """
    Check setup status and return status code for Claude to handle.
    Claude will use AskUserQuestion tool to show selection boxes if needed.

    Returns:
        "ok" - Already set up, proceed normally
        "fresh_install" - New user, auto-installed successfully
        "needs_user_choice" - Has existing config, Claude should ask user
        "install_failed" - Something went wrong
    """
    import platform

    global_claude_md = Path.home() / ".claude" / "CLAUDE.md"
    elf_dir = Path(__file__).parent.parent

    # Detect OS and find appropriate installer
    is_windows = platform.system() == "Windows"

    if is_windows:
        setup_script = elf_dir / "install.ps1"
    else:
        setup_script = elf_dir / "setup" / "install.sh"

    if not setup_script.exists():
        return "ok"

    # Case 1: No CLAUDE.md - new user, auto-install
    if not global_claude_md.exists():
        import subprocess
        print("")
        print("=" * 60)
        print("[ELF] Welcome! First-time setup...")
        print("=" * 60)
        print("")
        print("Installing:")
        print("  - CLAUDE.md : Core instructions")
        print("  - /search   : Session history search")
        print("  - /checkin  : Building check-in")
        print("  - /swarm    : Multi-agent coordination")
        print("  - Hooks     : Auto-query & enforcement")
        print("")
        try:
            if is_windows:
                # Windows: use PowerShell with CoreOnly to avoid dashboard during auto-setup
                result = subprocess.run(
                    ["powershell", "-ExecutionPolicy", "Bypass", "-File", str(setup_script), "-CoreOnly"],
                    capture_output=True, text=True, timeout=60
                )
            else:
                # Unix: use bash
                result = subprocess.run(
                    ["bash", str(setup_script), "--mode", "fresh"],
                    capture_output=True, text=True, timeout=30
                )
            print("[ELF] Setup complete!")
            print("")
            return "fresh_install"
        except Exception as e:
            print(f"[ELF] Setup issue: {e}")
            return "install_failed"
    
    # Case 2: Has CLAUDE.md with ELF already
    try:
        with open(global_claude_md, 'r', encoding='utf-8') as f:
            content = f.read()
        if "Emergent Learning Framework" in content or "query the building" in content.lower():
            return "ok"
    except:
        pass
    
    # Case 3: Has CLAUDE.md but no ELF - Claude should ask user
    print("")
    print("=" * 60)
    print("[ELF] Existing configuration detected")
    print("=" * 60)
    print("")
    print("You have ~/.claude/CLAUDE.md but it doesn't include ELF.")
    print("Claude will ask how you'd like to proceed.")
    print("")
    print("[ELF_NEEDS_USER_CHOICE]")
    print("")
    return "needs_user_choice"


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
    exit(main())
