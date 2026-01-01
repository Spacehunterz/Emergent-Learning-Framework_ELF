# ELF Refactor Plan v2 (Updated 2025-12-31)

> **This plan supersedes ELF-REFACTOR-PLAN.md** based on actual current state analysis.

## Executive Summary

The original plan was based on outdated assumptions. The actual situation is:

- **Two parallel QuerySystem implementations exist** (sync in query.py, async in core.py)
- The pyproject.toml and modular structure already exist
- The problem is not "monolith needs decomposition" but "two versions need unification"

### Current State

| File | Lines | Purpose | Status |
|------|-------|---------|--------|
| `query.py` | 2620 | Sync QuerySystem, monolithic | **Entry point for hooks** |
| `core.py` | 421 | Async QuerySystem, mixin-based | **Modern, clean** |
| `context.py` | 780 | Context building logic | Extracted |
| `cli.py` | 479 | CLI interface | Extracted |
| `queries/` | 10 files | Domain-specific query mixins | Extracted |

### The Core Problem

1. **Hooks call query.py directly** (`python query.py --context`)
2. **query.py is sync**, core.py is async
3. **Both are complete implementations** - not partial extraction
4. **External scripts depend on sync API**

---

## Phase 0: Decision Point

Before proceeding, choose one of these strategies:

### Option A: Deprecate query.py, Migrate to Async
- Make core.py the single source of truth
- Update all callers to use async API
- Eventually delete query.py
- **Risk**: Breaking change for hooks/scripts
- **Benefit**: Clean architecture, no duplication

### Option B: Keep Sync Wrapper, Delegate to Async
- query.py becomes a thin sync wrapper
- It calls `asyncio.run()` to invoke core.py's async methods
- External API unchanged
- **Risk**: Some complexity in sync→async bridge
- **Benefit**: No breaking changes

### Option C: Keep Both (Current State)
- Accept duplication
- Only touch to fix bugs
- **Risk**: Maintenance burden, drift between versions
- **Benefit**: Zero risk of breaking anything

**Recommended: Option B** - Keep sync entry point, delegate to async internals.

---

## Phase 1: Safety Net (Same as Original)

### Step 1.1: Verify Clean State
```bash
git status
# If dirty: git stash or git commit -m "WIP: pre-refactor state"
```

### Step 1.2: Create Restore Point
```bash
git tag -a v0.3.2-pre-unification -m "Working state before sync/async unification"
git push origin v0.3.2-pre-unification
```

### Step 1.3: Create Work Branch
```bash
git checkout -b refactor/unify-query-system
```

---

## Phase 2: Map All External References

### Step 2.1: Find All query.py Callers
```bash
grep -r "query\.py\|from query import\|import query" \
  --include="*.py" --include="*.sh" --include="*.ps1" \
  . | grep -v __pycache__ | grep -v ".pyc"
```

### Step 2.2: Categorize References

**Critical (must not break):**
- `src/hooks/learning-loop/user_prompt_inject_context.py` - ELF context hook
- `tools/setup/install.ps1` - Installation
- `scripts/*.sh` - Utility scripts

**Internal (can update):**
- Tests referencing query.py
- Documentation

---

## Phase 3: Create Sync Wrapper (Option B)

### Step 3.1: Slim Down query.py

Transform query.py from a 2620-line monolith into a ~200-line sync wrapper:

```python
#!/usr/bin/env python3
"""
Emergent Learning Framework - Query System (Sync Entry Point)

This module provides a synchronous interface to the async QuerySystem.
For internal/programmatic use, prefer the async API in query.core.

CLI Usage:
    python query.py --context
    python query.py --domain debugging
"""

import asyncio
import sys
from pathlib import Path
from typing import Dict, Any, Optional, List

# Import the real async implementation
from .core import QuerySystem as AsyncQuerySystem
from .exceptions import QuerySystemError, ValidationError, DatabaseError
from .validators import MAX_DOMAIN_LENGTH, MAX_QUERY_LENGTH, MAX_TOKENS


class QuerySystem:
    """
    Synchronous wrapper around the async QuerySystem.

    This class exists for backward compatibility with scripts that
    call query.py directly. New code should use the async API.
    """

    def __init__(self, base_path: Optional[str] = None, debug: bool = False,
                 session_id: Optional[str] = None, agent_id: Optional[str] = None,
                 current_location: Optional[str] = None):
        """Initialize sync wrapper - creates async instance internally."""
        self._async_qs = None
        self._init_args = {
            'base_path': base_path,
            'debug': debug,
            'session_id': session_id,
            'agent_id': agent_id,
            'current_location': current_location
        }

    def _ensure_async_qs(self):
        """Lazily initialize the async QuerySystem."""
        if self._async_qs is None:
            self._async_qs = asyncio.run(AsyncQuerySystem.create(**self._init_args))
        return self._async_qs

    def build_context(self, task: str = "", **kwargs) -> str:
        """Build context (sync wrapper)."""
        qs = self._ensure_async_qs()
        return asyncio.run(qs.build_context(task, **kwargs))

    def query_by_domain(self, domain: str, limit: int = 10, **kwargs) -> Dict[str, Any]:
        """Query by domain (sync wrapper)."""
        qs = self._ensure_async_qs()
        return asyncio.run(qs.query_by_domain(domain, limit, **kwargs))

    def get_golden_rules(self) -> str:
        """Get golden rules (sync wrapper)."""
        qs = self._ensure_async_qs()
        return asyncio.run(qs.get_golden_rules())

    # ... Add wrappers for all other public methods ...

    def cleanup(self):
        """Clean up resources."""
        if self._async_qs:
            asyncio.run(self._async_qs.cleanup())


def main():
    """CLI entry point - delegates to cli.py."""
    from .cli import main as cli_main
    cli_main()


if __name__ == "__main__":
    main()
```

