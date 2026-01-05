# QuerySystem API Reference

Complete reference for the `QuerySystem` class and all query methods.

## Table of Contents

- [Initialization](#initialization)
- [Context Building](#context-building)
- [Heuristic Queries](#heuristic-queries)
- [Learning Queries](#learning-queries)
- [Experiment Queries](#experiment-queries)
- [Decision Queries](#decision-queries)
- [Violation Queries](#violation-queries)
- [Invariant Queries](#invariant-queries)
- [Assumption Queries](#assumption-queries)
- [Spike Report Queries](#spike-report-queries)
- [Statistics Queries](#statistics-queries)
- [Database Operations](#database-operations)
- [Validation Methods](#validation-methods)

---

## Initialization

### QuerySystem.create()

Async factory method to create a QuerySystem instance.

**Since:** v2.0.0

```python
@classmethod
async def create(
    cls,
    base_path: Optional[str] = None,
    debug: bool = False,
    session_id: Optional[str] = None,
    agent_id: Optional[str] = None,
    current_location: Optional[str] = None
) -> QuerySystem
```

**Parameters:**

- `base_path` (Optional[str]): Base path to emergent-learning directory. Defaults to ELF base path resolution.
- `debug` (bool): Enable debug logging to stderr. Default: False.
- `session_id` (Optional[str]): Session ID for query logging. Falls back to `CLAUDE_SESSION_ID` env var.
- `agent_id` (Optional[str]): Agent ID for query logging. Falls back to `CLAUDE_AGENT_ID` env var.
- `current_location` (Optional[str]): Override working directory for project detection. Default: `os.getcwd()`.

**Returns:** Configured `QuerySystem` instance

**Raises:**
- `ConfigurationError` (QS004): If setup fails or directories cannot be created

**Example:**

```python
from query.core import QuerySystem

# Basic initialization
qs = await QuerySystem.create()

# With debug logging
qs = await QuerySystem.create(debug=True)

# With session tracking
qs = await QuerySystem.create(
    session_id="session_123",
    agent_id="claude-opus-4.5"
)

# Location-aware (for project-specific heuristics)
qs = await QuerySystem.create(
    current_location="/path/to/my-project"
)
```

### cleanup()

Clean up resources when done with the QuerySystem.

**Since:** v2.0.0

```python
async def cleanup(self) -> None
```

**Example:**

```python
qs = await QuerySystem.create()
try:
    # Use query system
    results = await qs.query_by_domain("debugging")
finally:
    await qs.cleanup()
```

---

## Context Building

### build_context()

Build a tiered context string for agent consumption with intelligent token budgeting.

**Since:** v1.0.0 (async since v2.0.0)

```python
async def build_context(
    self,
    task: str,
    domain: Optional[str] = None,
    tags: Optional[List[str]] = None,
    max_tokens: int = 5000,
    timeout: int = None,
    depth: str = 'standard'
) -> str
```

**Parameters:**

- `task` (str): Description of the task for context matching. Max 10,000 chars.
- `domain` (Optional[str]): Domain to focus on (e.g., "debugging", "security"). Max 100 chars.
- `tags` (Optional[List[str]]): Tags to match against learnings. Max 50 tags, 50 chars each.
- `max_tokens` (int): Maximum tokens to use (~4 chars/token). Default: 5000, Max: 50000.
- `timeout` (Optional[int]): Query timeout in seconds. Default: 60 (2x normal timeout).
- `depth` (str): Context depth level. One of: `"minimal"`, `"standard"`, `"deep"`. Default: `"standard"`.

**Depth Levels:**

- `minimal` - Golden rules only (~500 tokens). For quick tasks.
- `standard` - + domain heuristics and learnings (default).
- `deep` - + experiments, ADRs, all recent learnings (~5k tokens). For complex planning.

**Returns:** Formatted context string with tiered sections

**Raises:**
- `ValidationError` (QS001): Invalid task, domain, tags, or depth
- `TimeoutError` (QS003): Query exceeded timeout
- `DatabaseError` (QS002): Database operation failed

**Context Structure:**

```markdown
Building Status (depth)
Location: /current/path

# Task Context
[task description]

---

# TIER 0: Project Context (if in .elf/ project)
**Project:** my-project
**Domains:** react, typescript
[project description from context.md]

# TIER 1: Golden Rules
[golden rules content]

# TIER 2: Relevant Knowledge
## Domain: [domain]
### Heuristics:
- **[rule]** (confidence: 0.85, validated: 12x)
  [explanation]

### Recent Learnings:
- **[title]** (failure)
  [summary]

## Decisions (ADRs)
- **[title]** (domain: security)
  Decision: [text]

## Active Invariants
- **[statement]** (severity: error)

# TIER 3: Recent Context
[recent learnings if tokens remain]

# Active Experiments
- **[name]** (5 cycles)
  Hypothesis: [text]
```

**Example:**

```python
# Minimal context (golden rules only)
context = await qs.build_context(
    task="Quick code review",
    depth="minimal"
)

# Standard context with domain
context = await qs.build_context(
    task="Implement OAuth2 authentication flow",
    domain="security",
    tags=["oauth", "jwt"],
    max_tokens=5000
)

# Deep context for planning
context = await qs.build_context(
    task="Design microservice architecture for payment system",
    domain="architecture",
    depth="deep",
    max_tokens=10000
)
```

**See Also:**
- [get_golden_rules()](#get_golden_rules)
- [query_by_domain()](#query_by_domain)
- [find_similar_failures()](#find_similar_failures)

---

## Heuristic Queries

### get_golden_rules()

Read and return golden rules from memory/golden-rules.md.

**Since:** v1.0.0 (async since v2.0.0)

```python
async def get_golden_rules(
    self,
    categories: Optional[List[str]] = None
) -> str
```

**Parameters:**

- `categories` (Optional[List[str]]): Categories to filter by (e.g., `["core", "git"]`). If None, returns all rules.

**Returns:** Content of golden rules file (filtered by category if specified), or default message if file doesn't exist

**Example:**

```python
# Get all golden rules
all_rules = await qs.get_golden_rules()

# Get only core and git rules
core_rules = await qs.get_golden_rules(categories=["core", "git"])
```

### query_by_domain()

Get heuristics and learnings for a specific domain.

**Since:** v1.0.0 (async since v2.0.0)

```python
async def query_by_domain(
    self,
    domain: str,
    limit: int = 10,
    timeout: int = None
) -> Dict[str, Any]
```

**Parameters:**

- `domain` (str): Domain to query (e.g., "coordination", "debugging"). Max 100 chars.
- `limit` (int): Maximum results per category. Min: 1, Max: 1000, Default: 10.
- `timeout` (Optional[int]): Query timeout in seconds. Default: 30.

**Returns:** Dictionary with structure:

```python
{
    'domain': str,
    'heuristics': List[Dict],  # Ordered by confidence desc, times_validated desc
    'learnings': List[Dict],   # Ordered by created_at desc
    'count': {
        'heuristics': int,
        'learnings': int
    }
}
```

**Location-Aware Behavior:**

If `current_location` was set during initialization and a `.elf/` directory exists, returns both:
- Global heuristics (project_path IS NULL)
- Location-specific heuristics (project_path = current_location)

**Raises:**
- `ValidationError` (QS001): Invalid domain or limit
- `TimeoutError` (QS003): Query exceeded timeout
- `DatabaseError` (QS002): Database operation failed

**Example:**

```python
# Get debugging knowledge
results = await qs.query_by_domain("debugging", limit=20)

print(f"Domain: {results['domain']}")
print(f"Found {results['count']['heuristics']} heuristics")

for h in results['heuristics']:
    print(f"- {h['rule']} (confidence: {h['confidence']:.2f})")

for l in results['learnings']:
    print(f"- {l['title']} ({l['type']})")
```

### query_by_tags()

Get learnings matching specified tags.

**Since:** v1.0.0 (async since v2.0.0)

```python
async def query_by_tags(
    self,
    tags: List[str],
    limit: int = 10,
    timeout: int = None
) -> List[Dict[str, Any]]
```

**Parameters:**

- `tags` (List[str]): Tags to search for (OR logic). Max 50 tags, 50 chars each.
- `limit` (int): Maximum results to return. Min: 1, Max: 1000, Default: 10.
- `timeout` (Optional[int]): Query timeout in seconds. Default: 30.

**Returns:** List of learning dictionaries matching any of the tags, ordered by created_at desc

**Raises:**
- `ValidationError` (QS001): Invalid tags or limit
- `TimeoutError` (QS003): Query exceeded timeout
- `DatabaseError` (QS002): Database operation failed

**Example:**

```python
# Find learnings tagged with performance or optimization
results = await qs.query_by_tags(
    tags=["performance", "optimization", "caching"],
    limit=15
)

for learning in results:
    print(f"{learning['title']} ({learning['type']})")
    print(f"  Tags: {learning['tags']}")
    print(f"  Summary: {learning['summary']}")
```

---

## Learning Queries

### query_recent()

Get recent learnings, optionally filtered by type.

**Since:** v1.0.0 (async since v2.0.0)

```python
async def query_recent(
    self,
    type_filter: Optional[str] = None,
    limit: int = 10,
    timeout: int = None,
    days: int = 2
) -> List[Dict[str, Any]]
```

**Parameters:**

- `type_filter` (Optional[str]): Type filter. One of: `"failure"`, `"success"`, `"heuristic"`, `"experiment"`, `"observation"`. None = all types.
- `limit` (int): Maximum results to return. Min: 1, Max: 1000, Default: 10.
- `timeout` (Optional[int]): Query timeout in seconds. Default: 30.
- `days` (int): Only return learnings from last N days. Default: 2.

**Returns:** List of learning dictionaries ordered by created_at desc

**Raises:**
- `ValidationError` (QS001): Invalid type_filter or limit
- `TimeoutError` (QS003): Query exceeded timeout
- `DatabaseError` (QS002): Database operation failed

**Example:**

```python
# Get all recent learnings (last 2 days)
recent = await qs.query_recent(limit=20)

# Get only recent failures
failures = await qs.query_recent(
    type_filter="failure",
    days=7,
    limit=10
)

# Get recent successes from last week
successes = await qs.query_recent(
    type_filter="success",
    days=7
)
```

### find_similar_failures()

Find failures similar to a task description using keyword matching.

**Since:** v1.0.0 (async since v2.0.0)

```python
async def find_similar_failures(
    self,
    task_description: str,
    limit: int = 5,
    timeout: int = None
) -> List[Dict[str, Any]]
```

**Parameters:**

- `task_description` (str): Description of current task. Max 10,000 chars.
- `limit` (int): Maximum similar failures to return. Default: 5.
- `timeout` (Optional[int]): Query timeout in seconds. Default: 30.

**Returns:** List of dictionaries with structure:

```python
[
    {
        'learning': Dict,           # Full learning record
        'relevance_score': float,   # 0.0 to 1.0
        'matching_words': int       # Number of overlapping keywords
    }
]
```

Results are ordered by relevance_score desc.

**Algorithm:**
1. Fetches recent 100 failures
2. Tokenizes task_description and each failure's title/summary
3. Computes word overlap (set intersection)
4. Scores by: overlap / max(task_words, 1)
5. Returns top N matches

**Example:**

```python
similar = await qs.find_similar_failures(
    task_description="React hooks causing infinite re-render loop",
    limit=5
)

for failure in similar:
    score = failure['relevance_score']
    words = failure['matching_words']
    learning = failure['learning']

    print(f"[{score*100:.0f}% match] {learning['title']}")
    print(f"  Matching keywords: {words}")
    print(f"  Summary: {learning['summary']}")
```

---

## Experiment Queries

### get_active_experiments()

List all active experiments.

**Since:** v1.0.0 (async since v2.0.0)

```python
async def get_active_experiments(
    self,
    timeout: int = None
) -> List[Dict[str, Any]]
```

**Parameters:**

- `timeout` (Optional[int]): Query timeout in seconds. Default: 30.

**Returns:** List of experiment dictionaries ordered by created_at desc

**Raises:**
- `TimeoutError` (QS003): Query exceeded timeout
- `DatabaseError` (QS002): Database operation failed

**Example:**

```python
experiments = await qs.get_active_experiments()

for exp in experiments:
    print(f"{exp['name']} ({exp['cycles_run']} cycles)")
    print(f"  Hypothesis: {exp['hypothesis']}")
    print(f"  Folder: {exp['folder_path']}")
```

### get_pending_ceo_reviews()

List all pending CEO reviews (escalations).

**Since:** v1.0.0 (async since v2.0.0)

```python
async def get_pending_ceo_reviews(
    self,
    timeout: int = None
) -> List[Dict[str, Any]]
```

**Parameters:**

- `timeout` (Optional[int]): Query timeout in seconds. Default: 30.

**Returns:** List of CEO review dictionaries ordered by created_at desc

**Raises:**
- `TimeoutError` (QS003): Query exceeded timeout
- `DatabaseError` (QS002): Database operation failed

**Example:**

```python
reviews = await qs.get_pending_ceo_reviews()

for review in reviews:
    print(f"[PENDING] {review['title']}")
    print(f"  Context: {review['context']}")
    print(f"  Recommendation: {review['recommendation']}")
    print(f"  Created: {review['created_at']}")
```

---

## Decision Queries

### get_decisions()

Get architecture decision records (ADRs), optionally filtered by domain.

**Since:** v1.5.0 (async since v2.0.0)

```python
async def get_decisions(
    self,
    domain: Optional[str] = None,
    status: str = 'accepted',
    limit: int = 10,
    timeout: int = None
) -> List[Dict[str, Any]]
```

**Parameters:**

- `domain` (Optional[str]): Domain filter. Max 100 chars. None = all domains.
- `status` (str): Status filter. Default: `"accepted"`. Options: `"accepted"`, `"proposed"`, `"deprecated"`, `"superseded"`.
- `limit` (int): Maximum results. Min: 1, Max: 1000, Default: 10.
- `timeout` (Optional[int]): Query timeout in seconds. Default: 30.

**Returns:** List of decision dictionaries ordered by created_at desc

**Raises:**
- `ValidationError` (QS001): Invalid domain or limit
- `TimeoutError` (QS003): Query exceeded timeout
- `DatabaseError` (QS002): Database operation failed

**Example:**

```python
# Get all accepted decisions
decisions = await qs.get_decisions(status="accepted")

# Get security-related decisions
security_decisions = await qs.get_decisions(
    domain="security",
    status="accepted",
    limit=20
)

for dec in security_decisions:
    print(f"{dec['title']}")
    print(f"  Decision: {dec['decision']}")
    print(f"  Rationale: {dec['rationale']}")
    print(f"  Files: {dec['files_touched']}")
```

---

## Violation Queries

### get_violations()

Get Golden Rule violations from specified time period.

**Since:** v1.0.0 (async since v2.0.0)

```python
async def get_violations(
    self,
    days: int = 7,
    acknowledged: Optional[bool] = None,
    timeout: int = None
) -> List[Dict[str, Any]]
```

**Parameters:**

- `days` (int): Number of days to look back. Default: 7.
- `acknowledged` (Optional[bool]): Filter by acknowledged status. None = all violations.
- `timeout` (Optional[int]): Query timeout in seconds. Default: 30.

**Returns:** List of violation dictionaries ordered by violation_date desc

**Raises:**
- `TimeoutError` (QS003): Query exceeded timeout
- `DatabaseError` (QS002): Database operation failed

**Example:**

```python
# Get all violations in last 7 days
violations = await qs.get_violations(days=7)

# Get unacknowledged violations in last 30 days
unacked = await qs.get_violations(
    days=30,
    acknowledged=False
)

for v in unacked:
    print(f"[{v['violation_date']}] Rule {v['rule_id']}: {v['rule_name']}")
    print(f"  {v['description']}")
```

### get_violation_summary()

Get summary statistics of Golden Rule violations.

**Since:** v1.0.0 (async since v2.0.0)

```python
async def get_violation_summary(
    self,
    days: int = 7,
    timeout: int = None
) -> Dict[str, Any]
```

**Parameters:**

- `days` (int): Number of days to look back. Default: 7.
- `timeout` (Optional[int]): Query timeout in seconds. Default: 30.

**Returns:** Dictionary with structure:

```python
{
    'total': int,                # Total violations
    'acknowledged': int,         # Acknowledged count
    'unacknowledged': int,       # Unacknowledged count
    'by_rule': [                # Violations grouped by rule
        {
            'rule_id': int,
            'rule_name': str,
            'count': int
        }
    ],
    'recent': [                 # Last 5 violations
        {
            'rule_id': int,
            'rule_name': str,
            'description': str,
            'date': str
        }
    ],
    'days': int                 # Period queried
}
```

**Example:**

```python
summary = await qs.get_violation_summary(days=30)

print(f"Violations in last {summary['days']} days:")
print(f"  Total: {summary['total']}")
print(f"  Acknowledged: {summary['acknowledged']}")
print(f"  Unacknowledged: {summary['unacknowledged']}")

print("\nBy rule:")
for rule in summary['by_rule']:
    print(f"  {rule['rule_name']}: {rule['count']}x")
```

---

## Invariant Queries

### get_invariants()

Get invariants (statements about what must ALWAYS be true).

**Since:** v1.5.0 (async since v2.0.0)

```python
async def get_invariants(
    self,
    domain: Optional[str] = None,
    status: str = 'active',
    scope: Optional[str] = None,
    severity: Optional[str] = None,
    limit: int = 10,
    timeout: int = None
) -> List[Dict[str, Any]]
```

**Parameters:**

- `domain` (Optional[str]): Domain filter. Max 100 chars.
- `status` (str): Status filter. Default: `"active"`. Options: `"active"`, `"deprecated"`, `"violated"`.
- `scope` (Optional[str]): Scope filter. Options: `"codebase"`, `"module"`, `"function"`, `"runtime"`.
- `severity` (Optional[str]): Severity filter. Options: `"error"`, `"warning"`, `"info"`.
- `limit` (int): Maximum results. Min: 1, Max: 1000, Default: 10.
- `timeout` (Optional[int]): Query timeout in seconds. Default: 30.

**Returns:** List of invariant dictionaries ordered by created_at desc

**Raises:**
- `ValidationError` (QS001): Invalid domain or limit
- `TimeoutError` (QS003): Query exceeded timeout
- `DatabaseError` (QS002): Database operation failed

**Example:**

```python
# Get all active invariants
invariants = await qs.get_invariants(status="active")

# Get violated invariants (warnings)
violated = await qs.get_invariants(status="violated")

# Get error-level codebase invariants
critical = await qs.get_invariants(
    scope="codebase",
    severity="error",
    limit=20
)

for inv in critical:
    print(f"[{inv['severity']}] {inv['statement']}")
    print(f"  Scope: {inv['scope']}")
    print(f"  Rationale: {inv['rationale']}")
    if inv.get('validation_type'):
        print(f"  Validation: {inv['validation_type']}")
```

---

## Assumption Queries

### get_assumptions()

Get assumptions with validation tracking.

**Since:** v1.5.0 (async since v2.0.0)

```python
async def get_assumptions(
    self,
    domain: Optional[str] = None,
    status: str = 'active',
    min_confidence: float = 0.0,
    limit: int = 10,
    timeout: int = None
) -> List[Dict[str, Any]]
```

**Parameters:**

- `domain` (Optional[str]): Domain filter. Max 100 chars.
- `status` (str): Status filter. Default: `"active"`. Options: `"active"`, `"verified"`, `"challenged"`, `"invalidated"`.
- `min_confidence` (float): Minimum confidence threshold (0.0 to 1.0). Default: 0.0.
- `limit` (int): Maximum results. Min: 1, Max: 1000, Default: 10.
- `timeout` (Optional[int]): Query timeout in seconds. Default: 30.

**Returns:** List of assumption dictionaries ordered by confidence desc, created_at desc

**Raises:**
- `ValidationError` (QS001): Invalid domain or limit
- `TimeoutError` (QS003): Query exceeded timeout
- `DatabaseError` (QS002): Database operation failed

**Example:**

```python
# Get high-confidence active assumptions
assumptions = await qs.get_assumptions(
    status="active",
    min_confidence=0.7
)

# Get verified assumptions in security domain
verified = await qs.get_assumptions(
    domain="security",
    status="verified"
)

for a in assumptions:
    print(f"{a['assumption']} (confidence: {a['confidence']:.0%})")
    print(f"  Context: {a['context']}")
    print(f"  Verified: {a['verified_count']}x")
    if a['challenged_count']:
        print(f"  Challenged: {a['challenged_count']}x")
```

### get_challenged_assumptions()

Get challenged or invalidated assumptions as warnings.

**Since:** v1.5.0 (async since v2.0.0)

```python
async def get_challenged_assumptions(
    self,
    domain: Optional[str] = None,
    limit: int = 10,
    timeout: int = None
) -> List[Dict[str, Any]]
```

**Parameters:**

- `domain` (Optional[str]): Domain filter. Max 100 chars.
- `limit` (int): Maximum results. Min: 1, Max: 1000, Default: 10.
- `timeout` (Optional[int]): Query timeout in seconds. Default: 30.

**Returns:** List of challenged/invalidated assumption dictionaries ordered by challenged_count desc, created_at desc

**Example:**

```python
# Get assumptions that were proven wrong
challenged = await qs.get_challenged_assumptions()

for a in challenged:
    status = "INVALIDATED" if a['status'] == 'invalidated' else "CHALLENGED"
    print(f"[{status}] {a['assumption']}")
    print(f"  Challenged {a['challenged_count']}x, verified {a['verified_count']}x")
    print(f"  Confidence: {a['confidence']:.0%}")
```

---

## Spike Report Queries

### get_spike_reports()

Get spike reports (research/investigation knowledge).

**Since:** v1.5.0 (async since v2.0.0)

```python
async def get_spike_reports(
    self,
    domain: Optional[str] = None,
    tags: Optional[List[str]] = None,
    search: Optional[str] = None,
    limit: int = 10,
    timeout: int = None
) -> List[Dict[str, Any]]
```

**Parameters:**

- `domain` (Optional[str]): Domain filter. Max 100 chars.
- `tags` (Optional[List[str]]): Tags to match (OR logic). Max 50 tags, 50 chars each.
- `search` (Optional[str]): Search term for title/topic/findings.
- `limit` (int): Maximum results. Min: 1, Max: 1000, Default: 10.
- `timeout` (Optional[int]): Query timeout in seconds. Default: 30.

**Returns:** List of spike report dictionaries ordered by usefulness_score desc, created_at desc

**Raises:**
- `ValidationError` (QS001): Invalid domain, tags, or limit
- `TimeoutError` (QS003): Query exceeded timeout
- `DatabaseError` (QS002): Database operation failed

**Example:**

```python
# Get all spike reports
spikes = await qs.get_spike_reports(limit=20)

# Search for GraphQL-related research
graphql_spikes = await qs.get_spike_reports(
    search="GraphQL",
    limit=5
)

# Get performance-related spikes
perf_spikes = await qs.get_spike_reports(
    domain="performance",
    tags=["optimization", "caching"]
)

for spike in perf_spikes:
    print(f"{spike['title']} ({spike['time_invested_minutes']} min)")
    print(f"  Topic: {spike['topic']}")
    print(f"  Findings: {spike['findings']}")
    if spike['gotchas']:
        print(f"  Gotchas: {spike['gotchas']}")
    print(f"  Usefulness: {spike['usefulness_score']:.1f}/5")
```

---

## Statistics Queries

### get_statistics()

Get comprehensive statistics about the knowledge base.

**Since:** v1.0.0 (async since v2.0.0)

```python
async def get_statistics(
    self,
    timeout: int = None
) -> Dict[str, Any]
```

**Parameters:**

- `timeout` (Optional[int]): Query timeout in seconds. Default: 30.

**Returns:** Dictionary with structure:

```python
{
    # Learning statistics
    'total_learnings': int,
    'learnings_by_type': Dict[str, int],      # {'failure': 10, 'success': 5, ...}
    'learnings_by_domain': Dict[str, int],    # {'debugging': 8, 'security': 4, ...}

    # Heuristic statistics
    'total_heuristics': int,
    'heuristics_by_domain': Dict[str, int],
    'golden_heuristics': int,

    # Experiment statistics
    'total_experiments': int,
    'experiments_by_status': Dict[str, int],  # {'active': 2, 'completed': 5, ...}

    # CEO review statistics
    'total_ceo_reviews': int,
    'ceo_reviews_by_status': Dict[str, int],  # {'pending': 1, 'approved': 3, ...}

    # Violation statistics (last 7 days)
    'violations_7d': int,
    'violations_by_rule_7d': Dict[str, int]   # {'Rule 1: ...': 3, ...}
}
```

**Raises:**
- `TimeoutError` (QS003): Query exceeded timeout
- `DatabaseError` (QS002): Database operation failed

**Example:**

```python
stats = await qs.get_statistics()

print(f"Knowledge Base Statistics:")
print(f"  Total learnings: {stats['total_learnings']}")
print(f"  Total heuristics: {stats['total_heuristics']}")
print(f"  Golden heuristics: {stats['golden_heuristics']}")

print(f"\nLearnings by type:")
for type_name, count in stats['learnings_by_type'].items():
    print(f"  {type_name}: {count}")

print(f"\nDomain distribution:")
for domain, count in stats['learnings_by_domain'].items():
    print(f"  {domain}: {count}")

print(f"\nViolations (last 7 days): {stats['violations_7d']}")
```

---

## Database Operations

### validate_database()

Validate database integrity and check table structure.

**Since:** v1.0.0 (async since v2.0.0)

```python
async def validate_database(self) -> Dict[str, Any]
```

**Returns:** Dictionary with structure:

```python
{
    'valid': bool,
    'errors': List[str],
    'warnings': List[str],
    'checks': {
        'integrity': str,              # 'ok' or error message
        'tables': List[str],           # List of existing tables
        'learnings_count': int,
        'heuristics_count': int,
        'experiments_count': int,
        'ceo_reviews_count': int
    }
}
```

**Example:**

```python
validation = await qs.validate_database()

if validation['valid']:
    print("Database is healthy")
    print(f"Tables: {', '.join(validation['checks']['tables'])}")
    print(f"Learnings: {validation['checks']['learnings_count']}")
else:
    print("Database has errors:")
    for error in validation['errors']:
        print(f"  - {error}")
```

---

## Validation Methods

These methods validate inputs according to framework constraints. They're called automatically by query methods but can be used directly for pre-validation.

### _validate_domain()

```python
def _validate_domain(self, domain: str) -> str
```

**Validates:**
- Not empty
- Max 100 chars
- Only alphanumeric, hyphen, underscore, dot

**Raises:** `ValidationError` (QS001)

### _validate_limit()

```python
def _validate_limit(self, limit: int) -> int
```

**Validates:**
- Is integer
- Min: 1
- Max: 1000

**Raises:** `ValidationError` (QS001)

### _validate_tags()

```python
def _validate_tags(self, tags: List[str]) -> List[str]
```

**Validates:**
- Is list
- Max 50 tags
- Each tag max 50 chars
- Only alphanumeric (Unicode), hyphen, underscore, dot

**Raises:** `ValidationError` (QS001)

### _validate_query()

```python
def _validate_query(self, query: str) -> str
```

**Validates:**
- Not empty
- Max 10,000 chars

**Raises:** `ValidationError` (QS001)

---

## Constants

Validation constants are exposed as class attributes:

```python
QuerySystem.MAX_DOMAIN_LENGTH    # 100
QuerySystem.MAX_QUERY_LENGTH     # 10000
QuerySystem.MAX_TAG_COUNT        # 50
QuerySystem.MAX_TAG_LENGTH       # 50
QuerySystem.MIN_LIMIT            # 1
QuerySystem.MAX_LIMIT            # 1000
QuerySystem.DEFAULT_TIMEOUT      # 30 seconds
QuerySystem.MAX_TOKENS           # 50000
```

**Example:**

```python
from query.core import QuerySystem

print(f"Max domain length: {QuerySystem.MAX_DOMAIN_LENGTH}")
print(f"Default timeout: {QuerySystem.DEFAULT_TIMEOUT}s")
```

---

## Error Codes

All exceptions include error codes for programmatic handling:

- **QS000** - Base/unknown error (`QuerySystemError`)
- **QS001** - Input validation failure (`ValidationError`)
- **QS002** - Database operation failure (`DatabaseError`)
- **QS003** - Query timeout (`TimeoutError`)
- **QS004** - Configuration error (`ConfigurationError`)

**Example:**

```python
from query.exceptions import ValidationError, TimeoutError

try:
    results = await qs.query_by_domain("invalid@domain!")
except ValidationError as e:
    print(f"Validation failed [{e.error_code}]: {e}")
except TimeoutError as e:
    print(f"Query timed out [{e.error_code}]: {e}")
```

---

## See Also

- [Data Models Reference](./Models.md)
- [API Overview](./index.md)
- [Query Mixins Architecture](../ARCHITECTURE.md)
