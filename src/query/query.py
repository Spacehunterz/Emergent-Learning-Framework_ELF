#!/usr/bin/env python3
"""
Emergent Learning Framework - Query System

This is a thin entry point that delegates to the async implementation in cli.py.
The actual query logic lives in core.py (async) with mixins in queries/.

For programmatic use:
    # Async API (preferred)
    from query.core import QuerySystem
    qs = await QuerySystem.create()
    result = await qs.build_context("task")
    await qs.cleanup()

For CLI use:
    python query.py --context
    python query.py --domain debugging --limit 5

REFACTORED: 2025-12-31
Previously a 2600-line monolith duplicating core.py.
Now delegates to cli.py which uses the async core.py internally.
"""

# Portable venv detection and re-exec
# If critical dependencies are missing, try to re-exec with the venv python
import os
import sys
from pathlib import Path

def _ensure_venv_python():
    """Re-exec with venv python if current python lacks dependencies."""
    # Check if we already have peewee_aio
    try:
        import peewee_aio
        return  # Already in correct environment
    except ImportError:
        pass

    # Find the .venv directory relative to this script
    script_dir = Path(__file__).resolve().parent
    venv_dir = script_dir.parent.parent.parent / '.venv'
    venv_python = None

    # Try common venv locations
    for possible_venv in [
        venv_dir,  # ../../.venv (repo root .venv)
        script_dir / '.venv',  # ./.venv
        Path.home() / '.claude' / 'emergent-learning' / '.venv',  # ~/.claude/emergent-learning/.venv
    ]:
        if possible_venv.exists():
            # Try different python executable names
            for exe_name in ['python3', 'python']:
                candidate = possible_venv / 'bin' / exe_name
                if candidate.exists():
                    venv_python = str(candidate)
                    break
            if venv_python:
                break

    if not venv_python:
        # No venv found, continue with current python (will likely fail later)
        return

    # Re-exec this script with venv python
    os.execve(venv_python, [venv_python] + sys.argv, os.environ)

# Only run venv detection when executed as script, not when imported
if __name__ == '__main__':
    _ensure_venv_python()

# Handle both module import and script execution
try:
    # When imported as module: from query import QuerySystem
    from .core import QuerySystem
    from .exceptions import (
        QuerySystemError,
        ValidationError,
        DatabaseError,
        TimeoutError,
        ConfigurationError,
    )
    from .validators import (
        MAX_DOMAIN_LENGTH,
        MAX_QUERY_LENGTH,
        MAX_TAG_COUNT,
        MAX_TAG_LENGTH,
        MIN_LIMIT,
        MAX_LIMIT,
        DEFAULT_TIMEOUT,
        MAX_TOKENS,
    )
    from .formatters import format_output, generate_accountability_banner
    from .setup import ensure_hooks_installed, ensure_full_setup
    from .cli import main
except ImportError:
    # When run as script: python query.py --context
    from core import QuerySystem
    from exceptions import (
        QuerySystemError,
        ValidationError,
        DatabaseError,
        TimeoutError,
        ConfigurationError,
    )
    from validators import (
        MAX_DOMAIN_LENGTH,
        MAX_QUERY_LENGTH,
        MAX_TAG_COUNT,
        MAX_TAG_LENGTH,
        MIN_LIMIT,
        MAX_LIMIT,
        DEFAULT_TIMEOUT,
        MAX_TOKENS,
    )
    from formatters import format_output, generate_accountability_banner
    from setup import ensure_hooks_installed, ensure_full_setup
    from cli import main

__all__ = [
    # Core
    'QuerySystem',
    # Exceptions
    'QuerySystemError',
    'ValidationError',
    'DatabaseError',
    'TimeoutError',
    'ConfigurationError',
    # Constants
    'MAX_DOMAIN_LENGTH',
    'MAX_QUERY_LENGTH',
    'MAX_TAG_COUNT',
    'MAX_TAG_LENGTH',
    'MIN_LIMIT',
    'MAX_LIMIT',
    'DEFAULT_TIMEOUT',
    'MAX_TOKENS',
    # Utilities
    'format_output',
    'generate_accountability_banner',
    'ensure_hooks_installed',
    'ensure_full_setup',
    # CLI
    'main',
]

if __name__ == '__main__':
    # When run as script, delegate to cli.main()
    exit(main())
