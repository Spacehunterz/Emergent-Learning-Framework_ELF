# Query System Architecture with Context-Engine Features

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    Emergent Learning Framework                  │
│                         Query System v2.0                        │
└─────────────────────────────────────────────────────────────────┘

                              ┌─────────┐
                              │  Agent  │
                              │  Query  │
                              └────┬────┘
                                   │
                                   ▼
                    ┌──────────────────────────┐
                    │   build_context()        │
                    │   - task description     │
                    │   - domain (optional)    │
                    │   - tags (optional)      │
                    └──────────┬───────────────┘
                               │
           ┌───────────────────┼───────────────────┐
           │                   │                   │
           ▼                   ▼                   ▼
    ┌──────────┐      ┌──────────────┐    ┌──────────┐
    │ Failure  │      │   Domain     │    │   Tag    │
    │ Pattern  │      │   Query      │    │  Query   │
    │ Matching │      └──────┬───────┘    └────┬─────┘
    └────┬─────┘             │                 │
         │                   │                 │
         │              ┌────▼─────────────────▼────┐
         │              │  Relevance Scoring        │
         │              │  - Recency decay          │
         │              │  - Domain match           │
         │              │  - Validation count       │
         │              └───────────┬───────────────┘
         │                          │
         └──────────┬───────────────┘
                    │
                    ▼
         ┌──────────────────────┐
         │  Context Assembly    │
         │  - Tier 1: Golden    │
         │  - Tier 2: Relevant  │
         │  - Tier 3: Recent    │
         │  - Warnings: Similar │
         └──────────┬───────────┘
                    │
                    ▼
             ┌──────────────┐
             │   Output     │
             │   Context    │
             └──────────────┘
```

---

## Component Details

### 1. Relevance Scoring Engine

```python
┌─────────────────────────────────────────────────────────────┐
│  _calculate_relevance_score(learning, task, domain)        │
├─────────────────────────────────────────────────────────────┤
│  INPUT:                                                     │
│    - learning: {created_at, domain, times_validated}       │
│    - task: string description                              │
│    - domain: optional domain filter                        │
│                                                             │
│  ALGORITHM:                                                 │
│    base_score = 0.5                                         │
│                                                             │
│    # Recency decay (7-day half-life)                       │
│    age_days = now - learning.created_at                    │
│    recency_factor = 0.5 ^ (age_days / 7)                   │
│    score *= (0.5 + 0.5 * recency_factor)  # Min: 0.25     │
│                                                             │
│    # Domain match boost                                    │
│    if learning.domain == domain:                           │
│        score *= 1.5                                        │
│                                                             │
│    # Validation boost                                      │
│    if times_validated > 10: score *= 1.4                   │
│    elif times_validated > 5: score *= 1.2                  │
│                                                             │
│    return min(score, 1.0)                                  │
│                                                             │
│  OUTPUT: float [0.25 - 1.0]                                │
└─────────────────────────────────────────────────────────────┘
```

**Decay Curve:**
```
Relevance
   1.0 ┤●
       │ ●
       │  ●
   0.8 ┤   ●
       │    ●
       │     ●●
   0.6 ┤       ●●
       │         ●●
       │           ●●●
   0.4 ┤              ●●●●
       │                  ●●●●●
       │                      ●●●●●●
   0.2 ┤                           ●●●●●●●
       │
       └─┬───┬───┬───┬───┬───┬───┬───┬───┬─
         0   7  14  21  28  35  42  49  56
                      Days Old
```

---

### 2. Failure Pattern Matching Engine

```python
┌─────────────────────────────────────────────────────────────┐
│  find_similar_failures(task_description, threshold=0.3)     │
├─────────────────────────────────────────────────────────────┤
│  INPUT:                                                     │
│    - task_description: "debugging python import error"     │
│    - threshold: 0.3 (30% minimum similarity)               │
│                                                             │
│  ALGORITHM:                                                 │
│    # Extract keywords                                       │
│    task_words = extract_keywords(task_description)         │
│    # Words > 3 chars: {debugging, python, import, error}   │
│                                                             │
│    # Get recent failures (last 30 days, up to 50)         │
│    failures = query_recent(type='failure', limit=50)       │
│                                                             │
│    # Calculate Jaccard similarity                          │
│    for failure in failures:                                │
│        failure_words = extract_keywords(failure)           │
│        intersection = task_words ∩ failure_words           │
│        union = task_words ∪ failure_words                  │
│        similarity = |intersection| / |union|               │
│                                                             │
│        if similarity >= threshold:                         │
│            results.append({                                │
│                ...failure,                                 │
│                'similarity': similarity,                   │
│                'matched_keywords': intersection[:5]        │
│            })                                              │
│                                                             │
│    return sorted(results, key=similarity, reverse=True)    │
│                                                             │
│  OUTPUT: List[Dict] with similarity scores                 │
└─────────────────────────────────────────────────────────────┘
```

**Similarity Example:**
```
Task: "debugging python import error"
Keywords: {debugging, python, import, error}

