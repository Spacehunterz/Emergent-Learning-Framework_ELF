# Domain Elasticity Design - Phase 2 Heuristic Lifecycle

**Agent:** Agent 2 (Ultrathink Swarm)
**Date:** 2025-12-12
**Status:** Design Specification
**Phase:** 2 - Domain Elasticity

---

## Executive Summary

Phase 1 implemented a hard limit of 10 active heuristics per domain. This prevents unbounded growth but causes knowledge loss when high-quality heuristics arrive at a saturated domain. Phase 2 introduces **domain elasticity**: a two-tier limit system with intelligent expansion/contraction logic that preserves valuable knowledge while preventing bloat.

**Key Innovation:** Domains operate at a soft limit (5) under normal conditions but can expand to a hard limit (10) when exceptional heuristics arrive, then gradually contract back through intelligent merge/eviction strategies.

---

## 1. Problem Statement

### 1.1 Why Hard Limit 5 is Problematic

The current Phase 1 system has a single hard limit of 10 active heuristics per domain. If we reduce this to 5 (as originally envisioned), several problems emerge:

**Scenario 1: Domain Evolution Stagnation**
- Domain has 5 good heuristics (confidence 0.6-0.7)
- New exceptional heuristic arrives (confidence 0.8, highly validated)
- System must evict an existing heuristic to make room
- **Result:** Potential knowledge loss, no room for growth

**Scenario 2: Burst Learning Events**
- Multiple related failures occur in quick succession
- Each generates a valuable heuristic
- First 5 are captured, subsequent ones evicted
- **Result:** Incomplete pattern capture, fragmented knowledge

**Scenario 3: Domain Expertise Growth**
- As domain matures, nuanced sub-patterns emerge
- These refinements are valuable but can't coexist with existing rules
- **Result:** Domain stuck at surface-level knowledge, can't deepen

### 1.2 Real Knowledge Loss Examples

**Example 1: Git Pre-commit Hooks Domain**
```
Existing heuristics (5):
1. Always test hooks before committing (conf: 0.75)
2. Use shellcheck on bash scripts (conf: 0.70)
3. Set executable permissions (conf: 0.68)
4. Handle Windows/Unix path differences (conf: 0.65)
5. Test with sample files first (conf: 0.60)

New heuristic arrives:
6. Hooks must handle gitignored files gracefully (conf: 0.80, 5 validations)
   ⚠️ EVICTED under hard limit 5, despite being highest quality
```

**Example 2: WebSocket Domain**
```
Existing heuristics (5):
1. One handler per event type (conf: 0.85)
2. Reconnect with exponential backoff (conf: 0.80)
3. Clean up on unmount (conf: 0.78)
4. Use refs for callbacks (conf: 0.72)
5. Ping/pong for keepalive (conf: 0.68)

New heuristics from production debugging:
6. Rate-limit reconnection attempts (conf: 0.75, 3 validations)
7. Buffer messages during reconnect (conf: 0.73, 4 validations)
   ⚠️ Both evicted, critical production patterns lost
```

### 1.3 Why Unlimited is Also Bad

Removing limits entirely creates different problems:

**Problem 1: Knowledge Dilution**
- 50 heuristics in domain → None are actionable
- Cognitive overload when querying domain
- Signal-to-noise ratio collapses

**Problem 2: Duplicate/Overlapping Rules**
- Similar patterns expressed differently proliferate
- No pressure to merge/consolidate
- Database bloat

**Problem 3: Stale Knowledge Accumulation**
- Old, low-confidence heuristics linger indefinitely
- No forcing function for cleanup
- Historical cruft dominates

**Problem 4: Eviction Algorithm Never Runs**
- No trigger for dormancy/archival decisions
- Revival mechanisms unused
- Lifecycle management atrophies

---

## 2. Elasticity Model

### 2.1 Two-Tier Capacity System

```
┌─────────────────────────────────────────────────┐
│ DOMAIN CAPACITY STATES                          │
├─────────────────────────────────────────────────┤
│                                                 │
│ NORMAL STATE (0-5 active)                      │
│ ├─ Soft Limit: 5                               │
│ ├─ Operating mode: Steady state                │
│ ├─ Eviction: Standard scoring                  │
│ └─ Expansion: Allowed if quality threshold met │
│                                                 │
│ OVERFLOW STATE (6-10 active)                   │
│ ├─ Hard Limit: 10                              │
│ ├─ Operating mode: Emergency capacity          │
│ ├─ Eviction: Aggressive (2x pressure)          │
│ └─ Contraction: Active (gradual return to 5)   │
│                                                 │
│ CRITICAL STATE (10+ active)                    │
│ ├─ Reject new heuristics                       │
│ ├─ Force immediate eviction                    │
│ └─ Alert: Domain needs review                  │
│                                                 │
└─────────────────────────────────────────────────┘
```

### 2.2 State Transitions

**Normal → Overflow (Expansion)**
```
Trigger: New heuristic quality > expansion_threshold
Conditions:
  - Confidence >= 0.70
  - Validations >= 3
  - Novelty score >= 0.60 (not duplicate)
  - Domain health = stable
Action: Accept heuristic, increment count to 6-10
```

**Overflow → Normal (Contraction)**
```
Trigger: Maintenance cycle (daily)
Conditions:
  - Domain in overflow for > grace_period (7 days)
  - Merge candidates identified OR
  - Low-value heuristics present
Action: Gradual reduction (1-2 per week) back to 5
```

**Normal → Critical (Failure Mode)**
```
Trigger: Count exceeds hard limit
Conditions: Bug, race condition, or forced insertions
Action: Immediate eviction of lowest N heuristics
        Log alert for manual review
```

### 2.3 Transition Triggers

| From State | To State | Trigger | Threshold |
|------------|----------|---------|-----------|
| Normal | Overflow | Quality heuristic | conf >= 0.70, val >= 3 |
| Overflow | Normal | Time-based | 7+ days in overflow |
| Overflow | Normal | Merge success | 2+ heuristics merged |
| Any | Critical | Limit exceeded | count > hard_limit |
| Critical | Overflow | Forced eviction | Evict until count = hard_limit |

---

## 3. Expansion Criteria

### 3.1 Quality Threshold Model

A new heuristic is "worthy" of exceeding the soft limit if it meets **all** criteria:

**Criterion 1: Confidence Threshold**
```sql
confidence >= expansion_min_confidence (default: 0.70)
```

**Criterion 2: Validation Count**
```sql
times_validated >= expansion_min_validations (default: 3)
```

**Criterion 3: Novelty Score**
```
novelty_score = semantic_distance(new_heuristic, existing_heuristics)
novelty_score >= expansion_min_novelty (default: 0.60)

Where semantic distance is measured by:
- Keyword overlap (Jaccard similarity)
- Embedding cosine distance (if available)
- Domain expert rules (e.g., different failure modes)
```

**Criterion 4: Domain Health Check**
```sql
-- Domain must not be in crisis
SELECT
  (active_count / soft_limit) <= max_density_ratio  -- Not too crowded
  AND avg_confidence >= min_avg_confidence          -- Overall quality OK
  AND deprecated_count / total_count <= max_deprecated_ratio  -- Not too many failures
FROM domain_metadata
WHERE domain = ?

Defaults:
- max_density_ratio = 2.0 (allow 2x soft limit)
- min_avg_confidence = 0.40
- max_deprecated_ratio = 0.30
```

