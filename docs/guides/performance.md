# Performance Guide

Comprehensive guide to optimizing performance in the Emergent Learning Framework (ELF).

**Last Updated:** 2026-01-05
**Status:** Production
**Audience:** Developers, System Architects, Performance Engineers

---

## Table of Contents

- [Overview](#overview)
- [Query Optimization](#query-optimization)
- [Database Indexing Strategies](#database-indexing-strategies)
- [Token Cost Optimization](#token-cost-optimization)
- [Memory Usage Tuning](#memory-usage-tuning)
- [Dashboard Performance](#dashboard-performance)
- [Profiling Tools](#profiling-tools)
- [Benchmarking](#benchmarking)
- [Best Practices](#best-practices)

---

## Overview

ELF performance is critical because it runs in the hot path of Claude Code sessions. Every query adds latency to user interactions.

### Performance Targets

- **Query Response Time**: <100ms for simple queries, <500ms for complex context building
- **Memory Footprint**: <50MB for typical usage
- **Database Size**: <10MB for typical installation (thousands of learnings)
- **Token Cost**: <2000 tokens for full context (Tier 0-3)
- **Concurrent Operations**: Support 10+ agents without contention

### Performance Monitoring

```python
# Query system tracks performance automatically
from query.core import QuerySystem

qs = await QuerySystem.create(debug=True)
result = await qs.build_context("debugging")

# Check query stats
stats = await qs.get_statistics()
print(f"Total queries: {stats['total_queries']}")
print(f"Avg query time: {stats['avg_query_time_ms']}ms")
```

---

## Query Optimization

### Use LIMIT and OFFSET Effectively

**Always use LIMIT** for queries that could return many rows:

```python
# GOOD - Limited results
results = await Heuristic.select()\
    .where(Heuristic.domain == "debugging")\
    .order_by(Heuristic.confidence.desc())\
    .limit(10)

# BAD - Unbounded query
results = await Heuristic.select()\
    .where(Heuristic.domain == "debugging")\
    .order_by(Heuristic.confidence.desc())
# Could return thousands of rows!
```

**Use OFFSET for pagination**:

```python
# Paginate through large result sets
page_size = 20
offset = 0

while True:
    results = await Heuristic.select()\
        .where(Heuristic.domain == "debugging")\
        .limit(page_size)\
        .offset(offset)

    if not results:
        break

    process_results(results)
    offset += page_size
```

### Optimize ORDER BY Clauses

**Use indexed columns for sorting**:

```python
# GOOD - Sorts by indexed column
results = await Learning.select()\
    .where(Learning.domain == "debugging")\
    .order_by(Learning.created_at.desc())\
    .limit(10)
# Uses index: idx_learnings_created_at

# BAD - Sorts by non-indexed column
results = await Learning.select()\
    .order_by(Learning.summary)\
    .limit(10)
# Full table scan + sort
```

### Use Compound Queries

**Combine filters in WHERE clause**:

```python
# GOOD - Single query with compound conditions
results = await Heuristic.select()\
    .where(
        (Heuristic.domain == "debugging") &
        (Heuristic.confidence >= 0.8) &
        (Heuristic.is_golden == True)
    )\
    .limit(10)
# Uses compound index: idx_heuristics_domain_confidence

# BAD - Multiple queries
domain_results = await Heuristic.select()\
    .where(Heuristic.domain == "debugging")
filtered = [h for h in domain_results if h.confidence >= 0.8 and h.is_golden]
# Fetches ALL domain results, filters in Python
```

### Avoid N+1 Query Problems

**Use joins or prefetch**:

```python
# BAD - N+1 queries
learnings = await Learning.select().limit(10)
for learning in learnings:
    # This triggers a separate query for each learning!
    related = await Heuristic.select()\
        .where(Heuristic.source_id == learning.id)

# GOOD - Single query with join
query = Learning.select(Learning, Heuristic)\
    .join(Heuristic, on=(Learning.id == Heuristic.source_id))\
    .limit(10)
```

### Query Result Caching

**Cache frequently accessed data**:

```python
from functools import lru_cache

class QuerySystem:
    @lru_cache(maxsize=128)
    async def get_golden_rules_cached(self) -> List[str]:
        """Get golden rules with caching."""
        rules = await Heuristic.select()\
            .where(Heuristic.is_golden == True)\
            .order_by(Heuristic.confidence.desc())

        return [h.rule for h in rules]

    def clear_cache(self):
        """Clear cache when data changes."""
        self.get_golden_rules_cached.cache_clear()
```

### Use Query Explain for Analysis

```python
import sqlite3

conn = sqlite3.connect("memory/index.db")
cursor = conn.cursor()

# Explain query plan
cursor.execute("""
    EXPLAIN QUERY PLAN
    SELECT * FROM heuristics
    WHERE domain = 'debugging'
      AND confidence >= 0.8
    ORDER BY confidence DESC
    LIMIT 10
""")

for row in cursor.fetchall():
    print(row)
# Output shows which indexes are used
```

**Example output**:

```
SEARCH TABLE heuristics USING INDEX idx_heuristics_domain_confidence (domain=? AND confidence>?)
```

---

## Database Indexing Strategies

### Understanding Current Indexes

From `src/query/models.py`:

```python
class Learning(BaseModel):
    # ...
    class Meta:
        indexes = (
            (('domain',), False),              # Single column
            (('type',), False),
            (('tags',), False),
            (('created_at',), False),
            (('domain', 'created_at'), False), # Compound index
        )

class Heuristic(BaseModel):
    # ...
    class Meta:
        indexes = (
            (('domain',), False),
            (('is_golden',), False),
            (('confidence',), False),
            (('created_at',), False),
            (('domain', 'confidence'), False), # Compound index
            (('project_path',), False),
        )
```

### Index Selection Rules

**1. Index columns used in WHERE clauses**:

```python
# Query frequently filters by domain
SELECT * FROM heuristics WHERE domain = 'debugging'
# → Create index on domain column ✓ (exists)

# Query frequently filters by confidence
SELECT * FROM heuristics WHERE confidence >= 0.8
# → Create index on confidence column ✓ (exists)
```

**2. Index columns used in ORDER BY**:

```python
# Query frequently sorts by created_at
SELECT * FROM learnings ORDER BY created_at DESC LIMIT 10
# → Create index on created_at column ✓ (exists)
```

**3. Use compound indexes for common filter combinations**:

```python
# Common query pattern: domain + confidence
SELECT * FROM heuristics
WHERE domain = 'debugging' AND confidence >= 0.8
ORDER BY confidence DESC
# → Compound index (domain, confidence) ✓ (exists)
```

### Index Ordering in Compound Indexes

**Rule**: Put equality columns first, range columns second:

```python
# GOOD - Equality first, range second
CREATE INDEX idx_heuristics_domain_confidence
ON heuristics (domain, confidence)

# Query can use this index fully:
WHERE domain = 'debugging' AND confidence >= 0.8

# BAD - Range first, equality second
CREATE INDEX idx_heuristics_confidence_domain
ON heuristics (confidence, domain)

# Query can only use confidence part:
WHERE domain = 'debugging' AND confidence >= 0.8
```

### When NOT to Index

**Don't index**:

1. **Small tables** (<1000 rows)
2. **High cardinality columns with few queries** (e.g., unique identifiers)
3. **Columns that change frequently** (index maintenance overhead)
4. **Wide columns** (TEXT, BLOB) - index only prefixes

```python
# DON'T index large text fields
CREATE INDEX idx_learning_summary ON learnings(summary)
# Index would be huge and rarely useful

# DO index metadata about the text
CREATE INDEX idx_learning_domain ON learnings(domain)
```

### Monitoring Index Usage

```sql
-- Check which indexes exist
SELECT name, tbl_name, sql
FROM sqlite_master
WHERE type = 'index'
  AND tbl_name = 'heuristics';

-- Analyze table statistics
ANALYZE heuristics;

-- Check index efficiency
EXPLAIN QUERY PLAN
SELECT * FROM heuristics WHERE domain = 'debugging';
```

### Index Maintenance

```python
# Rebuild indexes periodically (after bulk operations)
import sqlite3

conn = sqlite3.connect("memory/index.db")
cursor = conn.cursor()

# Reindex specific table
cursor.execute("REINDEX heuristics")

# Update statistics for query planner
cursor.execute("ANALYZE")

conn.commit()
conn.close()
```

---

## Token Cost Optimization

ELF uses a tiered context system to minimize token costs while providing relevant information.

### Understanding Context Tiers

From `src/query/context.py`:

```python
# Tier 0: Project-specific (highest relevance)
# - Project heuristics
# - Project learnings
# Cost: ~200-500 tokens

# Tier 1: Golden rules (universal truths)
# - is_golden = True heuristics
# Cost: ~300-600 tokens

# Tier 2: Domain-specific (task-relevant)
# - Heuristics for requested domains
# - Recent learnings in domain
# Cost: ~500-1000 tokens

# Tier 3: General context (background)
# - Recent failures across domains
# - Active experiments
# Cost: ~300-500 tokens

# Total: ~1300-2600 tokens (target: <2000)
```

### Limit Results Per Tier

```python
# From context.py - optimized limits
TIER_0_LIMIT = 5   # Project-specific heuristics
TIER_1_LIMIT = 10  # Golden rules
TIER_2_LIMIT = 8   # Domain heuristics
TIER_3_LIMIT = 5   # Recent failures
```

### Optimize Heuristic Formatting

```python
# GOOD - Concise formatting
def format_heuristic(h: Heuristic) -> str:
    return f"- {h.rule} (confidence: {h.confidence:.2f})"
# ~30-50 tokens per heuristic

# BAD - Verbose formatting
def format_heuristic_verbose(h: Heuristic) -> str:
    return f"""
    Rule: {h.rule}
    Explanation: {h.explanation}
    Confidence: {h.confidence}
    Validated: {h.times_validated} times
    Domain: {h.domain}
    Created: {h.created_at}
    """
# ~100-150 tokens per heuristic!
```

### Token Budget Tracking

```python
class ContextBuilder:
    def __init__(self, max_tokens: int = 2000):
        self.max_tokens = max_tokens
        self.current_tokens = 0

    def add_section(self, content: str) -> bool:
        """Add content if within budget."""
        estimated_tokens = len(content) // 4  # Rough estimate

        if self.current_tokens + estimated_tokens > self.max_tokens:
            return False

        self.current_tokens += estimated_tokens
        return True
```

### Selective Context Loading

```python
# Only load what's needed for the task
async def build_minimal_context(task: str) -> str:
    """Build minimal context for simple tasks."""
    if is_simple_query(task):
        # Only Tier 1 (golden rules)
        return await build_tier_1_only()
    elif is_domain_specific(task):
        # Tier 1 + Tier 2 (golden rules + domain)
        return await build_tier_1_and_2(extract_domain(task))
    else:
        # Full context (all tiers)
        return await build_full_context(task)
```

### Deduplication

```python
def deduplicate_heuristics(heuristics: List[Heuristic]) -> List[Heuristic]:
    """Remove duplicate rules to save tokens."""
    seen_rules = set()
    unique = []

    for h in heuristics:
        if h.rule not in seen_rules:
            seen_rules.add(h.rule)
            unique.append(h)

    return unique
```

---

## Memory Usage Tuning

### Connection Pooling

```python
from peewee_aio import Manager

# Configure connection pool
manager = Manager(
    'aiosqlite:///memory/index.db',
    max_connections=10,  # Limit concurrent connections
    timeout=5.0          # Connection timeout
)
```

### Cleanup Unused Connections

```python
class QuerySystem:
    async def cleanup(self):
        """Clean up resources."""
        if self.manager:
            # Close all connections
            await self.manager.close()
            self.manager = None
```

### Limit In-Memory Results

```python
# BAD - Loads everything into memory
all_learnings = await Learning.select()
for learning in all_learnings:
    process(learning)

# GOOD - Stream results
async for learning in Learning.select():
    process(learning)
    # Each row is garbage collected after processing
```

### Use Generators for Large Datasets

```python
async def iter_learnings(domain: str):
    """Iterate learnings without loading all into memory."""
    async for learning in Learning.select()\
        .where(Learning.domain == domain)\
        .order_by(Learning.created_at.desc()):
        yield learning

# Usage
async for learning in iter_learnings("debugging"):
    print(learning.title)
```

### Database VACUUM

Reduce database file size by reclaiming unused space:

```python
import sqlite3

def vacuum_database(db_path: str):
    """Compact database file."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Get size before
    cursor.execute("PRAGMA page_count")
    pages_before = cursor.fetchone()[0]

    # Vacuum to reclaim space
    cursor.execute("VACUUM")

    # Get size after
    cursor.execute("PRAGMA page_count")
    pages_after = cursor.fetchone()[0]

    print(f"Reclaimed {pages_before - pages_after} pages")

    conn.close()
```

**When to VACUUM**:

- After deleting many rows
- After bulk updates
- Periodically (e.g., monthly)
- NOT during heavy usage (locks database)

### Memory Profiling

```python
import tracemalloc

# Start profiling
tracemalloc.start()

# Run operations
qs = await QuerySystem.create()
result = await qs.build_context("debugging")

# Check memory usage
current, peak = tracemalloc.get_traced_memory()
print(f"Current: {current / 1024 / 1024:.1f} MB")
print(f"Peak: {peak / 1024 / 1024:.1f} MB")

# Stop profiling
tracemalloc.stop()
```

---

## Dashboard Performance

### Optimize Dashboard Queries

The dashboard runs queries frequently - optimize them:

```python
# From src/query/dashboard.py

# GOOD - Efficient query with limit
def get_recent_learnings(limit: int = 10) -> List[Dict]:
    return Learning.select()\
        .order_by(Learning.created_at.desc())\
        .limit(limit)\
        .dicts()

# BAD - Loads all then slices in Python
def get_recent_learnings_bad() -> List[Dict]:
    all_learnings = Learning.select()\
        .order_by(Learning.created_at.desc())\
        .dicts()
    return list(all_learnings)[:10]  # Loads everything!
```

### Cache Dashboard Data

```python
from functools import lru_cache
from datetime import datetime, timedelta

class DashboardCache:
    def __init__(self, ttl_seconds: int = 60):
        self.ttl = ttl_seconds
        self.cache = {}

    def get(self, key: str):
        """Get cached value if not expired."""
        if key in self.cache:
            value, timestamp = self.cache[key]
            age = (datetime.now() - timestamp).total_seconds()

            if age < self.ttl:
                return value

        return None

    def set(self, key: str, value):
        """Cache value with timestamp."""
        self.cache[key] = (value, datetime.now())

# Usage
cache = DashboardCache(ttl_seconds=60)

def get_dashboard_stats():
    cached = cache.get('stats')
    if cached:
        return cached

    stats = compute_expensive_stats()
    cache.set('stats', stats)
    return stats
```

### Lazy Load Dashboard Sections

```html
<!-- Load critical sections first -->
<div id="recent-learnings">
  <!-- Loaded immediately -->
</div>

<!-- Load non-critical sections on demand -->
<div id="statistics" class="lazy-load">
  <button onclick="loadStatistics()">Show Statistics</button>
</div>

<script>
function loadStatistics() {
  fetch('/api/statistics')
    .then(r => r.json())
    .then(data => renderStatistics(data));
}
</script>
```

### Pagination in Dashboard

```python
def get_learnings_page(page: int = 1, per_page: int = 20):
    """Get paginated learnings."""
    offset = (page - 1) * per_page

    learnings = Learning.select()\
        .order_by(Learning.created_at.desc())\
        .limit(per_page)\
        .offset(offset)

    total = Learning.select().count()
    total_pages = (total + per_page - 1) // per_page

    return {
        'learnings': list(learnings.dicts()),
        'page': page,
        'per_page': per_page,
        'total': total,
        'total_pages': total_pages
    }
```

---

## Profiling Tools

### Built-in Python Profiling

```python
import cProfile
import pstats

# Profile a function
profiler = cProfile.Profile()
profiler.enable()

# Run code to profile
qs = await QuerySystem.create()
result = await qs.build_context("debugging")

profiler.disable()

# Print stats
stats = pstats.Stats(profiler)
stats.sort_stats('cumulative')
stats.print_stats(20)  # Top 20 functions
```

### Line-by-Line Profiling

```python
from line_profiler import LineProfiler

def profile_function():
    lp = LineProfiler()

    # Add functions to profile
    lp.add_function(QuerySystem.build_context)
    lp.add_function(Heuristic.select)

    # Run profiler
    lp.run('result = await qs.build_context("debugging")')

    # Print results
    lp.print_stats()
```

### Memory Profiling

```python
from memory_profiler import profile

@profile
async def build_context_profiled(task: str):
    """Profile memory usage of context building."""
    qs = await QuerySystem.create()
    result = await qs.build_context(task)
    return result

# Run with:
# python -m memory_profiler script.py
```

### SQLite Query Profiling

```python
import sqlite3
import time

class ProfilingConnection(sqlite3.Connection):
    def execute(self, sql, parameters=None):
        start = time.time()
        result = super().execute(sql, parameters or [])
        elapsed = time.time() - start

        if elapsed > 0.1:  # Log slow queries
            print(f"SLOW QUERY ({elapsed:.3f}s): {sql}")

        return result

# Use profiling connection
conn = sqlite3.connect(
    "memory/index.db",
    factory=ProfilingConnection
)
```

### Async Profiling

```python
import asyncio
import time

class AsyncProfiler:
    def __init__(self):
        self.timings = {}

    async def profile(self, name: str, coro):
        """Profile an async coroutine."""
        start = time.time()
        try:
            result = await coro
            return result
        finally:
            elapsed = time.time() - start
            self.timings[name] = elapsed

    def print_stats(self):
        """Print profiling results."""
        for name, elapsed in sorted(self.timings.items(),
                                    key=lambda x: x[1],
                                    reverse=True):
            print(f"{name}: {elapsed:.3f}s")

# Usage
profiler = AsyncProfiler()

result1 = await profiler.profile("build_context",
    qs.build_context("debugging"))
result2 = await profiler.profile("get_golden_rules",
    qs.get_golden_rules())

profiler.print_stats()
```

---

## Benchmarking

### Query Benchmarks

```python
import asyncio
import time

async def benchmark_query(name: str, query_func, iterations: int = 100):
    """Benchmark a query function."""
    times = []

    for _ in range(iterations):
        start = time.time()
        await query_func()
        elapsed = time.time() - start
        times.append(elapsed)

    avg = sum(times) / len(times)
    min_time = min(times)
    max_time = max(times)
    p95 = sorted(times)[int(len(times) * 0.95)]

    print(f"{name}:")
    print(f"  Avg: {avg*1000:.2f}ms")
    print(f"  Min: {min_time*1000:.2f}ms")
    print(f"  Max: {max_time*1000:.2f}ms")
    print(f"  P95: {p95*1000:.2f}ms")

# Run benchmarks
await benchmark_query(
    "get_golden_rules",
    lambda: qs.get_golden_rules()
)

await benchmark_query(
    "build_context",
    lambda: qs.build_context("debugging")
)
```

### Stress Testing

From `tests/test_stress.py`:

```python
def test_concurrent_access():
    """Benchmark concurrent access to blackboard."""
    import threading
    import time

    bb = BlackboardV2(tmp_path)
    operation_count = 0
    lock = threading.Lock()

    def worker():
        nonlocal operation_count
        for _ in range(100):
            bb.add_finding("agent", "test", "Finding")
            with lock:
                operation_count += 1

    # Start 10 threads
    start = time.time()
    threads = [threading.Thread(target=worker) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    elapsed = time.time() - start

    ops_per_sec = operation_count / elapsed
    print(f"Throughput: {ops_per_sec:.1f} ops/sec")
```

### Database Size Benchmarks

```python
import sqlite3
import os

def benchmark_database_size(db_path: str):
    """Analyze database size and composition."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Total database size
    file_size = os.path.getsize(db_path)
    print(f"Database size: {file_size / 1024 / 1024:.2f} MB")

    # Table sizes
    cursor.execute("""
        SELECT name,
               (SELECT COUNT(*) FROM sqlite_master sm2
                WHERE sm2.name = sm.name) as count
        FROM sqlite_master sm
        WHERE type = 'table'
    """)

    for table_name, _ in cursor.fetchall():
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        count = cursor.fetchone()[0]

        cursor.execute(f"""
            SELECT SUM(pgsize)
            FROM dbstat
            WHERE name = '{table_name}'
        """)
        size = cursor.fetchone()[0] or 0

        print(f"  {table_name}: {count} rows, "
              f"{size / 1024:.2f} KB")

    conn.close()
```

---

## Best Practices

### 1. Always Use Limits

```python
# ALWAYS
results = await query.limit(100)

# NEVER (unless you have a very good reason)
results = await query  # Unbounded!
```

### 2. Index Before Querying

```python
# Create indexes BEFORE running queries on new tables
await Learning.create_table()
await conn.execute("""
    CREATE INDEX idx_learning_domain
    ON learnings(domain)
""")

# NOW run queries
results = await Learning.select()\
    .where(Learning.domain == "debugging")
```

### 3. Monitor Query Performance in Production

```python
import logging

logger = logging.getLogger(__name__)

class QueryMonitor:
    async def execute_with_monitoring(self, query):
        start = time.time()
        result = await query
        elapsed = time.time() - start

        if elapsed > 0.5:
            logger.warning(f"Slow query: {elapsed:.3f}s")

        return result
```

### 4. Use Batch Operations

```python
# GOOD - Batch insert
learnings = [
    Learning(type='test', filepath=f'test{i}.md', title=f'Test {i}')
    for i in range(100)
]
await Learning.bulk_create(learnings, batch_size=50)

# BAD - Individual inserts
for i in range(100):
    await Learning.create(
        type='test',
        filepath=f'test{i}.md',
        title=f'Test {i}'
    )
```

### 5. Close Connections

```python
# Use context managers
async with manager:
    results = await Heuristic.select()
# Connection automatically closed

# Or explicit cleanup
try:
    results = await query
finally:
    await qs.cleanup()
```

### 6. Regular Maintenance

```python
# Weekly maintenance script
async def weekly_maintenance():
    conn = await aiosqlite.connect("memory/index.db")

    # Update statistics
    await conn.execute("ANALYZE")

    # Rebuild indexes
    await conn.execute("REINDEX")

    # Vacuum (compact database)
    await conn.execute("VACUUM")

    await conn.close()
```

### 7. Test Performance in CI

```yaml
# .github/workflows/performance.yml
- name: Performance Tests
  run: |
    pytest tests/test_stress.py
    pytest tests/test_performance_benchmarks.py

- name: Check Query Performance
  run: |
    python scripts/benchmark_queries.py
    # Fail if queries are too slow
```

---

## Performance Checklist

Before deploying changes:

- [ ] All queries have LIMIT clauses
- [ ] Queries use indexed columns in WHERE/ORDER BY
- [ ] No N+1 query patterns
- [ ] Connections are properly closed
- [ ] Token costs are within budget (<2000 tokens)
- [ ] Memory usage is acceptable (<50MB)
- [ ] Stress tests pass
- [ ] No slow queries (>500ms) in profiling
- [ ] Database is periodically VACUUMed
- [ ] Indexes are maintained (ANALYZE run)

---

## Resources

- **SQLite Performance**: https://www.sqlite.org/performance.html
- **SQLite Query Planner**: https://www.sqlite.org/queryplanner.html
- **Peewee ORM Optimization**: http://docs.peewee-orm.com/en/latest/peewee/database.html#optimizing-queries
- **Python Profiling**: https://docs.python.org/3/library/profile.html

---

**Next Steps:**

- Read [Testing Guide](testing.md) for test optimization strategies
- Check [Architecture Documentation](../DOCUMENTATION_ARCHITECTURE_ANALYSIS.md) for system design
- Review `tests/test_stress.py` for performance test patterns
- Run profiling tools on your queries to identify bottlenecks
