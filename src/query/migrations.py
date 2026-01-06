"""
Database schema migrations for the Emergent Learning Framework.

Handles automatic schema updates on startup. All migrations are idempotent
(safe to run multiple times) and are tracked in the schema_version table.

Usage:
    # Runs automatically on QuerySystem.create()
    migrator = SchemaMigrator(db_path)
    await migrator.migrate()

Migration files are stored in src/query/migrations/ and named as:
    001_initial_schema.sql
    002_add_topic_to_spike_reports.sql
    etc.
"""

import sqlite3
import logging
from pathlib import Path
from typing import Optional, Dict, List, Tuple
import sys

logger = logging.getLogger(__name__)


class SchemaMigrator:
    """Handles database schema migrations."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.migrations_dir = Path(__file__).parent / "migrations"

    def get_current_version(self) -> int:
        """Get the current schema version from the database."""
        try:
            conn = sqlite3.connect(self.db_path, timeout=10.0)
            conn.row_factory = sqlite3.Row

            try:
                cursor = conn.execute(
                    "SELECT version FROM schema_version ORDER BY version DESC LIMIT 1"
                )
                row = cursor.fetchone()
                version = row["version"] if row else 0
            except sqlite3.OperationalError:
                version = 0
            finally:
                conn.close()

            return version
        except Exception as e:
            logger.warning(f"Could not determine schema version: {e}")
            return 0

    def get_available_migrations(self) -> List[Tuple[int, Path]]:
        """Get list of available migration files in order."""
        migrations = []

        if not self.migrations_dir.exists():
            self.migrations_dir.mkdir(parents=True, exist_ok=True)
            return migrations

        for migration_file in sorted(self.migrations_dir.glob("*.sql")):
            try:
                version = int(migration_file.stem.split("_")[0])
                migrations.append((version, migration_file))
            except (ValueError, IndexError):
                logger.warning(f"Invalid migration file name: {migration_file.name}")

        return migrations

    def record_migration(self, version: int, description: str) -> None:
        """Record a migration in the schema_version table."""
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        try:
            conn.execute(
                "INSERT OR IGNORE INTO schema_version (version, description) "
                "VALUES (?, ?)",
                (version, description)
            )
            conn.commit()
        finally:
            conn.close()

    def apply_migration(self, version: int, migration_file: Path) -> bool:
        """Apply a single migration file with transaction safety."""
        try:
            with open(migration_file, "r") as f:
                sql_statements = f.read()

            conn = sqlite3.connect(self.db_path, timeout=10.0)
            conn.isolation_level = None
            try:
                cursor = conn.cursor()
                cursor.execute("BEGIN TRANSACTION")

                for statement in sql_statements.split(";"):
                    statement = statement.strip()
                    if statement and not statement.startswith("--"):
                        try:
                            cursor.execute(statement)
                        except sqlite3.OperationalError as e:
                            error_msg = str(e).lower()
                            if "already exists" in error_msg or "duplicate column" in error_msg:
                                logger.debug(f"Skipping idempotent statement: {statement[:50]}...")
                            else:
                                cursor.execute("ROLLBACK")
                                raise

                cursor.execute("COMMIT")

                description = migration_file.stem.split("_", 1)[1] if "_" in migration_file.stem else "migration"
                self.record_migration(version, description)

                return True
            except Exception:
                try:
                    cursor.execute("ROLLBACK")
                except Exception:
                    pass
                raise
            finally:
                conn.close()
        except Exception as e:
            logger.error(f"Failed to apply migration {version}: {e}")
            return False

    async def migrate(self) -> Dict[str, any]:
        """Run all pending migrations."""
        current_version = self.get_current_version()
        available_migrations = self.get_available_migrations()

        pending_migrations = [
            (v, f) for v, f in available_migrations if v > current_version
        ]

        result = {
            "current_version": current_version,
            "migrations_applied": [],
            "migrations_failed": [],
            "total_applied": 0,
            "status": "success"
        }

        if not pending_migrations:
            logger.debug(f"Database schema is up to date (v{current_version})")
            return result

        logger.info(f"Applying {len(pending_migrations)} schema migrations...")

        for version, migration_file in pending_migrations:
            logger.info(f"  Applying migration v{version}: {migration_file.name}")

            if self.apply_migration(version, migration_file):
                result["migrations_applied"].append({
                    "version": version,
                    "file": migration_file.name
                })
                result["total_applied"] += 1
            else:
                result["migrations_failed"].append({
                    "version": version,
                    "file": migration_file.name
                })
                result["status"] = "partial"

        if result["migrations_failed"]:
            logger.error(
                f"Failed to apply {len(result['migrations_failed'])} migrations. "
                "Some features may not work correctly."
            )
            result["status"] = "error"
        elif result["total_applied"] > 0:
            logger.info(f"Successfully applied {result['total_applied']} migrations")

        validation = self.validate_schema()
        result["schema_valid"] = validation["valid"]
        if not validation["valid"]:
            logger.error(f"Schema validation failed: {validation['issues']}")
            result["validation_issues"] = validation["issues"]
            if result["status"] == "success":
                result["status"] = "validation_failed"

        return result

    def validate_schema(self) -> Dict[str, any]:
        """Validate that the database schema is complete and correct."""
        issues = []

        required_columns = {
            "spike_reports": ["id", "title", "topic", "question", "findings", "gotchas",
                             "resources", "domain", "tags", "access_count", "updated_at"],
            "heuristics": ["id", "domain", "rule", "explanation", "confidence"],
            "learnings": ["id", "type", "filepath", "title"],
            "schema_version": ["version"],
        }

        try:
            conn = sqlite3.connect(self.db_path, timeout=10.0)
            cursor = conn.cursor()

            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = {row[0] for row in cursor.fetchall()}

            for table_name, required_cols in required_columns.items():
                if table_name not in tables:
                    issues.append(f"Missing table: {table_name}")
                    continue

                cursor.execute(f"PRAGMA table_info({table_name})")
                existing_columns = {row[1] for row in cursor.fetchall()}

                for col in required_cols:
                    if col not in existing_columns:
                        issues.append(f"Missing column: {table_name}.{col}")

            conn.close()
        except Exception as e:
            issues.append(f"Schema validation error: {e}")

        return {
            "valid": len(issues) == 0,
            "issues": issues
        }

    def repair_schema(self) -> Dict[str, any]:
        """Attempt to repair a corrupted schema by adding missing columns."""
        validation = self.validate_schema()
        if validation["valid"]:
            return {"repaired": False, "message": "Schema is already valid"}

        repairs = []
        errors = []

        column_defaults = {
            "spike_reports.topic": "TEXT NOT NULL DEFAULT ''",
            "spike_reports.question": "TEXT NOT NULL DEFAULT ''",
            "spike_reports.findings": "TEXT NOT NULL DEFAULT ''",
            "spike_reports.gotchas": "TEXT",
            "spike_reports.resources": "TEXT",
            "spike_reports.domain": "TEXT",
            "spike_reports.tags": "TEXT",
            "spike_reports.access_count": "INTEGER DEFAULT 0",
            "spike_reports.updated_at": "DATETIME",
        }

        try:
            conn = sqlite3.connect(self.db_path, timeout=10.0)
            cursor = conn.cursor()

            for issue in validation["issues"]:
                if issue.startswith("Missing column: "):
                    col_ref = issue.replace("Missing column: ", "")
                    if col_ref in column_defaults:
                        table, col = col_ref.split(".")
                        col_type = column_defaults[col_ref]
                        try:
                            cursor.execute(f"ALTER TABLE {table} ADD COLUMN {col} {col_type}")
                            repairs.append(col_ref)
                        except Exception as e:
                            errors.append(f"Failed to add {col_ref}: {e}")

            conn.commit()
            conn.close()
        except Exception as e:
            errors.append(f"Repair failed: {e}")

        return {
            "repaired": len(repairs) > 0,
            "repairs": repairs,
            "errors": errors,
            "revalidation": self.validate_schema() if repairs else validation
        }