Failure 1: "Python import error with missing modules"
Keywords: {python, import, error, with, missing, modules}

Intersection: {python, import, error} = 3 words
Union: {debugging, python, import, error, with, missing, modules} = 7 words
Similarity: 3/7 = 0.43 (43% match) ✓ Above threshold
```

---

### 3. Context Building Pipeline

```
┌────────────────────────────────────────────────────────────────┐
│                    build_context() Flow                        │
└────────────────────────────────────────────────────────────────┘

START
  │
  ├─► Validate inputs (task, domain, tags, max_tokens)
  │
  ├─► TIER 1: Load Golden Rules
  │   └─► Always included (~500 tokens)
  │
  ├─► EARLY WARNING: Find Similar Failures
  │   ├─► Extract keywords from task
  │   ├─► Search recent failures (30 days)
  │   ├─► Calculate similarity scores
  │   └─► If matches found: Add warning section
  │       └─► "⚠️ Similar Failures Detected"
  │           ├─► Top 3 most similar
  │           ├─► Similarity percentage
  │           ├─► Matched keywords
  │           └─► Lesson summaries
  │
  ├─► TIER 2: Relevant Knowledge
  │   │
  │   ├─► If domain specified:
  │   │   ├─► Query heuristics by domain
  │   │   │   ├─► Apply relevance scoring
  │   │   │   ├─► Sort by relevance (high → low)
  │   │   │   └─► Add to context
  │   │   │
  │   │   └─► Query learnings by domain
  │   │       ├─► Apply relevance scoring
  │   │       ├─► Sort by relevance (high → low)
  │   │       └─► Add to context
  │   │
  │   └─► If tags specified:
  │       ├─► Query learnings by tags
  │       ├─► Apply relevance scoring
  │       ├─► Sort by relevance (high → low)
  │       └─► Add to context
  │
  ├─► TIER 3: Recent Context (if tokens remain)
  │   ├─► Query recent learnings (last 2 days)
  │   └─► Add until token limit reached
  │
  ├─► METADATA: Active Experiments
  │   └─► List all active experiments
  │
  ├─► METADATA: Pending CEO Reviews
  │   └─► List all pending decisions
  │
  └─► ASSEMBLY: Format and return context
      └─► Building header + all sections
```

---

## Data Flow Diagram

```
                    ┌──────────────────┐
                    │  SQLite Database │
                    │   (index.db)     │
                    └────────┬─────────┘
                             │
         ┌───────────────────┼───────────────────┐
         │                   │                   │
         ▼                   ▼                   ▼
    ┌─────────┐      ┌──────────┐       ┌──────────┐
    │Learnings│      │Heuristics│       │Violations│
    │ Table   │      │  Table   │       │  Table   │
    └────┬────┘      └─────┬────┘       └─────┬────┘
         │                 │                   │
         │            ┌────▼────────────────┐  │
         │            │  Query Methods      │  │
         │            │  - by_domain()      │  │
         │            │  - by_tags()        │  │
         │            │  - recent()         │  │
         │            └────┬────────────────┘  │
         │                 │                   │
         └────────┬────────┘                   │
                  │                            │
                  ▼                            │
         ┌──────────────────┐                 │
         │  Raw Results     │                 │
         │  (unsorted)      │                 │
         └────────┬─────────┘                 │
                  │                            │
                  ▼                            │
         ┌──────────────────┐                 │
         │ Relevance Scorer │                 │
         │ + Sorter         │                 │
         └────────┬─────────┘                 │
                  │                            │
                  ▼                            │
         ┌──────────────────┐                 │
         │ Sorted Results   │◄────────────────┘
         │ (by relevance)   │  Pattern Matching
         └────────┬─────────┘
                  │
                  ▼
         ┌──────────────────┐
         │  Context String  │
         │  (formatted)     │
         └──────────────────┘