### 3.2 Novelty Detection Algorithm

**Step 1: Extract Keywords**
```python
def extract_keywords(heuristic_text):
    # Use existing _extract_keywords from lifecycle_manager.py
    return keywords

new_keywords = extract_keywords(new_heuristic.rule)
```

**Step 2: Compare with Existing Heuristics**
```python
def calculate_novelty(new_heuristic, existing_heuristics):
    new_kw = set(extract_keywords(new_heuristic.rule))

    max_overlap = 0.0
    for existing in existing_heuristics:
        existing_kw = set(extract_keywords(existing.rule))
        jaccard = len(new_kw & existing_kw) / len(new_kw | existing_kw)
        max_overlap = max(max_overlap, jaccard)

    # Novelty = 1 - max_overlap (high overlap = low novelty)
    return 1.0 - max_overlap
```

**Step 3: Threshold Decision**
```python
if novelty >= 0.60:
    # >60% different from all existing = novel enough
    return "NOVEL"
elif 0.40 <= novelty < 0.60:
    # Moderate overlap = potential refinement
    return "REFINEMENT"  # Consider merge instead
else:
    # >60% overlap = duplicate
    return "DUPLICATE"  # Reject or merge
```

### 3.3 Domain Health Metrics

**Health Score Calculation**
```sql
CREATE VIEW domain_health_score AS
SELECT
    domain,

    -- Component 1: Average quality (0-1)
    AVG(confidence) as avg_confidence,

    -- Component 2: Utilization ratio (active/soft_limit)
    CAST(active_count AS REAL) / soft_limit as utilization,

    -- Component 3: Deprecation rate (lower is better)
    1.0 - (CAST(deprecated_count AS REAL) / NULLIF(total_count, 0)) as deprecation_health,

    -- Component 4: Activity recency (days since last use)
    CASE
        WHEN days_since_activity <= 7 THEN 1.0
        WHEN days_since_activity <= 30 THEN 0.8
        WHEN days_since_activity <= 90 THEN 0.5
        ELSE 0.2
    END as recency_health,

    -- Overall health score (weighted average)
    (
        AVG(confidence) * 0.35 +
        (1.0 - LEAST(CAST(active_count AS REAL) / soft_limit, 1.5) / 1.5) * 0.25 +
        (1.0 - (CAST(deprecated_count AS REAL) / NULLIF(total_count, 0))) * 0.20 +
        CASE
            WHEN days_since_activity <= 7 THEN 1.0
            WHEN days_since_activity <= 30 THEN 0.8
            ELSE 0.5
        END * 0.20
    ) as health_score
FROM domain_metadata
GROUP BY domain;
```

**Health-Based Expansion Rules**
```
IF health_score >= 0.70:  ALLOW expansion (healthy domain)
ELIF 0.50 <= health_score < 0.70:  ALLOW if exceptional quality (conf >= 0.80)
ELIF health_score < 0.50:  DENY expansion (domain in crisis)
```

---

## 4. Contraction Algorithm

### 4.1 Gradual Reduction Strategy

Domains in overflow should not immediately snap back to soft limit. Instead, use a **gradual contraction** strategy:

**Contraction Schedule**
```
Day 0:  Domain enters overflow (6-10 active)
Day 7:  Grace period ends, contraction begins
Day 14: Target: reduce by 1-2 heuristics
Day 21: Target: reduce by 1-2 heuristics
Day 28: Target: back to soft limit (5)
```

**Contraction Rate**
```python
def calculate_contraction_target(current_count, days_in_overflow, soft_limit):
    """
    Calculate how many heuristics to remove this cycle.

    Returns: (target_count, urgent)
    """
    grace_period = 7  # days
    max_overflow_duration = 28  # days

    if days_in_overflow < grace_period:
        return current_count, False  # No action during grace period

    # Linear contraction: reduce by (overflow - 0) over (max_duration - grace_period) days
    overflow_amount = current_count - soft_limit
    days_for_contraction = max_overflow_duration - grace_period
    weekly_reduction = math.ceil(overflow_amount / (days_for_contraction / 7))

    target_count = current_count - weekly_reduction
    urgent = days_in_overflow > max_overflow_duration  # Force if deadline passed

    return max(target_count, soft_limit), urgent
```

### 4.2 Merge Candidates Detection

Before evicting, try to merge similar heuristics:

**Merge Eligibility Criteria**
```sql
-- Find pairs of heuristics that could be merged
SELECT
    h1.id as heuristic_1,
    h2.id as heuristic_2,
    h1.rule as rule_1,
    h2.rule as rule_2,
    (h1.confidence + h2.confidence) / 2 as merged_confidence,
    -- Similarity score (use keyword overlap as proxy)
    -- In real implementation, use semantic similarity
    (LENGTH(h1.rule) + LENGTH(h2.rule) - LENGTH(h1.rule || h2.rule)) /
    (LENGTH(h1.rule) + LENGTH(h2.rule)) as similarity
FROM heuristics h1
JOIN heuristics h2 ON h1.domain = h2.domain AND h1.id < h2.id
WHERE h1.status = 'active'
  AND h2.status = 'active'
  AND h1.domain = ?
  -- Similarity threshold
  AND similarity >= 0.40  -- 40%+ similar
ORDER BY similarity DESC
LIMIT 5;
```

**Merge Decision Tree**
```
IF similarity >= 0.60:
    → AUTO-MERGE (very similar)
    → Combine validations/violations
    → Take weighted average confidence
    → Merge explanations

ELIF 0.40 <= similarity < 0.60:
    → FLAG for MANUAL review
    → Present to user/CEO
    → Keep both until decision

ELSE:
    → Too different, no merge
    → Proceed to eviction
```

**Merged Heuristic Properties**
```python
def merge_heuristics(h1, h2):
    """Merge two similar heuristics into one."""
    return Heuristic(
        rule=f"{h1.rule} + {h2.rule}",  # Concatenate or LLM-summarize
        confidence=(h1.confidence * h1.times_validated + h2.confidence * h2.times_validated) /
                   (h1.times_validated + h2.times_validated),  # Weighted average
        times_validated=h1.times_validated + h2.times_validated,
        times_violated=h1.times_violated + h2.times_violated,
        times_contradicted=h1.times_contradicted + h2.times_contradicted,
        explanation=f"Merged from: {h1.id}, {h2.id}",
        status='active',
        created_at=min(h1.created_at, h2.created_at),  # Preserve earliest
        merge_parent_ids=[h1.id, h2.id]  # Track lineage
    )
```

### 4.3 Dormancy vs. Eviction Decision Tree

When contraction is needed and merges are not possible:

