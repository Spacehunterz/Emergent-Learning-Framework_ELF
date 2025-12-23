"""
Centralized path resolution for the Emergent Learning Framework.

Resolves the ELF base path with guardrails:
1) ELF_BASE_PATH environment variable (explicit override)
2) Repo-root discovery from a start path

If a legacy ~/.claude/emergent-learning installation is detected and the
current base has no user data yet, a one-time migration copies the legacy
database (and golden rules) into the new base.
"""

from __future__ import annotations

import os
import shutil
import warnings
from pathlib import Path
from typing import Optional

_MIGRATION_ATTEMPTED = False
_LEGACY_BASE = Path.home() / ".claude" / "emergent-learning"


def _normalize_start(start: Optional[Path]) -> Path:
    if start is None:
        start = Path.cwd()
    else:
        start = Path(start)
    if start.is_file():
        start = start.parent
    return start.resolve()


def _find_repo_root(start: Path) -> Optional[Path]:
    markers = (".git", ".coordination", "pyproject.toml")
    for candidate in [start] + list(start.parents):
        for marker in markers:
            if (candidate / marker).exists():
                return candidate
    return None


def _warn_migration(source: Path, target: Path, items: list[str]) -> None:
    warnings.warn(
        "Migrated legacy ELF data from "
        f"{source} to {target}. Files: {', '.join(items)}",
        RuntimeWarning,
        stacklevel=2,
    )


def _db_has_user_data(db_path: Path) -> bool:
    if not db_path.exists():
        return False

    conn = None
    try:
        import sqlite3

        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master "
            "WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        )
        tables = [row[0] for row in cursor.fetchall()]
        if not tables:
            return False

        skip_tables = {"schema_version", "db_operations"}
        for table in tables:
            if table in skip_tables:
                continue
            cursor.execute(f"SELECT 1 FROM {table} LIMIT 1")
            if cursor.fetchone():
                return True
        return False
    except Exception:
        return True
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass


def _copy_if_missing(source: Path, target: Path) -> bool:
    if not source.exists() or target.exists():
        return False
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    return True


def _maybe_migrate_legacy(base: Path) -> None:
    global _MIGRATION_ATTEMPTED
    if _MIGRATION_ATTEMPTED:
        return
    _MIGRATION_ATTEMPTED = True

    legacy_base = _LEGACY_BASE
    if not legacy_base.exists():
        return

    if legacy_base.resolve() == base.resolve():
        return

    legacy_db = legacy_base / "memory" / "index.db"
    if not legacy_db.exists():
        return

    target_db = base / "memory" / "index.db"
    if target_db.exists() and _db_has_user_data(target_db):
        return

    target_db.parent.mkdir(parents=True, exist_ok=True)
    if target_db.exists():
        backup_path = target_db.with_suffix(".db.pre-legacy-migration")
        try:
            shutil.copy2(target_db, backup_path)
        except Exception:
            pass

    shutil.copy2(legacy_db, target_db)
    migrated_items = [str(target_db)]
    if _copy_if_missing(legacy_base / "memory" / "golden-rules.md",
                        base / "memory" / "golden-rules.md"):
        migrated_items.append(str(base / "memory" / "golden-rules.md"))

    _warn_migration(legacy_base, base, migrated_items)


def get_base_path(start: Optional[Path] = None) -> Path:
    """
    Resolve the ELF base path.

    Args:
        start: Optional start path for repo-root discovery.

    Returns:
        Resolved base path.
    """
    env_path = os.environ.get("ELF_BASE_PATH")
    if env_path:
        base = Path(env_path).expanduser().resolve()
        _maybe_migrate_legacy(base)
        return base

    repo_root = _find_repo_root(_normalize_start(start))
    if repo_root:
        _maybe_migrate_legacy(repo_root)
        return repo_root

    raise RuntimeError(
        "ELF_BASE_PATH was not provided and repo root could not be found. "
        "Run from the repo root or set ELF_BASE_PATH explicitly."
    )


def get_paths(base_path: Optional[Path] = None) -> dict:
    """
    Return common ELF paths derived from the base path.
    """
    base = base_path or get_base_path()
    return {
        "base": base,
        "memory": base / "memory",
        "logs": base / "logs",
        "coordination": base / ".coordination",
        "scripts": base / "scripts",
        "data": base / "data",
    }
