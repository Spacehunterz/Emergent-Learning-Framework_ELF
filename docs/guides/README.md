# ELF Developer Guides

This directory contains comprehensive guides for working with the Emergent Learning Framework.

## Available Guides

### [Testing Guide](testing.md)
**963 lines** | **23KB**

Comprehensive guide to testing in ELF, covering:
- Test organization and structure
- Running tests with pytest
- Writing unit, integration, and stress tests
- Fixture patterns from conftest.py
- Mocking strategies for SQLite
- Coverage requirements and CI/CD integration
- Advanced patterns for testing concurrency and edge cases

**Key Topics:**
- Fixture patterns: `bb`, `results`, `test_dir`, `runner`
- Test categories: unit, integration, edge case, stress, destructive
- SQLite edge case testing patterns
- Claim chain atomicity testing
- Event log consistency testing
- Resource cleanup patterns

### [Performance Guide](performance.md)
**1074 lines** | **26KB**

Comprehensive guide to optimizing ELF performance, covering:
- Query optimization with LIMIT, OFFSET, and indexes
- Database indexing strategies
- Token cost optimization (context tiers)
- Memory usage tuning
- Dashboard performance tips
- Profiling tools and techniques
- Benchmarking strategies

**Key Topics:**
- Query optimization: LIMIT/OFFSET, compound indexes, avoiding N+1
- Index strategy: compound indexes, ordering, when NOT to index
- Token budget: tiered context (Tier 0-3), deduplication
- Memory profiling: tracemalloc, connection pooling, generators
- Dashboard caching and lazy loading
- Profiling tools: cProfile, line_profiler, memory_profiler
- Stress testing patterns

### [Extensions Guide](extensions.md)
**9.4KB**

Guide to extending ELF functionality.

## Quick Start

### Running Tests
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov=coordinator --cov-report=html

# Run specific category
pytest tests/test_stress.py
```

### Performance Profiling
```python
from query.core import QuerySystem

qs = await QuerySystem.create(debug=True)
result = await qs.build_context("debugging")

stats = await qs.get_statistics()
print(f"Avg query time: {stats['avg_query_time_ms']}ms")
```

### Performance Targets
- Query response: <100ms simple, <500ms complex
- Memory footprint: <50MB
- Token cost: <2000 tokens for full context
- Database size: <10MB typical

## Documentation Organization

```
docs/
├── guides/
│   ├── README.md (this file)
│   ├── testing.md        # Testing comprehensive guide
│   ├── performance.md    # Performance optimization guide
│   └── extensions.md     # Extension development guide
│
├── DOCUMENTATION_ARCHITECTURE_ANALYSIS.md  # System architecture
├── DEBUG_ANALYSIS_REPORT.md                # Debugging guide
└── CRITICAL_BUGS_QUICKREF.md              # Bug reference

```

## Related Documentation

- [Architecture Analysis](../DOCUMENTATION_ARCHITECTURE_ANALYSIS.md) - System design and components
- [Debug Analysis](../DEBUG_ANALYSIS_REPORT.md) - Debugging workflows
- Main [README.md](../../README.md) - Project overview

## Contributing

When adding new guides:

1. Follow the existing structure (Overview → Detailed sections → Best practices → Resources)
2. Include code examples from the actual codebase
3. Provide file paths to reference implementations
4. Add performance considerations where relevant
5. Update this README with the new guide

## File Locations Reference

### Test Files
- `tests/conftest.py` - Pytest fixtures
- `tests/test_*.py` - Test suites
- `tests/test_stress.py` - Concurrency stress tests
- `tests/test_sqlite_edge_cases.py` - Database edge cases

### Performance-Critical Code
- `src/query/core.py` - Query system core
- `src/query/context.py` - Context building (token optimization)
- `src/query/models.py` - Database models and indexes
- `coordinator/blackboard_v2.py` - Dual-write coordination

### Configuration
- `pyproject.toml` - Test and coverage configuration
- `.github/workflows/test.yml` - CI/CD (if exists)
- `tests/conftest.py` - Pytest configuration

---

**Last Updated:** 2026-01-05