```
┌─────────────────────────────────────────┐
│ Heuristic Evaluation for Contraction   │
└─────────────────────────────────────────┘
            │
            ▼
    ┌───────────────┐
    │ Is Golden?    │───YES──→ PROTECTED (skip)
    └───────────────┘
            │ NO
            ▼
    ┌───────────────┐
    │ Confidence    │───>0.65──→ KEEP (high value)
    │     Score     │
    └───────────────┘
            │ ≤0.65
            ▼
    ┌───────────────┐
    │ Times         │───≥10──→ Consider DORMANT
    │  Validated    │         (proven track record)
    └───────────────┘
            │ <10
            ▼
    ┌───────────────┐
    │ Days Since    │───>90──→ ARCHIVE (not used)
    │   Last Use    │
    └───────────────┘
            │ ≤90
            ▼
    ┌───────────────┐
    │ Eviction      │───<0.15──→ EVICT (lowest score)
    │    Score      │
    └───────────────┘
            │ ≥0.15
            ▼
        DORMANT (default: preserve with revival chance)
```

**Pseudo-SQL Implementation**
```sql
-- Classify heuristics for contraction
SELECT
    id,
    rule,
    confidence,
    times_validated,
    days_since_use,
    eviction_score,
    CASE
        WHEN is_golden = 1 THEN 'PROTECTED'
        WHEN confidence > 0.65 THEN 'KEEP'
        WHEN times_validated >= 10 AND confidence >= 0.45 THEN 'DORMANT'
        WHEN days_since_use > 90 THEN 'ARCHIVE'
        WHEN eviction_score < 0.15 THEN 'EVICT'
        ELSE 'DORMANT'
    END as action
FROM eviction_candidates
WHERE domain = ?
  AND status = 'active'
ORDER BY eviction_score ASC;
```

### 4.4 Grace Period Management

Domains in overflow get a grace period before contraction:

```python
@dataclass
class OverflowState:
    """Track domain overflow state."""
    domain: str
    entered_overflow_at: datetime
    current_count: int
    soft_limit: int
    hard_limit: int
    grace_period_days: int = 7
    max_overflow_days: int = 28

    @property
    def days_in_overflow(self) -> int:
        return (datetime.now() - self.entered_overflow_at).days

    @property
    def is_in_grace_period(self) -> bool:
        return self.days_in_overflow < self.grace_period_days

    @property
    def is_urgent(self) -> bool:
        return self.days_in_overflow > self.max_overflow_days

    @property
    def contraction_pressure(self) -> float:
        """
        Pressure to contract: 0.0 (no pressure) to 1.0 (maximum pressure).

        - During grace period: 0.0
        - After grace period: linear increase to 1.0 over max_overflow_days
        """
        if self.is_in_grace_period:
            return 0.0

        days_past_grace = self.days_in_overflow - self.grace_period_days
        max_pressure_days = self.max_overflow_days - self.grace_period_days

        return min(1.0, days_past_grace / max_pressure_days)
```

---

## 5. Schema Changes

### 5.1 New Table: domain_metadata

Stores per-domain elasticity configuration and state.

```sql
-- ==============================================================
-- Domain Metadata Table
-- ==============================================================

CREATE TABLE IF NOT EXISTS domain_metadata (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    -- Domain identifier
    domain TEXT NOT NULL UNIQUE,

    -- Capacity Configuration
    soft_limit INTEGER NOT NULL DEFAULT 5,
    hard_limit INTEGER NOT NULL DEFAULT 10,

    -- Current State
    active_count INTEGER NOT NULL DEFAULT 0,
    dormant_count INTEGER NOT NULL DEFAULT 0,
    archived_count INTEGER NOT NULL DEFAULT 0,
    deprecated_count INTEGER NOT NULL DEFAULT 0,

    -- Overflow Tracking
    is_in_overflow INTEGER DEFAULT 0,  -- Boolean: 0 or 1
    entered_overflow_at DATETIME,
    days_in_overflow INTEGER DEFAULT 0,

    -- Expansion Configuration
    expansion_min_confidence REAL DEFAULT 0.70,
    expansion_min_validations INTEGER DEFAULT 3,
    expansion_min_novelty REAL DEFAULT 0.60,

    -- Contraction Configuration
    grace_period_days INTEGER DEFAULT 7,
    max_overflow_days INTEGER DEFAULT 28,
    contraction_rate INTEGER DEFAULT 2,  -- Heuristics to remove per week

    -- Health Metrics (cached)
    avg_confidence REAL,
    health_score REAL,
    last_health_check DATETIME,

    -- Timestamps
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,

    -- Constraints
    CHECK(soft_limit > 0),
    CHECK(hard_limit >= soft_limit),
    CHECK(soft_limit <= hard_limit),
    CHECK(is_in_overflow IN (0, 1)),
    CHECK(expansion_min_confidence >= 0.0 AND expansion_min_confidence <= 1.0),
    CHECK(expansion_min_novelty >= 0.0 AND expansion_min_novelty <= 1.0)
);

CREATE INDEX idx_domain_metadata_domain ON domain_metadata(domain);
CREATE INDEX idx_domain_metadata_overflow ON domain_metadata(is_in_overflow);

-- ==============================================================
-- Heuristic Merges Table (Track merge history)
-- ==============================================================

CREATE TABLE IF NOT EXISTS heuristic_merges (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    -- Merged result
    merged_heuristic_id INTEGER NOT NULL,

    -- Original heuristics (JSON array of IDs)
    parent_heuristic_ids TEXT NOT NULL,  -- JSON: [id1, id2, ...]

    -- Merge metadata
    merge_reason TEXT,  -- 'overflow_contraction', 'manual', 'similarity_detected'
    merge_strategy TEXT,  -- 'weighted_average', 'llm_summary', 'manual'
    similarity_score REAL,

    -- Outcome
    space_saved INTEGER DEFAULT 1,  -- How many heuristics reduced

    -- Timestamps
    merged_at DATETIME DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (merged_heuristic_id) REFERENCES heuristics(id) ON DELETE CASCADE
);

CREATE INDEX idx_merges_result ON heuristic_merges(merged_heuristic_id);
CREATE INDEX idx_merges_merged_at ON heuristic_merges(merged_at DESC);

-- ==============================================================
-- Expansion Events Table (Audit log)
-- ==============================================================

CREATE TABLE IF NOT EXISTS expansion_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    domain TEXT NOT NULL,
    heuristic_id INTEGER NOT NULL,

    -- Event type
    event_type TEXT NOT NULL CHECK(event_type IN ('expansion', 'contraction', 'merge')),

    -- Counts at time of event
    count_before INTEGER NOT NULL,
    count_after INTEGER NOT NULL,

    -- Decision factors
    quality_score REAL,
    novelty_score REAL,
    health_score REAL,

    -- Justification
    reason TEXT,

    -- Timestamp
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (heuristic_id) REFERENCES heuristics(id) ON DELETE CASCADE
);

CREATE INDEX idx_expansion_domain ON expansion_events(domain);
CREATE INDEX idx_expansion_type ON expansion_events(event_type);
CREATE INDEX idx_expansion_created ON expansion_events(created_at DESC);
```

### 5.2 Trigger: Auto-update domain_metadata

Keep domain_metadata counts synchronized with heuristics table:

