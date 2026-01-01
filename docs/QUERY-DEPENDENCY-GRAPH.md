# Query System Dependency Graph

Generated: 2025-12-31

## Critical Path (Hook → Context)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         CLAUDE CODE SESSION                              │
│                                                                          │
│  User types prompt                                                       │
│         │                                                                │
│         ▼                                                                │
│  ┌──────────────────────────────────────────────────┐                   │
│  │  UserPromptSubmit Hook                           │                   │
│  │  src/hooks/learning-loop/user_prompt_inject_     │                   │
│  │  context.py                                      │                   │
│  │                                                  │                   │
│  │  subprocess.run([python, query.py, --context])  │◄── SYNC CALL      │
│  └──────────────────────────────────────────────────┘                   │
│         │                                                                │
│         │ subprocess (not import)                                        │
│         ▼                                                                │
└─────────────────────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         query.py (2620 lines)                            │
│                         SYNC MONOLITH                                    │
│                                                                          │
│  class QuerySystem:           ◄── Duplicate of core.py                  │
│      def __init__()                                                      │
│      def build_context()      ◄── Called by --context                   │
│      def query_by_domain()                                               │
│      def get_golden_rules()                                              │
│      ...                                                                 │
│                                                                          │
│  def main():                  ◄── CLI entry point                       │
│      argparse → QuerySystem → print output                              │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
          │
          │ imports
          ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         HELPER MODULES                                   │
│                                                                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │
│  │ validators  │  │ formatters  │  │ exceptions  │  │   utils     │    │
│  │   .py       │  │    .py      │  │    .py      │  │    .py      │    │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘    │
│                                                                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                      │
│  │  models.py  │  │  setup.py   │  │config_loader│                      │
│  │  (Peewee)   │  │             │  │    .py      │                      │
│  └─────────────┘  └─────────────┘  └─────────────┘                      │
└─────────────────────────────────────────────────────────────────────────┘
```

## Parallel Implementation (Unused by Hooks)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         __init__.py                                      │
│                                                                          │
│  from .core import QuerySystem  ◄── Exports ASYNC version               │
│  from .cli import main                                                   │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
          │
          │ imports
          ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         core.py (421 lines)                              │
│                         ASYNC + MIXINS                                   │
│                                                                          │
│  class QuerySystem(                                                      │
│      HeuristicQueryMixin,     ◄── from queries/heuristics.py            │
│      LearningQueryMixin,      ◄── from queries/learnings.py             │
│      ExperimentQueryMixin,    ◄── from queries/experiments.py           │
│      ViolationQueryMixin,     ◄── from queries/violations.py            │
│      DecisionQueryMixin,      ◄── from queries/decisions.py             │
│      AssumptionQueryMixin,    ◄── from queries/assumptions.py           │
│      InvariantQueryMixin,     ◄── from queries/invariants.py            │
│      SpikeQueryMixin,         ◄── from queries/spikes.py                │
│      StatisticsQueryMixin,    ◄── from queries/statistics.py            │
│      ContextBuilderMixin,     ◄── from context.py                       │
│      BaseQueryMixin           ◄── from queries/base.py                  │
│  ):                                                                      │
│      async def create()       ◄── Factory method                        │
│      async def build_context()                                           │
│      async def cleanup()                                                 │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
          │
          │ imports mixins from
          ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         queries/ subdirectory                            │
│                                                                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │
│  │  base.py    │  │heuristics.py│  │learnings.py │  │experiments  │    │
│  │  3.5KB      │  │  11.9KB     │  │   6.2KB     │  │   4.9KB     │    │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘    │
│                                                                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │
│  │violations.py│  │decisions.py │  │assumptions  │  │invariants.py│    │
│  │   6.7KB     │  │   3.6KB     │  │   8.3KB     │  │   5.5KB     │    │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘    │
│                                                                          │
│  ┌─────────────┐  ┌─────────────┐                                       │
│  │  spikes.py  │  │statistics.py│  context.py (780 lines)              │
│  │   6.4KB     │  │   5.2KB     │  ContextBuilderMixin                  │
│  └─────────────┘  └─────────────┘                                       │
└─────────────────────────────────────────────────────────────────────────┘
```

## External Callers

### Subprocess Callers (require query.py to stay runnable)

| File | How It Calls | Critical? |
|------|--------------|-----------|
| `user_prompt_inject_context.py` | `subprocess.run([python, query.py, --context])` | **YES - HOOK** |
| `install.ps1` | Copies query.py, docs reference it | YES |
| `bootstrap-recovery.sh` | `query.py --stats` | Medium |
| `self-test.sh` | `query.py --stats`, `--golden-rules`, etc. | Medium |
| `demo.sh` | `query.py --help`, `--validate` | Low |

### Import Callers (can migrate to async)

| File | Import | Can Migrate? |
|------|--------|--------------|
| `mcp/elf_server.py` | `from query import QuerySystem` | Already async |
| `tests/test_edge_cases_v2.py` | `from query.core import QuerySystem` | Already async |
| `tests/test_destructive_edge_cases.py` | `from query import QuerySystem` | Already async |
| `tests/test_sqlite_edge_cases.py` | `from query import QuerySystem` | Already async |
| `tools/benchmarks/*.py` | `from query import QuerySystem` | Already async |
| `src/query/test_enhancements.py` | `from query import QuerySystem` | Needs update (sync) |

### Internal Imports (within query module)

| Module | Imports From |
|--------|--------------|
| `query.py` | models, validators, formatters, exceptions, utils, setup, plan_postmortem, model_detection |
| `core.py` | models, validators, exceptions, queries/*, context |
| `cli.py` | (needs checking) |
| `context.py` | models, formatters, project_context, plan_postmortem, session_integration |

## Migration Strategy

### What MUST Stay Sync
```
query.py --context  (subprocess from hook)
query.py --stats    (subprocess from scripts)
query.py --*        (all CLI flags)
```

### What CAN Be Async
```
QuerySystem class internals
All mixin methods
Database operations
Context building
```

### Solution: Thin Sync Shell + Async Core

```
                    BEFORE                              AFTER
                    ══════                              ═════

┌────────────────────────────┐        ┌────────────────────────────┐
│ query.py (2620 lines)      │        │ query.py (~150 lines)      │
│ Full sync implementation   │   →    │ Thin sync shell            │
│ Duplicate of core.py       │        │ asyncio.run(core.method()) │
└────────────────────────────┘        └────────────────────────────┘
              +                                    │
┌────────────────────────────┐                     │
│ core.py (421 lines)        │                     ▼
│ Async + mixins             │        ┌────────────────────────────┐
│ Unused by hooks            │   →    │ core.py (unchanged)        │
└────────────────────────────┘        │ Single source of truth     │
                                      │ All async implementation   │
                                      └────────────────────────────┘
```

## Files to Modify (Ranked by Risk)

### High Risk (touches critical path)
1. `query.py` - Replace 2620 lines with ~150 line wrapper

### Medium Risk (needs testing)
2. `cli.py` - May need async bridge updates
3. `src/query/test_enhancements.py` - Uses sync API

### Low Risk (already async)
4. Tests - Most already use async API
5. MCP server - Already async
6. Benchmarks - Already async

### No Risk (documentation only)
7. `create-wiki.py` - String references only
8. `dependency-check.sh` - Comments only
9. `self-test.sh` - Can stay as-is (CLI calls)