### Step 3.2: Verify No Behavior Change

Run the exact commands that hooks use:
```bash
# Test context generation
python src/query/query.py --context

# Test domain query
python src/query/query.py --domain meta-learning

# Test stats
python src/query/query.py --stats

# Compare output to original (should be identical)
```

### Step 3.3: Update __init__.py

```python
# src/query/__init__.py
"""
ELF Query System

Public API:
    # Async (preferred for new code)
    from query.core import QuerySystem
    qs = await QuerySystem.create()

    # Sync (for scripts/CLI)
    from query import QuerySystem
    qs = QuerySystem()
"""

# Export async version as default
from .core import QuerySystem

# Also export sync wrapper for backward compat
from .query import QuerySystem as SyncQuerySystem

from .exceptions import (
    QuerySystemError,
    ValidationError,
    DatabaseError,
    TimeoutError,
    ConfigurationError,
)

from .cli import main

__all__ = [
    'QuerySystem',       # Async (preferred)
    'SyncQuerySystem',   # Sync wrapper
    'QuerySystemError',
    'ValidationError',
    'DatabaseError',
    'TimeoutError',
    'ConfigurationError',
    'main',
]

__version__ = '0.4.0'  # Version bump for API clarification
```

---

## Phase 4: Clean Up

### Step 4.1: Remove Backup Files
```bash
rm src/query/query.py.before_improvements
rm src/query/query.py.pre-hardening
```

### Step 4.2: Move Markdown Files Out of src/query/

Documentation doesn't belong in the source directory:
```bash
mkdir -p docs/query/
mv src/query/*.md docs/query/
# Keep only ARCHITECTURE.md if it's actually used
```

### Step 4.3: Update .gitignore
```bash
# Add to .gitignore
*.py.bak
*.py.backup
*.py.before_*
*.py.pre-*
```

---

## Phase 5: Test Everything

### Step 5.1: Run Full Test Suite
```bash
python -m pytest tests/ -v
```

### Step 5.2: Test Hook Integration
```bash
# Simulate what the hook does
python src/query/query.py --context
```

### Step 5.3: Test Module Import
```python
# Test both import paths work
from query import QuerySystem          # Async
from query.query import QuerySystem    # Sync
from query.core import QuerySystem     # Async (explicit)
```

---

## Phase 6: Commit and Version

### Step 6.1: Commit
```bash
git add -A
git commit -m "refactor: unify query system to single async implementation

- query.py is now a thin sync wrapper over core.py
- All query logic lives in core.py + mixins
- External API unchanged (sync calls still work)
- Removed duplicate code (~2000 lines)
- Cleaned up backup files and misplaced docs

BREAKING: None (backward compatible)
"
```

### Step 6.2: Version Bump
```bash
echo "0.4.0" > VERSION
# Update pyproject.toml version
```

---

## Checklist

Before considering complete:

- [ ] `python query.py --context` works (hook compatibility)
- [ ] `python -m query --context` works (module mode)
- [ ] All tests pass (`pytest tests/`)
- [ ] No import errors from any path
- [ ] Hook still injects context on session start
- [ ] Install script still works
- [ ] Backup files removed
- [ ] Documentation moved out of src/query/

---

## Rollback

If something breaks:
```bash
git checkout v0.3.2-pre-unification
git checkout -B main
git push --force origin main  # CAREFUL: force push
```

---

## Future Work (Not This Refactor)

1. **Phase out sync wrapper**: Once all external scripts are updated, deprecate SyncQuerySystem
2. **Consider pyproject entry points**: Make `elf-query` a proper CLI command
3. **Add type hints**: The async version in core.py should have full typing
4. **Performance**: Profile context generation, consider caching

---

## Key Differences from Original Plan

| Original Plan | This Plan |
|---------------|-----------|
| Assumed monolith needs decomposition | Recognizes two parallel implementations |
| Proposed creating src/elf/ | Uses existing src/query/ structure |
| Suggested creating pyproject.toml | Already exists |
| 10 phases | 6 focused phases |
| Git worktree approach | Simpler branch approach (lower risk) |

The original plan was good but based on outdated assumptions. This plan reflects the actual current state and addresses the real problem: unifying two implementations, not decomposing one.