```sql
-- ==============================================================
-- Triggers: Synchronize domain_metadata with heuristics
-- ==============================================================

-- Update counts when heuristic status changes
CREATE TRIGGER IF NOT EXISTS sync_domain_counts_on_update
AFTER UPDATE OF status ON heuristics
FOR EACH ROW
BEGIN
    -- Decrement old status count
    UPDATE domain_metadata
    SET
        active_count = active_count - CASE WHEN OLD.status = 'active' THEN 1 ELSE 0 END,
        dormant_count = dormant_count - CASE WHEN OLD.status = 'dormant' THEN 1 ELSE 0 END,
        archived_count = archived_count - CASE WHEN OLD.status = 'archived' THEN 1 ELSE 0 END,
        deprecated_count = deprecated_count - CASE WHEN OLD.status = 'deprecated' THEN 1 ELSE 0 END,

        -- Increment new status count
        active_count = active_count + CASE WHEN NEW.status = 'active' THEN 1 ELSE 0 END,
        dormant_count = dormant_count + CASE WHEN NEW.status = 'dormant' THEN 1 ELSE 0 END,
        archived_count = archived_count + CASE WHEN NEW.status = 'archived' THEN 1 ELSE 0 END,
        deprecated_count = deprecated_count + CASE WHEN NEW.status = 'deprecated' THEN 1 ELSE 0 END,

        -- Check overflow state
        is_in_overflow = CASE WHEN (active_count + CASE WHEN NEW.status = 'active' THEN 1 ELSE 0 END) > soft_limit THEN 1 ELSE 0 END,
        entered_overflow_at = CASE
            WHEN (active_count + CASE WHEN NEW.status = 'active' THEN 1 ELSE 0 END) > soft_limit
                 AND is_in_overflow = 0
            THEN CURRENT_TIMESTAMP
            ELSE entered_overflow_at
        END,

        updated_at = CURRENT_TIMESTAMP
    WHERE domain = NEW.domain;

    -- Insert if doesn't exist
    INSERT OR IGNORE INTO domain_metadata (domain, active_count, dormant_count, archived_count, deprecated_count)
    VALUES (NEW.domain, 0, 0, 0, 0);
END;

-- Update counts when new heuristic is inserted
CREATE TRIGGER IF NOT EXISTS sync_domain_counts_on_insert
AFTER INSERT ON heuristics
FOR EACH ROW
BEGIN
    -- Insert domain_metadata if doesn't exist
    INSERT OR IGNORE INTO domain_metadata (domain, active_count, dormant_count, archived_count, deprecated_count)
    VALUES (NEW.domain, 0, 0, 0, 0);

    -- Increment count
    UPDATE domain_metadata
    SET
        active_count = active_count + CASE WHEN NEW.status = 'active' THEN 1 ELSE 0 END,
        dormant_count = dormant_count + CASE WHEN NEW.status = 'dormant' THEN 1 ELSE 0 END,
        archived_count = archived_count + CASE WHEN NEW.status = 'archived' THEN 1 ELSE 0 END,
        deprecated_count = deprecated_count + CASE WHEN NEW.status = 'deprecated' THEN 1 ELSE 0 END,

        -- Check overflow state
        is_in_overflow = CASE WHEN active_count > soft_limit THEN 1 ELSE 0 END,
        entered_overflow_at = CASE
            WHEN active_count > soft_limit AND is_in_overflow = 0
            THEN CURRENT_TIMESTAMP
            ELSE entered_overflow_at
        END,

        updated_at = CURRENT_TIMESTAMP
    WHERE domain = NEW.domain;
END;
```

### 5.3 View: Overflow Pressure Dashboard

```sql
-- ==============================================================
-- View: Overflow Pressure Dashboard
-- ==============================================================

CREATE VIEW IF NOT EXISTS overflow_pressure_dashboard AS
SELECT
    dm.domain,
    dm.active_count,
    dm.soft_limit,
    dm.hard_limit,
    dm.is_in_overflow,
    dm.days_in_overflow,
    dm.grace_period_days,
    dm.max_overflow_days,

    -- Pressure calculation
    CASE
        WHEN dm.is_in_overflow = 0 THEN 0.0
        WHEN dm.days_in_overflow < dm.grace_period_days THEN 0.0
        ELSE MIN(1.0, CAST(dm.days_in_overflow - dm.grace_period_days AS REAL) /
                      (dm.max_overflow_days - dm.grace_period_days))
    END as contraction_pressure,

    -- Utilization percentage
    ROUND(CAST(dm.active_count AS REAL) / dm.soft_limit * 100, 1) as utilization_pct,

    -- Health score
    dm.health_score,
    dm.avg_confidence,

    -- Status
    CASE
        WHEN dm.active_count > dm.hard_limit THEN 'CRITICAL'
        WHEN dm.is_in_overflow = 1 AND dm.days_in_overflow > dm.max_overflow_days THEN 'URGENT'
        WHEN dm.is_in_overflow = 1 AND dm.days_in_overflow >= dm.grace_period_days THEN 'CONTRACTION_NEEDED'
        WHEN dm.is_in_overflow = 1 THEN 'GRACE_PERIOD'
        WHEN dm.active_count >= dm.soft_limit * 0.8 THEN 'NEAR_LIMIT'
        ELSE 'HEALTHY'
    END as status,

    -- Action needed
    CASE
        WHEN dm.active_count > dm.hard_limit THEN 'FORCE_EVICT'
        WHEN dm.is_in_overflow = 1 AND dm.days_in_overflow > dm.max_overflow_days THEN 'URGENT_CONTRACT'
        WHEN dm.is_in_overflow = 1 AND dm.days_in_overflow >= dm.grace_period_days THEN 'GRADUAL_CONTRACT'
        ELSE 'NONE'
    END as action_needed,

    -- Timestamps
    dm.entered_overflow_at,
    dm.updated_at

FROM domain_metadata dm
ORDER BY
    CASE status
        WHEN 'CRITICAL' THEN 1
        WHEN 'URGENT' THEN 2
        WHEN 'CONTRACTION_NEEDED' THEN 3
        WHEN 'GRACE_PERIOD' THEN 4
        WHEN 'NEAR_LIMIT' THEN 5
        ELSE 6
    END,
    dm.active_count DESC;
```

---

## 6. Overflow Pressure Metrics

### 6.1 Pressure Measurement Formula

```python
def calculate_overflow_pressure(domain_state: DomainMetadata) -> float:
    """
    Calculate overflow pressure for a domain.

    Returns: 0.0 (no pressure) to 1.0 (maximum pressure)
    """
    # Not in overflow = no pressure
    if not domain_state.is_in_overflow:
        return 0.0

    # During grace period = no pressure
    if domain_state.days_in_overflow < domain_state.grace_period_days:
        return 0.0

    # After grace period: linear increase
    days_past_grace = domain_state.days_in_overflow - domain_state.grace_period_days
    max_pressure_days = domain_state.max_overflow_days - domain_state.grace_period_days

    base_pressure = min(1.0, days_past_grace / max_pressure_days)

    # Amplify pressure if near hard limit
    utilization = domain_state.active_count / domain_state.hard_limit
    if utilization > 0.9:
        # Add extra pressure if >90% of hard limit
        utilization_factor = (utilization - 0.9) / 0.1  # 0.0 to 1.0
        base_pressure = min(1.0, base_pressure * (1.0 + utilization_factor))

    return base_pressure
```