```

---

## Performance Characteristics

### Time Complexity

| Operation | Complexity | Typical Time |
|-----------|-----------|--------------|
| Relevance scoring | O(1) per item | 0.1ms |
| Keyword extraction | O(n) where n = text length | 1-5ms |
| Failure matching | O(m × k) where m = failures, k = keywords | 20-50ms |
| Sorting | O(n log n) where n = results | 1-2ms |
| **Total overhead** | - | **25-60ms** |

### Space Complexity

| Component | Memory |
|-----------|--------|
| Relevance scores | O(n) where n = results |
| Keyword sets | O(k) where k = unique keywords |
| Similar failures | O(5) = constant (top 5 only) |
| **Total** | **Linear in result count** |

### Token Impact

| Section | Tokens | When |
|---------|--------|------|
| Golden Rules | ~500 | Always |
| Similar Failures | 100-300 | When matches found |
| Tier 2 Content | 2000-4000 | Always |
| Tier 3 Content | 0-500 | If space remains |
| **Total** | **2600-5300** | Typical |

---

## Configuration Parameters

### Relevance Scoring
```python
RECENCY_HALF_LIFE = 7  # days
DOMAIN_BOOST = 1.5
HIGH_VALIDATION_THRESHOLD = 10
HIGH_VALIDATION_BOOST = 1.4
MEDIUM_VALIDATION_THRESHOLD = 5
MEDIUM_VALIDATION_BOOST = 1.2
MIN_RELEVANCE = 0.25  # Never decay below this
MAX_RELEVANCE = 1.0   # Cap at this
```

### Failure Matching
```python
SIMILARITY_THRESHOLD = 0.3  # 30% keyword overlap
MIN_KEYWORD_LENGTH = 4      # Characters
FAILURE_LOOKBACK_DAYS = 30
FAILURE_LIMIT = 50          # Max failures to check
RESULT_LIMIT = 5            # Top N to return
```

### Context Building
```python
DEFAULT_MAX_TOKENS = 5000
TIER_1_GOLDEN_RULES = True  # Always include
TIER_2_DOMAIN_LIMIT = 5
TIER_2_TAG_LIMIT = 5
TIER_3_RECENT_LIMIT = 3
SIMILAR_FAILURES_DISPLAY = 3  # Show top 3
```

---

## Extension Points

### Custom Relevance Scoring
```python
# Override _calculate_relevance_score() to use custom formula
class CustomQuerySystem(QuerySystem):
    def _calculate_relevance_score(self, learning, task, domain):
        # Your custom algorithm here
        return custom_score
```

### Custom Similarity Metrics
```python
# Override find_similar_failures() to use embeddings
class SemanticQuerySystem(QuerySystem):
    def find_similar_failures(self, task_description, threshold=0.3):
        # Use sentence embeddings + cosine similarity
        return semantic_matches
```

### Custom Context Assembly
```python
# Override build_context() to customize output
class CustomContextSystem(QuerySystem):
    def build_context(self, task, domain=None, tags=None, max_tokens=5000):
        # Your custom context structure
        return custom_context
```

---

## Monitoring and Observability

### Metrics Logged
- Query type and parameters
- Results returned count
- Token approximation
- Query duration (ms)
- Status (success/error/timeout)
- Component counts (heuristics, learnings, etc.)

### Debug Output
```bash
# Enable debug mode
python query.py --context --domain debugging --debug

# Output includes:
[DEBUG] QuerySystem initialized with base_path: ...
[DEBUG] Querying domain 'debugging' with limit 5
[DEBUG] Found 3 heuristics and 7 learnings
[DEBUG] Found 2 similar failures
[DEBUG] Built context with ~1250 tokens
```

---

## Security Considerations

### Input Validation
- Domain names: alphanumeric + hyphen/underscore/dot only
- Tags: alphanumeric + hyphen/underscore/dot only
- Query strings: max 10,000 characters
- Limits: 1-1000 results

### SQL Injection Prevention
- All queries use parameterized statements
- LIKE wildcards escaped with `escape_like()`
- No dynamic SQL construction

### Database Security
- File permissions: 0600 (owner read/write only)
- Windows ACLs: Current user only
- Connection pooling: Max 5 connections
- Timeout enforcement: 30s default

---

## Conclusion

This architecture provides:

1. **Intelligent Ranking:** Relevance-based sorting ensures most valuable knowledge surfaces first
2. **Proactive Warnings:** Similar failure detection prevents repeating mistakes
3. **Performance:** Minimal overhead (<60ms) with linear scaling
4. **Extensibility:** Clear extension points for custom algorithms
5. **Observability:** Comprehensive logging for monitoring and debugging

**Next Steps:**
- Phase 2: Add semantic similarity using embeddings
- Phase 3: Implement feedback-based learning rate adjustment
- Phase 4: Multi-agent knowledge sharing protocol
