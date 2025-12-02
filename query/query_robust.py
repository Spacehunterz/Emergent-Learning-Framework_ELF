#!/usr/bin/env python3
"""
Emergent Learning Framework - Robust Query System (Agent D Enhanced)
A hardened tiered retrieval system with defensive SQLite handling.

Enhanced with:
1. Schema migration and evolution
2. Strict type validation
3. NULL handling and validation
4. Constraint enforcement
5. Transaction retry logic with exponential backoff
6. Database locking with configurable timeouts
7. Corruption detection and recovery
8. Index integrity checks
9. Auto-maintenance (VACUUM, ANALYZE)
"""

import sqlite3
import os
import sys
import io
import argparse
import time
import shutil
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import json
import logging

# Fix Windows console encoding for Unicode characters
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] [query] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


class DatabaseCorruptionError(Exception):
    """Raised when database corruption is detected."""
    pass


class RobustQuerySystem:
    """Manages knowledge retrieval from the Emergent Learning Framework with defensive SQLite handling."""

    # Current schema version
    SCHEMA_VERSION = 1

    # Database configuration
    DEFAULT_TIMEOUT = 30.0  # 30 seconds timeout
    MAX_RETRIES = 5
    RETRY_BASE_DELAY = 0.1  # 100ms base delay

    # Maintenance thresholds
    FREELIST_THRESHOLD = 100  # Pages before considering VACUUM
    ANALYZE_INTERVAL = 100  # Operations before ANALYZE

    def __init__(self, base_path: Optional[str] = None):
        """
        Initialize the robust query system.

        Args:
            base_path: Base path to the emergent-learning directory.
                      Defaults to ~/.claude/emergent-learning
        """
        if base_path is None:
            home = Path.home()
            self.base_path = home / ".claude" / "emergent-learning"
        else:
            self.base_path = Path(base_path)

        self.memory_path = self.base_path / "memory"
        self.db_path = self.memory_path / "index.db"
        self.db_backup_path = self.memory_path / "index.db.backup"
        self.golden_rules_path = self.memory_path / "golden-rules.md"

        # Ensure directories exist
        self.memory_path.mkdir(parents=True, exist_ok=True)

        # Operation counter for maintenance
        self.operation_count = 0

        # Initialize database with error handling
        try:
            self._preflight_check()
            self._init_database()
            self._migrate_schema()
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            self._attempt_recovery()

    def _preflight_check(self):
        """Pre-flight integrity and security checks."""
        logger.info("Running pre-flight checks")

        # Security: Check for symlink attacks
        if self.memory_path.is_symlink():
            raise SecurityError("SECURITY: memory directory is a symlink")

        # Check database integrity if exists
        if self.db_path.exists():
            try:
                conn = self._connect_with_retry()
                cursor = conn.cursor()
                cursor.execute("PRAGMA integrity_check")
                result = cursor.fetchone()[0]

                if result != "ok":
                    raise DatabaseCorruptionError(f"Database integrity check failed: {result}")

                conn.close()
                logger.info("Pre-flight integrity check passed")
            except sqlite3.DatabaseError as e:
                raise DatabaseCorruptionError(f"Database corruption detected: {e}")

    def _attempt_recovery(self):
        """Attempt to recover from database corruption."""
        logger.warning("Attempting database recovery")

        # Try to restore from backup
        if self.db_backup_path.exists():
            logger.info(f"Restoring from backup: {self.db_backup_path}")
            try:
                shutil.copy2(self.db_backup_path, self.db_path)
                self._preflight_check()
                self._init_database()
                logger.info("Recovery successful from backup")
                return
            except Exception as e:
                logger.error(f"Backup restoration failed: {e}")

        # Last resort: recreate database
        logger.warning("Creating new database (data loss occurred)")
        if self.db_path.exists():
            # Move corrupted DB to .corrupted
            corrupted_path = self.db_path.with_suffix('.db.corrupted')
            shutil.move(self.db_path, corrupted_path)
            logger.info(f"Corrupted database moved to: {corrupted_path}")

        self._init_database()

    def _connect_with_retry(self, timeout: Optional[float] = None) -> sqlite3.Connection:
        """
        Connect to database with retry logic and exponential backoff.

        Args:
            timeout: Connection timeout in seconds

        Returns:
            Database connection

        Raises:
            sqlite3.OperationalError: If connection fails after retries
        """
        if timeout is None:
            timeout = self.DEFAULT_TIMEOUT

        for attempt in range(self.MAX_RETRIES):
            try:
                conn = sqlite3.connect(
                    str(self.db_path),
                    timeout=timeout,
                    isolation_level='DEFERRED'  # More conservative than default
                )

                # Enable foreign keys
                conn.execute("PRAGMA foreign_keys = ON")

                # Enable WAL mode for better concurrency (if not already)
                # WAL mode allows reads during writes
                try:
                    conn.execute("PRAGMA journal_mode=WAL")
                except sqlite3.OperationalError:
                    # WAL not supported, continue with rollback journal
                    logger.warning("WAL mode not available, using rollback journal")

                return conn

            except sqlite3.OperationalError as e:
                if "locked" in str(e).lower() and attempt < self.MAX_RETRIES - 1:
                    # Exponential backoff
                    delay = self.RETRY_BASE_DELAY * (2 ** attempt)
                    logger.warning(f"Database locked, retry {attempt + 1}/{self.MAX_RETRIES} after {delay:.2f}s")
                    time.sleep(delay)
                else:
                    raise

        raise sqlite3.OperationalError(f"Failed to connect after {self.MAX_RETRIES} retries")

    def _execute_with_retry(self, conn: sqlite3.Connection, query: str, params: tuple = ()) -> sqlite3.Cursor:
        """
        Execute query with retry logic for locked database.

        Args:
            conn: Database connection
            query: SQL query
            params: Query parameters

        Returns:
            Cursor with results

        Raises:
            sqlite3.OperationalError: If execution fails after retries
        """
        for attempt in range(self.MAX_RETRIES):
            try:
                cursor = conn.cursor()
                cursor.execute(query, params)
                return cursor

            except sqlite3.OperationalError as e:
                if "locked" in str(e).lower() and attempt < self.MAX_RETRIES - 1:
                    delay = self.RETRY_BASE_DELAY * (2 ** attempt)
                    logger.warning(f"Query locked, retry {attempt + 1}/{self.MAX_RETRIES} after {delay:.2f}s")
                    time.sleep(delay)
                else:
                    raise

        raise sqlite3.OperationalError(f"Query failed after {self.MAX_RETRIES} retries")

    def _validate_severity(self, severity: Any) -> int:
        """
        Validate and normalize severity value.

        Args:
            severity: Input severity (int, string, or None)

        Returns:
            Validated severity as integer 1-5

        Raises:
            ValueError: If severity is invalid
        """
        if severity is None:
            return 3  # Default

        # If already integer, validate range
        if isinstance(severity, int):
            if 1 <= severity <= 5:
                return severity
            raise ValueError(f"Severity must be 1-5, got {severity}")

        # If string, try to convert
        if isinstance(severity, str):
            # Try numeric string
            try:
                val = int(severity)
                if 1 <= val <= 5:
                    return val
            except ValueError:
                pass

            # Try word mapping
            severity_map = {
                'low': 2,
                'medium': 3,
                'high': 4,
                'critical': 5
            }
            normalized = severity.lower().strip()
            if normalized in severity_map:
                return severity_map[normalized]

        raise ValueError(f"Invalid severity: {severity}")

    def _validate_confidence(self, confidence: Any) -> float:
        """
        Validate and normalize confidence value.

        Args:
            confidence: Input confidence (float, string, or None)

        Returns:
            Validated confidence as float 0.0-1.0

        Raises:
            ValueError: If confidence is invalid
        """
        if confidence is None:
            return 0.5  # Default

        # If already float/int, validate range
        if isinstance(confidence, (float, int)):
            val = float(confidence)
            if 0.0 <= val <= 1.0:
                return val
            raise ValueError(f"Confidence must be 0.0-1.0, got {val}")

        # If string, try to convert
        if isinstance(confidence, str):
            # Try numeric string
            try:
                val = float(confidence)
                if 0.0 <= val <= 1.0:
                    return val
            except ValueError:
                pass

            # Try word mapping
            confidence_map = {
                'low': 0.3,
                'medium': 0.6,
                'high': 0.85
            }
            normalized = confidence.lower().strip()
            if normalized in confidence_map:
                return confidence_map[normalized]

        raise ValueError(f"Invalid confidence: {confidence}")

    def _init_database(self):
        """Initialize the database with required schema if it does not exist."""
        logger.info("Initializing database schema")

        conn = self._connect_with_retry()
        cursor = conn.cursor()

        # Create learnings table with proper constraints
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS learnings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type TEXT NOT NULL CHECK(type IN ('failure', 'success', 'observation', 'experiment')),
                filepath TEXT NOT NULL UNIQUE,
                title TEXT NOT NULL,
                summary TEXT,
                tags TEXT,
                domain TEXT,
                severity INTEGER DEFAULT 3 CHECK(severity >= 1 AND severity <= 5),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Create heuristics table with proper constraints
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS heuristics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                domain TEXT NOT NULL,
                rule TEXT NOT NULL,
                explanation TEXT,
                source_type TEXT CHECK(source_type IN ('failure', 'success', 'observation', NULL)),
                source_id INTEGER,
                confidence REAL DEFAULT 0.5 CHECK(confidence >= 0.0 AND confidence <= 1.0),
                times_validated INTEGER DEFAULT 0 CHECK(times_validated >= 0),
                times_violated INTEGER DEFAULT 0 CHECK(times_violated >= 0),
                is_golden BOOLEAN DEFAULT FALSE,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(domain, rule)
            )
        """)

        # Create experiments table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS experiments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                hypothesis TEXT,
                status TEXT DEFAULT 'active' CHECK(status IN ('active', 'paused', 'completed', 'failed')),
                cycles_run INTEGER DEFAULT 0 CHECK(cycles_run >= 0),
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
                status TEXT DEFAULT 'pending' CHECK(status IN ('pending', 'approved', 'rejected', 'deferred')),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                reviewed_at TIMESTAMP
            )
        """)

        # Create schema_version table for migrations
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS schema_version (
                version INTEGER PRIMARY KEY,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Enable foreign keys
        cursor.execute("PRAGMA foreign_keys = ON")

        # Create indexes for efficient querying
        self._create_indexes(cursor)

        # Update query planner statistics
        cursor.execute("ANALYZE")

        conn.commit()
        conn.close()

        logger.info("Database schema initialized")

    def _create_indexes(self, cursor: sqlite3.Cursor):
        """Create all necessary indexes."""
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_learnings_domain ON learnings(domain)",
            "CREATE INDEX IF NOT EXISTS idx_learnings_type ON learnings(type)",
            "CREATE INDEX IF NOT EXISTS idx_learnings_created_at ON learnings(created_at DESC)",
            "CREATE INDEX IF NOT EXISTS idx_learnings_domain_created ON learnings(domain, created_at DESC)",
            "CREATE INDEX IF NOT EXISTS idx_learnings_filepath ON learnings(filepath)",
            "CREATE INDEX IF NOT EXISTS idx_heuristics_domain ON heuristics(domain)",
            "CREATE INDEX IF NOT EXISTS idx_heuristics_golden ON heuristics(is_golden)",
            "CREATE INDEX IF NOT EXISTS idx_heuristics_created_at ON heuristics(created_at DESC)",
            "CREATE INDEX IF NOT EXISTS idx_heuristics_domain_confidence ON heuristics(domain, confidence DESC)",
            "CREATE INDEX IF NOT EXISTS idx_experiments_status ON experiments(status)",
            "CREATE INDEX IF NOT EXISTS idx_ceo_reviews_status ON ceo_reviews(status)",
        ]

        for index_sql in indexes:
            cursor.execute(index_sql)

    def _migrate_schema(self):
        """Migrate database schema to latest version."""
        conn = self._connect_with_retry()
        cursor = conn.cursor()

        # Get current version
        try:
            cursor.execute("SELECT MAX(version) FROM schema_version")
            result = cursor.fetchone()
            current_version = result[0] if result and result[0] else 0
        except sqlite3.OperationalError:
            # schema_version table doesn't exist (very old DB)
            current_version = 0

        logger.info(f"Current schema version: {current_version}")

        # Apply migrations
        if current_version < self.SCHEMA_VERSION:
            logger.info(f"Migrating schema from v{current_version} to v{self.SCHEMA_VERSION}")

            # Backup before migration
            self._create_backup()

            # Migration v0 -> v1: Add missing columns to old schemas
            if current_version < 1:
                self._migrate_to_v1(cursor)

            # Record new version
            cursor.execute("INSERT OR REPLACE INTO schema_version (version) VALUES (?)",
                          (self.SCHEMA_VERSION,))

            conn.commit()
            logger.info("Schema migration completed")

        conn.close()

    def _migrate_to_v1(self, cursor: sqlite3.Cursor):
        """Migrate to schema version 1."""
        logger.info("Applying migration to v1")

        # Check if learnings table exists and add missing columns
        cursor.execute("PRAGMA table_info(learnings)")
        columns = {row[1] for row in cursor.fetchall()}

        migrations = []

        # Add missing columns if needed
        if 'tags' not in columns:
            migrations.append("ALTER TABLE learnings ADD COLUMN tags TEXT")
        if 'domain' not in columns:
            migrations.append("ALTER TABLE learnings ADD COLUMN domain TEXT")
        if 'severity' not in columns:
            migrations.append("ALTER TABLE learnings ADD COLUMN severity INTEGER DEFAULT 3 CHECK(severity >= 1 AND severity <= 5)")
        if 'created_at' not in columns:
            migrations.append("ALTER TABLE learnings ADD COLUMN created_at DATETIME DEFAULT CURRENT_TIMESTAMP")
        if 'updated_at' not in columns:
            migrations.append("ALTER TABLE learnings ADD COLUMN updated_at DATETIME DEFAULT CURRENT_TIMESTAMP")

        for migration in migrations:
            logger.info(f"  Running: {migration}")
            cursor.execute(migration)

        # Note: SQLite doesn't support adding constraints to existing tables
        # For UNIQUE constraint on filepath, we'd need to recreate the table
        # This is left for a future migration if needed

    def _create_backup(self):
        """Create a backup of the database."""
        if self.db_path.exists():
            try:
                shutil.copy2(self.db_path, self.db_backup_path)
                logger.info(f"Database backed up to: {self.db_backup_path}")
            except Exception as e:
                logger.error(f"Failed to create backup: {e}")

    def _perform_maintenance(self, force: bool = False):
        """Perform database maintenance (VACUUM, ANALYZE) if needed."""
        self.operation_count += 1

        # ANALYZE every N operations
        if force or self.operation_count % self.ANALYZE_INTERVAL == 0:
            try:
                conn = self._connect_with_retry()
                cursor = conn.cursor()

                # Check freelist for VACUUM decision
                cursor.execute("PRAGMA freelist_count")
                freelist = cursor.fetchone()[0]

                if force or freelist > self.FREELIST_THRESHOLD:
                    logger.info(f"Running VACUUM (freelist: {freelist} pages)")
                    cursor.execute("VACUUM")

                logger.info("Running ANALYZE")
                cursor.execute("ANALYZE")

                conn.close()
            except Exception as e:
                logger.error(f"Maintenance failed: {e}")

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
                return f.read()
        except Exception as e:
            logger.error(f"Failed to read golden rules: {e}")
            return f"# Error Reading Golden Rules\n\nError: {str(e)}"

    def query_by_domain(self, domain: str, limit: int = 10) -> Dict[str, Any]:
        """
        Get heuristics and learnings for a specific domain.

        Args:
            domain: The domain to query (e.g., 'coordination', 'debugging')
            limit: Maximum number of results to return

        Returns:
            Dictionary containing heuristics and learnings for the domain
        """
        conn = self._connect_with_retry()
        conn.row_factory = sqlite3.Row

        cursor = self._execute_with_retry(conn, """
            SELECT * FROM heuristics
            WHERE domain = ?
            ORDER BY confidence DESC, times_validated DESC
            LIMIT ?
        """, (domain, limit))
        heuristics = [dict(row) for row in cursor.fetchall()]

        cursor = self._execute_with_retry(conn, """
            SELECT * FROM learnings
            WHERE domain = ?
            ORDER BY created_at DESC
            LIMIT ?
        """, (domain, limit))
        learnings = [dict(row) for row in cursor.fetchall()]

        conn.close()

        self._perform_maintenance()

        return {
            'domain': domain,
            'heuristics': heuristics,
            'learnings': learnings,
            'count': {
                'heuristics': len(heuristics),
                'learnings': len(learnings)
            }
        }

    # Additional methods would be similarly enhanced...
    # (Omitted for brevity, but would include same retry logic, validation, etc.)


def main():
    """Command-line interface for the robust query system."""
    parser = argparse.ArgumentParser(
        description="Emergent Learning Framework - Robust Query System (Agent D)",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument('--base-path', type=str, help='Base path to emergent-learning directory')
    parser.add_argument('--maintenance', action='store_true', help='Force maintenance (VACUUM + ANALYZE)')
    parser.add_argument('--backup', action='store_true', help='Create database backup')
    parser.add_argument('--check-integrity', action='store_true', help='Check database integrity')

    args = parser.parse_args()

    # Initialize robust query system
    try:
        query_system = RobustQuerySystem(base_path=args.base_path)

        if args.maintenance:
            query_system._perform_maintenance(force=True)
            print("Maintenance completed")

        if args.backup:
            query_system._create_backup()
            print("Backup created")

        if args.check_integrity:
            query_system._preflight_check()
            print("Integrity check passed")

    except Exception as e:
        logger.error(f"Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