### 6.2 Dashboard Query

```sql
-- Query to display overflow pressure for all domains
SELECT
    domain,
    active_count,
    soft_limit,
    hard_limit,
    status,
    contraction_pressure,
    utilization_pct,
    action_needed,
    days_in_overflow,
    health_score
FROM overflow_pressure_dashboard
WHERE status != 'HEALTHY'
ORDER BY
    CASE status
        WHEN 'CRITICAL' THEN 1
        WHEN 'URGENT' THEN 2
        WHEN 'CONTRACTION_NEEDED' THEN 3
        WHEN 'GRACE_PERIOD' THEN 4
        WHEN 'NEAR_LIMIT' THEN 5
        ELSE 6
    END;
```

### 6.3 Alert Thresholds

| Metric | Threshold | Alert Level | Action |
|--------|-----------|-------------|--------|
| Contraction Pressure | >= 0.80 | WARNING | Review domain, consider merge |
| Contraction Pressure | >= 1.0 | ERROR | Force contraction now |
| Active Count | > Hard Limit | CRITICAL | Immediate eviction |
| Utilization % | >= 90% of Soft | INFO | Monitor for overflow |
| Health Score | < 0.40 | WARNING | Domain in crisis, block expansion |
| Days in Overflow | > Max Overflow Days | ERROR | Contraction overdue |

### 6.4 Monitoring Queries

**Query 1: Domains Under Pressure**
```sql
SELECT
    domain,
    active_count,
    soft_limit,
    contraction_pressure,
    days_in_overflow,
    action_needed
FROM overflow_pressure_dashboard
WHERE contraction_pressure >= 0.5
ORDER BY contraction_pressure DESC;
```

**Query 2: Expansion Event History**
```sql
SELECT
    domain,
    event_type,
    count_before,
    count_after,
    quality_score,
    novelty_score,
    reason,
    created_at
FROM expansion_events
WHERE domain = ?
ORDER BY created_at DESC
LIMIT 20;
```

**Query 3: Merge Opportunities**
```sql
-- Find domains that could benefit from merging
SELECT
    domain,
    COUNT(*) as potential_merges
FROM (
    SELECT
        h1.domain,
        h1.id as id1,
        h2.id as id2
    FROM heuristics h1
    JOIN heuristics h2 ON h1.domain = h2.domain AND h1.id < h2.id
    WHERE h1.status = 'active' AND h2.status = 'active'
      AND h1.domain IN (SELECT domain FROM overflow_pressure_dashboard WHERE is_in_overflow = 1)
      -- Placeholder for similarity; in reality use semantic comparison
      AND h1.rule LIKE '%' || h2.rule || '%'
)
GROUP BY domain
ORDER BY potential_merges DESC;
```

---

## 7. Edge Cases & Failure Modes

### 7.1 Domain Permanently at Hard Limit

**Scenario:** Domain has 10 high-quality heuristics, all essential, no merges possible.

**Indicators:**
- Active count = hard limit for > max_overflow_days
- All heuristics have confidence >= 0.70
- All validations >= 10
- No merge candidates (novelty scores all > 0.80)
- Health score >= 0.70

**Response Strategy:**

1. **Auto-Response (System):**
   ```
   - Log WARNING: "Domain {domain} at hard limit with no eviction candidates"
   - Set status = 'REVIEW_NEEDED'
   - Block new heuristics (reject with message)
   - Create CEO inbox item
   ```

2. **CEO Decision Options:**
   ```
   Option A: Increase hard limit for this domain
             → domain_metadata.hard_limit = 15 (exceptional case)

   Option B: Force merge of most similar pair
             → Manual review + LLM-assisted merge

   Option C: Split domain into sub-domains
             → e.g., "websocket" → "websocket-connection", "websocket-messaging"

   Option D: Accept soft rejection
             → Keep at 10, new heuristics go to dormant immediately
   ```

3. **Mitigation:**
   ```python
   def handle_saturated_domain(domain, new_heuristic):
       """Handle domain at hard limit with no room."""
       # Check if new heuristic is EXCEPTIONAL (conf >= 0.85, val >= 5)
       if new_heuristic.confidence >= 0.85 and new_heuristic.times_validated >= 5:
           # Emergency: Make lowest heuristic dormant even if good
           candidates = get_eviction_candidates(domain)
           make_dormant(candidates[0].id, reason="Emergency: exceptional new heuristic")
           accept_new_heuristic(new_heuristic)
           log_emergency_eviction(domain, candidates[0], new_heuristic)
       else:
           # Reject new heuristic
           reject_heuristic(new_heuristic, reason="Domain at capacity, not exceptional")
   ```

### 7.2 Rapid Churn (Lots of New Heuristics)

**Scenario:** 20 new heuristics arrive in one day for the same domain.

**Indicators:**
- Expansion events > 10 in 24 hours
- Multiple heuristics accepted into overflow
- Domain going from 5 → 10 → 5 → 10 rapidly

**Response Strategy:**

1. **Detection:**
   ```sql
   SELECT domain, COUNT(*) as expansion_count
   FROM expansion_events
   WHERE event_type = 'expansion'
     AND created_at > datetime('now', '-1 day')
   GROUP BY domain
   HAVING COUNT(*) > 10;
   ```

2. **Rate Limiting:**
   ```python
   def check_expansion_rate_limit(domain):
       """Prevent more than 5 expansions per day."""
       conn = get_connection()
       cursor = conn.execute("""
           SELECT COUNT(*) as count
           FROM expansion_events
           WHERE domain = ?
             AND event_type = 'expansion'
             AND created_at > datetime('now', '-1 day')
       """, (domain,))

       count = cursor.fetchone()['count']

       if count >= 5:
           return False, "Expansion rate limit: max 5 per day"

       return True, "OK"
   ```

3. **Batch Processing:**
   ```python
   def batch_process_pending_heuristics(domain):
       """Process multiple pending heuristics together."""
       pending = get_pending_heuristics(domain)

       # Detect duplicates via clustering
       clusters = cluster_by_similarity(pending)

       # Accept one representative per cluster
       for cluster in clusters:
           best = max(cluster, key=lambda h: h.confidence)
           accept_heuristic(best)

           # Mark others as duplicates
           for h in cluster:
               if h != best:
                   mark_duplicate(h, merged_into=best.id)
   ```

### 7.3 Conflicting Golden Rules in Overflow

**Scenario:** Domain has 2 golden rules that contradict each other in overflow state.

**Example:**
```
Golden Rule 1: "Always preserve high-confidence heuristics"
Golden Rule 2: "Never exceed hard limit"

Conflict: Domain has 10 heuristics, all with confidence > 0.80 (golden-worthy),
          and an 11th exceptional heuristic arrives.
```

**Response Strategy:**

1. **Priority Hierarchy:**
   ```
   Priority 1: Hard limit (security boundary)
   Priority 2: Golden rule protection
   Priority 3: Confidence preservation
   ```

