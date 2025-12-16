# Migrating from v0.1.x to v0.2.0

## Breaking Change Notice

**v0.2.0 is a BREAKING CHANGE.** All query methods are now async.

The QuerySystem now uses `peewee-aio` with `aiosqlite` for native async SQLite support. This provides better performance for concurrent operations and eliminates blocking I/O during database queries.

## Quick Migration (5 minutes)

### 1. Update dependencies

```bash
pip install peewee-aio[aiosqlite] aiofiles
```

Or if using requirements.txt, ensure these are present:
```
peewee-aio[aiosqlite]>=1.0.0
aiofiles>=23.0.0
```

### 2. Update your code

**Before (v1.x):**
```python
from query import QuerySystem

qs = QuerySystem()
context = qs.build_context("My task", domain="debugging")
decisions = qs.get_decisions(domain="architecture")
stats = qs.get_statistics()
```

**After (v0.2.0):**
```python
import asyncio
from query import QuerySystem

async def main():
    # Use factory method instead of __init__
    qs = await QuerySystem.create()

    # All methods now require await
    context = await qs.build_context("My task", domain="debugging")
    decisions = await qs.get_decisions(domain="architecture")
    stats = await qs.get_statistics()

    # Always cleanup when done
    await qs.cleanup()

asyncio.run(main())
```

### 3. CLI unchanged

The command-line interface works exactly the same:
```bash
python query/query.py --context
python query/query.py --domain debugging --limit 5
python query/query.py --stats
python query/query.py --validate
```

## Detailed Changes

### Initialization

| v0.1.x | v0.2.0 |
|------|--------|
| `qs = QuerySystem()` | `qs = await QuerySystem.create()` |
| `qs = QuerySystem(base_path="/path")` | `qs = await QuerySystem.create(base_path="/path")` |

### All Query Methods

Every query method now requires `await`:

| Method | v0.1.x | v0.2.0 |
|--------|------|--------|
| Build context | `qs.build_context(...)` | `await qs.build_context(...)` |
| Get golden rules | `qs.get_golden_rules()` | `await qs.get_golden_rules()` |
| Query by domain | `qs.query_by_domain(...)` | `await qs.query_by_domain(...)` |
| Query by tags | `qs.query_by_tags(...)` | `await qs.query_by_tags(...)` |
| Query recent | `qs.query_recent(...)` | `await qs.query_recent(...)` |
| Get decisions | `qs.get_decisions(...)` | `await qs.get_decisions(...)` |
| Get assumptions | `qs.get_assumptions(...)` | `await qs.get_assumptions(...)` |
| Get invariants | `qs.get_invariants(...)` | `await qs.get_invariants(...)` |
| Get spike reports | `qs.get_spike_reports(...)` | `await qs.get_spike_reports(...)` |
| Get experiments | `qs.get_active_experiments()` | `await qs.get_active_experiments()` |
| Get CEO reviews | `qs.get_pending_ceo_reviews()` | `await qs.get_pending_ceo_reviews()` |
| Get statistics | `qs.get_statistics()` | `await qs.get_statistics()` |
| Get violations | `qs.get_violations(...)` | `await qs.get_violations(...)` |
| Validate database | `qs.validate_database()` | `await qs.validate_database()` |

### Cleanup

**New requirement:** Always call cleanup when done:

```python
async def main():
    qs = await QuerySystem.create()
    try:
        # ... your code ...
    finally:
        await qs.cleanup()
```

Or use a context manager pattern:
```python
async def main():
    qs = await QuerySystem.create()
    try:
        result = await qs.build_context("task")
    finally:
        await qs.cleanup()
    return result
```

## Common Migration Patterns

### Pattern 1: Simple script

**Before:**
```python
from query import QuerySystem

def get_context():
    qs = QuerySystem()
    return qs.build_context("my task")

print(get_context())
```

**After:**
```python
import asyncio
from query import QuerySystem

async def get_context():
    qs = await QuerySystem.create()
    try:
        return await qs.build_context("my task")
    finally:
        await qs.cleanup()

print(asyncio.run(get_context()))
```

### Pattern 2: Multiple queries

**Before:**
```python
from query import QuerySystem

qs = QuerySystem()
context = qs.build_context("task")
stats = qs.get_statistics()
decisions = qs.get_decisions(domain="api")
```

**After:**
```python
import asyncio
from query import QuerySystem

async def main():
    qs = await QuerySystem.create()
    try:
        context = await qs.build_context("task")
        stats = await qs.get_statistics()
        decisions = await qs.get_decisions(domain="api")
        return context, stats, decisions
    finally:
        await qs.cleanup()

context, stats, decisions = asyncio.run(main())
```

### Pattern 3: Integration with existing async code

If you already have async code:
```python
async def my_existing_async_function():
    # Create QuerySystem in your async context
    qs = await QuerySystem.create()
    try:
        context = await qs.build_context("task")
        # ... use context ...
    finally:
        await qs.cleanup()
```

### Pattern 4: Concurrent queries

New in v0.2.0 - run multiple queries concurrently:
```python
import asyncio
from query import QuerySystem

async def main():
    qs = await QuerySystem.create()
    try:
        # Run multiple queries concurrently
        context, stats, decisions = await asyncio.gather(
            qs.build_context("task"),
            qs.get_statistics(),
            qs.get_decisions(domain="api")
        )
        return context, stats, decisions
    finally:
        await qs.cleanup()
```

## Why Async?

1. **Non-blocking I/O**: Database queries no longer block the event loop
2. **Better concurrency**: Multiple queries can run concurrently with `asyncio.gather()`
3. **Modern Python**: Aligns with async/await patterns used in modern Python frameworks
4. **Performance**: Reduced latency when performing multiple operations

## Error Codes

Error codes remain unchanged from v0.1.x:

| Code | Description |
|------|-------------|
| QS000 | General query system error |
| QS001 | Validation error (invalid input) |
| QS002 | Database error (connection/query failed) |
| QS003 | Timeout error (query took too long) |
| QS004 | Configuration error (setup failed) |

## Troubleshooting

### "coroutine was never awaited" warning

You forgot to `await` a query method:
```python
# Wrong
context = qs.build_context("task")  # Returns coroutine, not result

# Right
context = await qs.build_context("task")
```

### "RuntimeError: no running event loop"

You're calling async code outside an async context:
```python
# Wrong - calling from sync code
async def get_context():
    qs = await QuerySystem.create()
    return await qs.build_context("task")

result = get_context()  # Error!

# Right - use asyncio.run()
result = asyncio.run(get_context())
```

### "Event loop is already running"

You're calling `asyncio.run()` from within an async context (like Jupyter):
```python
# In Jupyter, use await directly instead of asyncio.run()
qs = await QuerySystem.create()
context = await qs.build_context("task")
await qs.cleanup()
```

## Version Check

To verify you're on v0.2.0:
```python
from query import __version__
print(__version__)  # Should print '0.2.0'
```
