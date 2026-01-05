# API Reference

The Emergent Learning Framework provides a comprehensive async API for querying and managing institutional knowledge.

## Quick Start

```python
from query.core import QuerySystem

# Create instance (async)
qs = await QuerySystem.create()

# Build context for an agent
context = await qs.build_context(
    task="Fix authentication bug",
    domain="security",
    depth="standard"
)

# Query domain-specific knowledge
results = await qs.query_by_domain("debugging", limit=10)

# Get golden rules
rules = await qs.get_golden_rules()

# Clean up when done
await qs.cleanup()
```

## Architecture

The QuerySystem uses a mixin-based architecture:

- **QuerySystem** - Main orchestrator class
- **HeuristicQueryMixin** - Golden rules and heuristics
- **LearningQueryMixin** - Recent learnings and failure search
- **ExperimentQueryMixin** - Active experiments and CEO reviews
- **ViolationQueryMixin** - Golden rule violations
- **DecisionQueryMixin** - Architecture Decision Records (ADRs)
- **AssumptionQueryMixin** - Assumptions and validations
- **InvariantQueryMixin** - System invariants
- **SpikeQueryMixin** - Research spike reports
- **StatisticsQueryMixin** - Knowledge base statistics
- **ContextBuilderMixin** - Agent context generation

## Documentation

- [QuerySystem Reference](./QuerySystem.md) - Complete API for all query methods
- [Data Models Reference](./Models.md) - All database models and their fields

## Core Concepts

### Async-First Design

All methods are async (since v2.0.0):

```python
# Create instance
qs = await QuerySystem.create()

# All queries are async
results = await qs.query_by_domain("coordination")
rules = await qs.get_golden_rules()
```

### Location-Aware Queries

The QuerySystem supports location-aware filtering for project-specific knowledge:

```python
# Automatically detects .elf/ in current working directory
qs = await QuerySystem.create(current_location="/path/to/project")

# Queries will include both global and project-specific heuristics
results = await qs.query_by_domain("react")
```

### Tiered Context Building

Context is built in tiers for optimal token usage:

- **Tier 0** - Project context (if in .elf/ project)
- **Tier 1** - Golden rules (always included)
- **Tier 2** - Domain/tag-matched knowledge
- **Tier 3** - Recent context (if tokens remain)

Depth levels control verbosity:
- `minimal` - Golden rules only (~500 tokens)
- `standard` - + domain heuristics and learnings (default)
- `deep` - + experiments, ADRs, all recent learnings (~5k tokens)

### Error Handling

All methods raise typed exceptions:

```python
from query.exceptions import (
    ValidationError,    # QS001 - Invalid input
    DatabaseError,      # QS002 - Database failure
    TimeoutError,       # QS003 - Query timeout
    ConfigurationError, # QS004 - Config error
    QuerySystemError    # QS000 - Base exception
)

try:
    results = await qs.query_by_domain("invalid@domain")
except ValidationError as e:
    print(f"Validation failed: {e}")  # Includes error code
```

### Query Logging

All queries are automatically logged to the `building_queries` table for analytics:

```python
# Queries log:
# - Query type and parameters
# - Duration and status
# - Results count by type
# - Error messages (if any)
# - Session and agent IDs (if set)
```

### Validation Constants

Input validation limits are exposed:

```python
from query.validators import (
    MAX_DOMAIN_LENGTH,   # 100 chars
    MAX_QUERY_LENGTH,    # 10000 chars
    MAX_TAG_COUNT,       # 50 tags
    MAX_TAG_LENGTH,      # 50 chars per tag
    MIN_LIMIT,           # 1
    MAX_LIMIT,           # 1000
    DEFAULT_TIMEOUT,     # 30 seconds
    MAX_TOKENS           # 50000 tokens
)
```

## Examples

### Building Context for Claude

```python
qs = await QuerySystem.create()

# Build minimal context (golden rules only, ~500 tokens)
context = await qs.build_context(
    task="Quick code review",
    depth="minimal"
)

# Build standard context (default)
context = await qs.build_context(
    task="Implement user authentication",
    domain="security",
    tags=["oauth", "jwt"]
)

# Build deep context (all knowledge, ~5k tokens)
context = await qs.build_context(
    task="Design new microservice architecture",
    domain="architecture",
    depth="deep",
    max_tokens=10000
)
```

### Querying Heuristics

```python
# Get golden rules
rules = await qs.get_golden_rules()

# Get golden rules for specific categories
rules = await qs.get_golden_rules(categories=["core", "git"])

# Query by domain
results = await qs.query_by_domain("debugging", limit=20)
# Returns: {'domain': 'debugging', 'heuristics': [...], 'learnings': [...]}

# Query by tags
learnings = await qs.query_by_tags(["performance", "react"], limit=10)
```

### Finding Similar Failures

```python
# Find failures similar to current task
similar = await qs.find_similar_failures(
    task_description="React hook causing infinite re-renders",
    limit=5
)

for failure in similar:
    print(f"Relevance: {failure['relevance_score']:.0%}")
    print(f"Title: {failure['learning']['title']}")
    print(f"Matching words: {failure['matching_words']}")
```

### Querying Recent Activity

```python
# Get recent learnings
recent = await qs.query_recent(limit=10, days=7)

# Filter by type
failures = await qs.query_recent(type_filter="failure", days=2)
```

### Working with Decisions (ADRs)

```python
# Get accepted decisions
decisions = await qs.get_decisions(status="accepted", limit=10)

# Filter by domain
auth_decisions = await qs.get_decisions(
    domain="authentication",
    status="accepted"
)
```

### Tracking Violations

```python
# Get recent violations
violations = await qs.get_violations(days=7, acknowledged=False)

# Get violation summary
summary = await qs.get_violation_summary(days=30)
print(f"Total violations: {summary['total']}")
print(f"By rule: {summary['by_rule']}")
```

### Statistics and Health

```python
# Get knowledge base statistics
stats = await qs.get_statistics()
print(f"Total learnings: {stats['total_learnings']}")
print(f"By domain: {stats['learnings_by_domain']}")
print(f"Golden heuristics: {stats['golden_heuristics']}")

# Validate database integrity
validation = await qs.validate_database()
if not validation['valid']:
    print(f"Errors: {validation['errors']}")
```

## Version History

- **v2.0.0** (2025-01-01) - Full async/await refactor
- **v1.5.0** (2024-12-26) - Location-aware queries, project context
- **v1.0.0** (2024-12-01) - Initial release

## See Also

- [QuerySystem API Reference](./QuerySystem.md)
- [Data Models Reference](./Models.md)
- [Query Mixins Architecture](../ARCHITECTURE.md)