2. **Resolution:**
   ```python
   def resolve_golden_conflict(domain, new_heuristic):
       """Handle conflict between golden rules."""
       # Check if new heuristic is golden-eligible
       if new_heuristic.confidence >= 0.90 and new_heuristic.times_validated >= 10:
           # Escalate to CEO: both old and new are golden-worthy
           create_ceo_decision(
               title=f"Golden Rule Conflict in {domain}",
               context="New golden-worthy heuristic, but domain at hard limit with all golden",
               options=[
                   "Increase hard limit for this domain",
                   "Force merge of most similar golden heuristics",
                   "Reject new heuristic (preserve existing golden set)"
               ]
           )
           # Block until CEO decision
           return "PENDING_CEO_DECISION"
       else:
           # New heuristic not golden-worthy: reject
           return "REJECTED"
   ```

### 7.4 Database Corruption / Race Conditions

**Scenario:** Trigger fails, domain_metadata.active_count != actual count.

**Detection:**
```sql
-- Daily integrity check
SELECT
    h.domain,
    COUNT(*) as actual_count,
    dm.active_count as recorded_count,
    COUNT(*) - dm.active_count as discrepancy
FROM heuristics h
LEFT JOIN domain_metadata dm ON h.domain = dm.domain
WHERE h.status = 'active'
GROUP BY h.domain, dm.active_count
HAVING actual_count != recorded_count;
```

**Auto-Repair:**
```python
def repair_domain_metadata():
    """Fix discrepancies between heuristics and domain_metadata."""
    conn = get_connection()

    # Recalculate counts from source of truth (heuristics table)
    conn.execute("""
        UPDATE domain_metadata
        SET
            active_count = (SELECT COUNT(*) FROM heuristics WHERE domain = domain_metadata.domain AND status = 'active'),
            dormant_count = (SELECT COUNT(*) FROM heuristics WHERE domain = domain_metadata.domain AND status = 'dormant'),
            archived_count = (SELECT COUNT(*) FROM heuristics WHERE domain = domain_metadata.domain AND status = 'archived'),
            deprecated_count = (SELECT COUNT(*) FROM heuristics WHERE domain = domain_metadata.domain AND status = 'deprecated'),
            updated_at = CURRENT_TIMESTAMP
    """)
    conn.commit()

    log("Domain metadata repaired from heuristics table")
```

### 7.5 User Forces Insertion Past Limit

**Scenario:** User runs manual SQL: `INSERT INTO heuristics (domain, rule, status) VALUES ('test', 'manual', 'active')`

**Protection:**

1. **Application-Level Validation:**
   ```python
   def add_heuristic(domain, rule, **kwargs):
       """Add heuristic with validation."""
       # Check domain limit BEFORE insertion
       dm = get_domain_metadata(domain)
       if dm.active_count >= dm.hard_limit:
           raise DomainCapacityError(f"Domain {domain} at hard limit ({dm.hard_limit})")

       # Proceed with insertion
       ...
   ```

2. **Database-Level Constraint (Optional):**
   ```sql
   -- Trigger to prevent insertions past hard limit
   CREATE TRIGGER IF NOT EXISTS enforce_hard_limit
   BEFORE INSERT ON heuristics
   FOR EACH ROW
   WHEN NEW.status = 'active'
   BEGIN
       SELECT CASE
           WHEN (SELECT active_count FROM domain_metadata WHERE domain = NEW.domain) >=
                (SELECT hard_limit FROM domain_metadata WHERE domain = NEW.domain)
           THEN RAISE(ABORT, 'Hard limit exceeded for domain')
       END;
   END;
   ```

   **Caution:** This trigger might cause issues with batch imports. Use only if strict enforcement needed.

---

## 8. Test Scenarios

### 8.1 Normal Operation (Under Soft Limit)

**Test: Domain stays at soft limit**

```python
def test_normal_operation():
    """Domain operates normally under soft limit."""
    manager = LifecycleManager()
    domain = "test-normal"

    # Add 5 heuristics (at soft limit)
    for i in range(5):
        manager.add_heuristic(
            domain=domain,
            rule=f"Test rule {i}",
            confidence=0.60,
            times_validated=2
        )

    # Check state
    dm = manager.get_domain_metadata(domain)
    assert dm.active_count == 5
    assert dm.is_in_overflow == False
    assert dm.entered_overflow_at is None

    # Verify new low-quality heuristic is rejected
    result = manager.add_heuristic(
        domain=domain,
        rule="Low quality rule",
        confidence=0.40,  # Below expansion threshold
        times_validated=1
    )
    assert result.accepted == False
    assert result.reason == "Below expansion threshold"
```

### 8.2 Expansion Trigger (Quality 6th Heuristic)

**Test: High-quality heuristic triggers expansion**

```python
def test_expansion_trigger():
    """Domain expands when exceptional heuristic arrives."""
    manager = LifecycleManager()
    domain = "test-expansion"

    # Add 5 normal heuristics
    for i in range(5):
        manager.add_heuristic(
            domain=domain,
            rule=f"Rule {i}",
            confidence=0.60,
            times_validated=3
        )

    # Add exceptional 6th heuristic
    result = manager.add_heuristic(
        domain=domain,
        rule="Exceptional rule",
        confidence=0.80,  # High quality
        times_validated=5,
        novelty_score=0.85  # Very novel
    )

    # Verify expansion
    assert result.accepted == True
    assert result.expansion_triggered == True

    dm = manager.get_domain_metadata(domain)
    assert dm.active_count == 6
    assert dm.is_in_overflow == True
    assert dm.entered_overflow_at is not None

    # Check expansion event logged
    events = manager.get_expansion_events(domain)
    assert len(events) == 1
    assert events[0].event_type == "expansion"
    assert events[0].count_before == 5
    assert events[0].count_after == 6
```

### 8.3 Contraction (Domain Shrinks Back)

**Test: Domain contracts after grace period**

```python
def test_contraction():
    """Domain contracts back to soft limit after grace period."""
    manager = LifecycleManager()
    domain = "test-contraction"

    # Setup: Domain in overflow with 8 heuristics
    for i in range(8):
        manager.add_heuristic(
            domain=domain,
            rule=f"Rule {i}",
            confidence=0.50 + (i * 0.05),  # Varying quality
            times_validated=2 + i
        )

    dm = manager.get_domain_metadata(domain)
    dm.entered_overflow_at = datetime.now() - timedelta(days=10)  # 10 days ago
    manager.update_domain_metadata(dm)

    # Run maintenance (should trigger contraction)
    result = manager.run_maintenance()

    # Verify contraction started
    assert result.contractions_performed > 0

    dm = manager.get_domain_metadata(domain)
    assert dm.active_count < 8  # Reduced
    assert dm.active_count >= 5  # Not below soft limit yet

    # Check that lowest-scoring heuristics were made dormant
    dormant = manager.get_heuristics(domain=domain, status="dormant")
    assert len(dormant) > 0
```

### 8.4 Hard Limit Enforcement

**Test: Hard limit cannot be exceeded**

