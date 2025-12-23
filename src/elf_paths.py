"""
Centralized path resolution for the Emergent Learning Framework.

Resolves the ELF base path with guardrails:
1) ELF_BASE_PATH environment variable (explicit override)
2) Repo-root discovery from a start path
3) ~/.claude/emergent-learning fallback (with warning)

Set ELF_STRICT_PATH=1 to disable fallback and force explicit configuration.
"""

from __future__ import annotations

import os
import warnings
from pathlib import Path
from typing import Optional

_FALLBACK_WARNED = False


def _is_truthy(value: Optional[str]) -> bool:
    if not value:
        return False
    return value.strip().lower() in {"1", "true", "yes", "on", "y"}


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


def _warn_fallback(path: Path) -> None:
    global _FALLBACK_WARNED
    if _FALLBACK_WARNED:
        return
    _FALLBACK_WARNED = True
    warnings.warn(
        "ELF_BASE_PATH not set and repo root not found; using fallback "
        f"{path}. Set ELF_BASE_PATH or enable ELF_STRICT_PATH to prevent fallback.",
        RuntimeWarning,
        stacklevel=2,
    )


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
        return Path(env_path).expanduser().resolve()

    repo_root = _find_repo_root(_normalize_start(start))
    if repo_root:
        return repo_root

    fallback = Path.home() / ".claude" / "emergent-learning"
    if _is_truthy(os.environ.get("ELF_STRICT_PATH")):
        raise RuntimeError(
            "ELF_STRICT_PATH is set, but ELF_BASE_PATH was not provided and "
            "repo root could not be found."
        )
    _warn_fallback(fallback)
    return fallback


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