```python
def test_hard_limit_enforcement():
    """Hard limit is strictly enforced."""
    manager = LifecycleManager()
    domain = "test-hard-limit"

    # Add 10 heuristics (at hard limit)
    for i in range(10):
        manager.add_heuristic(
            domain=domain,
            rule=f"Rule {i}",
            confidence=0.70 + (i * 0.02),
            times_validated=5
        )

    dm = manager.get_domain_metadata(domain)
    assert dm.active_count == 10
    assert dm.is_in_overflow == True

    # Try to add 11th heuristic (even if exceptional)
    result = manager.add_heuristic(
        domain=domain,
        rule="Exceptional 11th rule",
        confidence=0.95,  # Exceptional quality
        times_validated=10,
        novelty_score=0.90
    )

    # Should be rejected
    assert result.accepted == False
    assert result.reason == "Hard limit reached"

    # Domain count unchanged
    dm = manager.get_domain_metadata(domain)
    assert dm.active_count == 10
```

### 8.5 Merge Workflow

**Test: Similar heuristics are merged during contraction**

```python
def test_merge_workflow():
    """Similar heuristics merge during contraction."""
    manager = LifecycleManager()
    domain = "test-merge"

    # Add 7 heuristics, including 2 similar ones
    manager.add_heuristic(domain=domain, rule="Always use refs for callbacks", confidence=0.70, times_validated=5)
    manager.add_heuristic(domain=domain, rule="Use useRef for callback storage", confidence=0.65, times_validated=3)
    for i in range(5):
        manager.add_heuristic(domain=domain, rule=f"Other rule {i}", confidence=0.60, times_validated=2)

    dm = manager.get_domain_metadata(domain)
    assert dm.active_count == 7

    # Simulate grace period passed
    dm.entered_overflow_at = datetime.now() - timedelta(days=10)
    manager.update_domain_metadata(dm)

    # Run maintenance with merge detection enabled
    result = manager.run_maintenance(enable_merge=True)

    # Verify merge occurred
    assert result.merges_performed > 0

    # Check merge history
    merges = manager.get_heuristic_merges(domain=domain)
    assert len(merges) > 0
    assert merges[0].similarity_score >= 0.60

    # Verify count reduced
    dm = manager.get_domain_metadata(domain)
    assert dm.active_count < 7
```

### 8.6 Novelty Detection

**Test: Duplicate heuristics are rejected**

```python
def test_novelty_detection():
    """Duplicate heuristics are detected and rejected."""
    manager = LifecycleManager()
    domain = "test-novelty"

    # Add original heuristic
    manager.add_heuristic(
        domain=domain,
        rule="Use refs for callbacks to prevent useEffect loops",
        confidence=0.75,
        times_validated=5
    )

    # Try to add very similar heuristic
    result = manager.add_heuristic(
        domain=domain,
        rule="Store callbacks in refs to avoid useEffect dependencies",
        confidence=0.70,
        times_validated=3
    )

    # Should be rejected as duplicate
    assert result.accepted == False
    assert result.reason == "Duplicate: novelty score too low"
    assert result.novelty_score < 0.40

    # Suggest merge instead
    assert result.suggested_action == "merge"
    assert result.merge_candidate_id is not None
```

### 8.7 Grace Period

**Test: No contraction during grace period**

```python
def test_grace_period():
    """Contraction does not occur during grace period."""
    manager = LifecycleManager()
    domain = "test-grace"

    # Setup: Domain with 7 heuristics (in overflow)
    for i in range(7):
        manager.add_heuristic(domain=domain, rule=f"Rule {i}", confidence=0.60, times_validated=2)

    dm = manager.get_domain_metadata(domain)
    dm.entered_overflow_at = datetime.now() - timedelta(days=3)  # Only 3 days
    manager.update_domain_metadata(dm)

    # Run maintenance
    result = manager.run_maintenance()

    # No contraction should occur (still in 7-day grace period)
    assert result.contractions_performed == 0

    dm = manager.get_domain_metadata(domain)
    assert dm.active_count == 7  # Unchanged
    assert dm.is_in_overflow == True

    # Verify pressure is 0.0
    pressure = manager.calculate_overflow_pressure(domain)
    assert pressure == 0.0
```

### 8.8 Health-Based Expansion Blocking

**Test: Unhealthy domain blocks expansion**

```python
def test_health_based_blocking():
    """Unhealthy domain cannot expand."""
    manager = LifecycleManager()
    domain = "test-health"

    # Add 5 low-quality heuristics (unhealthy domain)
    for i in range(5):
        h_id = manager.add_heuristic(
            domain=domain,
            rule=f"Poor rule {i}",
            confidence=0.30,  # Low quality
            times_validated=1
        ).heuristic_id

        # Mark some as deprecated
        if i % 2 == 0:
            manager.deprecate_heuristic(h_id)

    # Calculate health
    manager.update_domain_health(domain)
    dm = manager.get_domain_metadata(domain)
    assert dm.health_score < 0.50  # Unhealthy

    # Try to add exceptional heuristic
    result = manager.add_heuristic(
        domain=domain,
        rule="Exceptional rule",
        confidence=0.75,
        times_validated=5
    )

    # Should be rejected due to domain health
    assert result.accepted == False
    assert result.reason == "Domain health too low for expansion"
    assert dm.active_count == 5  # No expansion
```

---

## 9. Implementation Estimate

### 9.1 Lines of Code

**Schema Changes (SQL):**
- domain_metadata table: ~60 lines
- heuristic_merges table: ~25 lines
- expansion_events table: ~25 lines
- Triggers (sync counts): ~80 lines
- Views (overflow_pressure_dashboard, health_score): ~60 lines
**Subtotal: ~250 lines SQL**

**Python Implementation (lifecycle_manager.py extensions):**
- Domain metadata CRUD: ~100 lines
- Expansion logic (quality check, novelty detection): ~150 lines
- Contraction algorithm: ~200 lines
- Merge detection & execution: ~180 lines
- Overflow pressure calculation: ~80 lines
- Health score calculation: ~60 lines
- Test scenarios: ~400 lines
**Subtotal: ~1,170 lines Python**

**Total Estimate: ~1,420 lines of code**

### 9.2 Complexity Rating

| Component | Complexity | Reason |
|-----------|-----------|---------|
| Schema changes | Low | Straightforward tables, triggers |
| Domain metadata sync | Medium | Trigger logic, race condition handling |
| Expansion criteria | Medium | Multiple factors, threshold tuning |
| Novelty detection | High | Semantic similarity, keyword extraction |
| Contraction algorithm | High | Multi-step decision tree, merge logic |
| Merge execution | High | Combining heuristics, validation tracking |
| Testing | Medium | Many scenarios, state setup required |

**Overall Complexity: Medium-High**

**Risk Areas:**
1. **Novelty detection accuracy:** Keyword-based similarity is crude; may need embeddings
2. **Merge quality:** Automated merging might produce incoherent heuristics
3. **Performance:** Triggers on every heuristic update could slow inserts
4. **Race conditions:** Concurrent insertions might bypass limits

### 9.3 Dependencies

**External:**
- SQLite 3.35+ (for triggers, views, JSON functions)
- Python 3.8+ (dataclasses, type hints)
- (Optional) Sentence-Transformers for embeddings-based novelty

**Internal:**
- Phase 1 lifecycle manager (required)
- Existing heuristics table schema (required)
- query.py integration (for dashboard visibility)

**Data Migration:**
- Need to populate domain_metadata from existing heuristics
- Backfill expansion_events from confidence_updates history
- One-time migration script (~50 lines)

### 9.4 Implementation Phases

**Phase 2a: Foundation (Week 1)**
- Schema changes (tables, triggers, views)
- Domain metadata CRUD
- Basic expansion/contraction logic
- **Deliverable:** Soft/hard limits enforced

**Phase 2b: Intelligence (Week 2)**
- Novelty detection (keyword-based)
- Merge candidate detection
- Health score calculation
- **Deliverable:** Smart expansion decisions

**Phase 2c: Operations (Week 3)**
- Contraction algorithm
- Merge execution
- Overflow pressure dashboard
- **Deliverable:** Full elasticity loop working

**Phase 2d: Testing & Refinement (Week 4)**
- All test scenarios implemented
- Performance tuning
- CEO decision workflows
- **Deliverable:** Production-ready

**Total Time Estimate: 3-4 weeks (for single developer)**

---

## 10. FINDINGS

### [fact] Current Phase 1 has only hard limit of 10, no soft limit distinction
The `LifecycleConfig` in `lifecycle_manager.py` line 56 sets `max_active_per_domain = 10` as a single boundary. There is no concept of soft vs. hard limits in Phase 1.

### [fact] Eviction score formula: confidence × recency_factor × usage_factor
Defined in migration 002, lines 113-128. Lower score = higher eviction priority. Recency ranges from 0.1 (>90 days) to 1.0 (<7 days). Usage ranges from 0.5 (0 validations) to 1.0 (>10 validations).

### [fact] Golden rules are protected from eviction
Line 658 in `lifecycle_manager.py`: `if cursor.fetchone()['is_golden']: continue` — golden rules skip eviction.

### [hypothesis] Novelty detection via keyword overlap will catch ~80% of duplicates
Jaccard similarity on keywords should detect obvious duplicates (e.g., "use refs for callbacks" vs "store callbacks in refs"). However, it will miss semantic duplicates with different wording (e.g., "avoid inline functions in deps" vs "extract functions to prevent re-renders"). May need embeddings for remaining 20%.

### [hypothesis] Gradual contraction (1-2 per week) prevents thrashing
Immediate snap-back from 10 → 5 could evict valuable heuristics during temporary spikes. Grace period + gradual reduction allows domain to stabilize and identify true low-value candidates.

### [hypothesis] Merge quality will be the biggest challenge
Automated merging of two heuristics requires:
1. Combining rule text (concatenation? LLM summary?)
2. Merging explanations (which to keep?)
3. Weighted confidence (simple average? validation-weighted?)
4. Validation counts (sum? or keep separate tracking?)

This is complex and error-prone. May need CEO review for all merges initially.

### [blocker] No embeddings infrastructure currently exists
For high-quality novelty detection, need sentence embeddings (e.g., all-MiniLM-L6-v2). This requires:
- Python package: `sentence-transformers` (~500 MB model download)
- Embedding cache table in database
- Embedding computation on heuristic insertion (~50ms per heuristic)

Decision: Start with keyword-based (Phase 2b), add embeddings later (Phase 3?) if needed.

### [blocker] Merge execution needs conflict resolution strategy
When merging two heuristics with contradictory validations:
- H1: 10 validations, 2 violations, confidence 0.75
- H2: 5 validations, 8 violations, confidence 0.45

Should merged heuristic be:
- Option A: Sum (15 validations, 10 violations) — reflects total history
- Option B: Weighted average — reflects relative confidence
- Option C: Keep better one, discard worse — not truly a merge

**Recommendation:** Option A (sum), but recalculate confidence from scratch based on merged validation history.

### [question] Should soft limit be configurable per domain?
Some domains (e.g., "git-hooks") might benefit from higher soft limit (7) due to complexity, while others (e.g., "markdown-formatting") might need lower (3) due to simplicity.

**Recommendation:** Start with global defaults (soft=5, hard=10), add per-domain overrides in domain_metadata later if needed.

### [question] How to handle "permanent overflow" domains?
If a domain legitimately needs 10+ heuristics (all high-quality, no merges possible), current design forces manual intervention.

**Options:**
1. CEO manually raises hard limit to 15 for that domain
2. System auto-suggests domain split (e.g., "websocket" → "websocket-connection" + "websocket-messaging")
3. Accept overflow state as permanent, disable contraction alerts

**Recommendation:** Option 1 + 2 (CEO can raise limit OR split domain, system suggests split).

### [question] Should expansion be automatic or require CEO approval?
Current design assumes automatic expansion if quality thresholds met. But this could lead to runaway growth if thresholds are miscalibrated.

**Alternative:** First expansion (5 → 6) is automatic, but subsequent expansions (7, 8, 9) require CEO approval.

**Recommendation:** Start with automatic (faster iteration), add CEO approval for 8+ if abuse detected.

### [fact] Trigger-based count synchronization has race condition risk
If two heuristics are inserted concurrently in the same domain:
1. Thread A reads `active_count = 5`
2. Thread B reads `active_count = 5`
3. Thread A increments to 6, commits
4. Thread B increments to 6, commits (should be 7!)

**Mitigation:** SQLite has DB-level locking, so this is less likely, but still possible with WAL mode.

**Solution:** Use atomic increment in trigger: `UPDATE ... SET active_count = active_count + 1` (not read-then-write).

### [hypothesis] Grace period of 7 days is sufficient for most cases
Most domain overflow events are caused by:
- Burst learning (multiple failures analyzed together) — resolves in 1-3 days
- Domain maturation (gradual refinement) — sustained growth over weeks

7-day grace period handles burst case, 28-day max overflow handles maturation case.

### [fact] No performance benchmarks exist for trigger overhead
Adding 3 triggers (sync counts on insert/update/delete) will add overhead to every heuristic operation. Need benchmarks:
- Time to insert 1000 heuristics (with/without triggers)
- Time to update status for 100 heuristics (bulk update)

If triggers add >10% overhead, consider batch sync instead (update counts every 5 minutes via cron).

---

## Conclusion

Phase 2 domain elasticity solves the knowledge loss problem at hard limit 5 while preventing unbounded growth. The two-tier system (soft limit 5, hard limit 10) with intelligent expansion criteria and gradual contraction provides flexibility without chaos.

**Key Innovations:**
1. Quality-gated expansion (confidence + validations + novelty)
2. Health-based blocking (sick domains can't grow)
3. Graceful contraction (7-day grace, 1-2 per week reduction)
4. Merge-before-evict strategy (preserve knowledge)
5. Overflow pressure metrics (visibility + alerting)

**Risks to Manage:**
- Novelty detection accuracy (start keyword, upgrade to embeddings if needed)
- Merge quality (CEO review initially, automate later)
- Trigger performance (benchmark, consider batch sync)
- Race conditions (use atomic increments)

**Next Steps:**
1. CEO review of design
2. Implement Phase 2a (schema + basic logic)
3. Test with real domains
4. Iterate based on feedback

This design is ready for implementation.
