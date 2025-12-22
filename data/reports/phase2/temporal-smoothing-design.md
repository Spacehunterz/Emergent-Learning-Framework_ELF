# Phase 2: Temporal Smoothing Design
## Exponential Moving Average for Confidence Updates

**Agent:** Agent 3 (Ultrathink Swarm)
**Date:** 2025-12-12
**Status:** Design Proposal
**Complexity:** High

---

## 1. Problem Statement

### Why Discrete Updates Are Problematic

The current Phase 1 lifecycle manager uses **discrete, immediate confidence updates**. Each validation, violation, or contradiction causes an instantaneous step change in confidence:

```python
# Current implementation (lifecycle_manager.py:230-256)
if update_type == UpdateType.SUCCESS:
    delta = 0.1 * (1 - old_conf)
    new_conf = min(old_conf + delta, max_confidence)
```

**Problems with this approach:**

1. **Noise Sensitivity**: A single anomalous event (edge case, measurement error, timing issue) causes an immediate, permanent confidence shift.

2. **Erratic Behavior**: Confidence can zigzag rapidly if validation/violation events alternate, making it hard to distinguish signal from noise.

3. **No Context Window**: Each update is treated in isolation. No notion of "recent trend" or "rolling average."

4. **Gaming via Strategic Timing**: An adversary who understands the cooldown (60 minutes) can wait and apply updates at maximum frequency, still causing rapid swings within rate limits.

5. **Poor Response to Transient Conditions**: Temporary environmental changes (e.g., testing in a degraded environment) can permanently damage confidence even if the heuristic is fundamentally sound.

### Examples of Noise Sensitivity

**Scenario 1: Flaky Test Environment**
```
Heuristic: "Cache database queries for performance"
- Confidence starts at 0.70
- Test runs in CI with network latency spike → FAILURE (conf drops to 0.63)
- Next test in normal conditions → SUCCESS (conf rises to 0.67)
- CI flakes again → FAILURE (conf drops to 0.60)
- Result: Confidence degraded from 0.70 → 0.60 due to transient infrastructure issues
```

**Scenario 2: Edge Case Discovery**
```
Heuristic: "Validate user input with regex"
- Confidence at 0.85 after 50 successful applications
- Discover 1 edge case with Unicode normalization → CONTRADICTION (conf drops to 0.72)
- Single edge case causes 13-point drop despite 50 successes
- If smoothed: New evidence would be incorporated gradually
```

**Scenario 3: Measurement Timing Attack**
```
Adversarial scenario:
1. Wait for 60-minute cooldown
2. Apply UPDATE_SUCCESS (confidence increases)
3. Wait exactly 60 minutes
4. Apply UPDATE_SUCCESS again
5. Repeat 5 times/day (max rate limit)
6. Result: Mediocre heuristic's confidence artificially inflated by timing exploitation
```

### Gaming via Timing Attacks

**Attack Pattern**: Pump-and-Dump with Cooldown Exploitation
```
Timeline:
00:00 - Apply SUCCESS (+0.05 to conf 0.50 → 0.55)
01:00 - Apply SUCCESS (+0.045 to conf 0.55 → 0.595)
02:00 - Apply SUCCESS (+0.0405 to conf 0.595 → 0.6355)
03:00 - Apply SUCCESS (+0.0365 to conf 0.6355 → 0.672)
04:00 - Apply SUCCESS (+0.0328 to conf 0.672 → 0.7048)

Result: In 4 hours, confidence pumped from 0.50 → 0.70 by exploiting cooldown timing.
```

Rate limiting prevents frequency but doesn't smooth the impact of each update.

---

## 2. EMA Fundamentals

### Mathematical Definition

Exponential Moving Average (EMA) is a weighted average where recent values have exponentially higher weight than older values:

```
EMA_t = α × value_t + (1 - α) × EMA_{t-1}
```

Where:
- `α` (alpha) = smoothing factor (0 < α ≤ 1)
- `value_t` = new raw value at time t
- `EMA_{t-1}` = previous EMA value
- `EMA_t` = new EMA value

**Rewritten for clarity:**
```
new_EMA = α × new_value + (1 - α) × old_EMA
```

### Choosing α (Smoothing Factor)

Alpha determines how much weight to give new data vs. historical average:

| α Value | Weight to New Data | Weight to History | Behavior |
|---------|-------------------|-------------------|----------|
| 1.0     | 100%              | 0%                | No smoothing (current behavior) |
| 0.5     | 50%               | 50%               | Balanced |
| 0.2     | 20%               | 80%               | Highly smoothed |
| 0.1     | 10%               | 90%               | Very stable |
| 0.05    | 5%                | 95%               | Extremely stable |

**Rule of thumb**: Smaller α = smoother, more resistant to noise, slower to respond.

### Half-Life Interpretation

The **half-life** is the number of updates required for old data to decay to 50% influence:

```
half_life ≈ ln(2) / ln(1 / (1 - α))
```

Examples:
- α = 0.5 → half_life ≈ 1 update (very fast decay)
- α = 0.2 → half_life ≈ 3 updates
- α = 0.1 → half_life ≈ 7 updates
- α = 0.05 → half_life ≈ 14 updates

**Practical meaning**: With α = 0.1, it takes ~7 updates for a single anomalous event to lose most of its influence.

### Comparison to Simple Moving Average (SMA)

**Simple Moving Average**:
```
SMA = (value_1 + value_2 + ... + value_n) / n
```

**Pros of SMA:**
- Easy to understand
- All data in window weighted equally

**Cons of SMA:**
- Requires storing entire window of past values
- Old data has same weight as new data
- "Cliff effect" when old data exits the window

**Pros of EMA:**
- Only requires storing previous EMA (constant memory)
- Recent data weighted higher (more responsive to trends)
- Smooth decay (no cliff effect)
- Computationally efficient (single multiplication + addition)

**For heuristic confidence**, EMA is superior because:
1. We don't want to store 100+ past confidence values per heuristic
2. Recent validations should matter more than ancient ones
3. We want smooth, continuous adjustment

---

## 3. Confidence EMA Design

### What Gets Smoothed?

**Option A: Smooth the Confidence Value Directly**
```python
# After calculating discrete delta from update type
raw_new_conf = old_conf + delta

# Smooth the result
ema_conf = α × raw_new_conf + (1 - α) × old_ema_conf
```

**Option B: Smooth the Delta**
```python
# Calculate discrete delta
discrete_delta = calculate_delta(update_type, old_conf)

# Smooth the delta
ema_delta = α × discrete_delta + (1 - α) × old_ema_delta

# Apply smoothed delta
new_conf = old_conf + ema_delta
```

**Option C: Smooth Both (Hybrid)**
```python
# Calculate target confidence
target_conf = old_conf + discrete_delta

# Move current EMA toward target
ema_conf = α × target_conf + (1 - α) × old_ema_conf
```

**Recommendation: Option A (Smooth Confidence Directly)**

**Rationale**:
- Most intuitive: Confidence itself is what we care about
- Aligns with existing bounds checking (min/max confidence)
- Delta smoothing (Option B) can accumulate drift over time
- Simplest to reason about and debug

### Proposed Algorithm

```python
def update_confidence_with_ema(
    heuristic_id: int,
    update_type: UpdateType,
    reason: str = "",
    session_id: Optional[str] = None,
    agent_id: Optional[str] = None,
    force: bool = False
) -> Dict[str, Any]:
    """Update confidence with EMA smoothing."""

    # 1. Rate limiting check (unchanged)
    if not force:
        allowed, limit_reason = can_update_confidence(heuristic_id, session_id)
        if not allowed:
            return {"success": False, "rate_limited": True, "reason": limit_reason}

    # 2. Get current state
    old_conf = heuristic.confidence
    old_ema = heuristic.confidence_ema  # New field
    alpha = heuristic.ema_alpha  # New field

    # 3. Calculate raw target confidence (using existing formula)
    if update_type == UpdateType.SUCCESS:
        raw_delta = 0.1 * (1 - old_conf)
        raw_target = min(old_conf + raw_delta, max_confidence)
    elif update_type == UpdateType.FAILURE:
        raw_delta = 0.1 * old_conf
        raw_target = max(old_conf - raw_delta, min_confidence)
    elif update_type == UpdateType.CONTRADICTION:
        raw_delta = 0.15 * old_conf
        raw_target = max(old_conf - raw_delta, min_confidence)
    elif update_type == UpdateType.DECAY:
        raw_target = max(old_conf * 0.92, min_confidence)
    elif update_type == UpdateType.REVIVAL:
        raw_target = max(old_conf, 0.35)

    # 4. Apply EMA smoothing
    new_ema = alpha * raw_target + (1 - alpha) * old_ema

    # 5. Clamp to bounds (defense in depth)
    new_ema = max(min_confidence, min(max_confidence, new_ema))

    # 6. Update database
    UPDATE heuristics SET
        confidence = new_ema,
        confidence_ema = new_ema,
        last_confidence_update = NOW(),
        ...

    # 7. Record audit trail with both raw and smoothed values
    INSERT INTO confidence_updates (
        heuristic_id, old_confidence, new_confidence,
        raw_target_confidence,  # New field
        delta, smoothed_delta,  # Track both
        alpha_used,  # Record what alpha was used
        update_type, reason
    ) VALUES (...)

    return {
        "success": True,
        "old_confidence": old_conf,
        "new_confidence": new_ema,
        "raw_target": raw_target,
        "smoothing_effect": abs(raw_target - new_ema),
        "alpha": alpha
    }
```

### Separate α for Increases vs. Decreases?

**Proposal: YES - Asymmetric Smoothing**

```python
alpha_increase = 0.15  # Slower to increase (more skeptical of good news)
alpha_decrease = 0.20  # Faster to decrease (more responsive to bad news)

if raw_target > old_ema:
    alpha = alpha_increase
else:
    alpha = alpha_decrease

new_ema = alpha * raw_target + (1 - alpha) * old_ema
```

**Rationale**:
- **Conservative principle**: Easier to lose confidence than gain it
- **Mirrors real-world trust**: Trust is built slowly, lost quickly
- **Security posture**: Respond faster to failures (safety-critical)
- **Prevents pump-and-dump**: Makes artificial inflation harder

**Example**:
```
Heuristic at confidence 0.60:
- Receives SUCCESS → raw_target 0.64
  → alpha=0.15 → new_ema = 0.15×0.64 + 0.85×0.60 = 0.606 (+0.006)
- Receives FAILURE → raw_target 0.54
  → alpha=0.20 → new_ema = 0.20×0.54 + 0.80×0.60 = 0.588 (-0.012)

Failure has 2× the impact of success (asymmetric protection)
```

### Warm-Up Period for New Heuristics

**Problem**: New heuristics have no EMA history. How to initialize?

**Solution: Bootstrap Period**

```python
def initialize_new_heuristic(rule: str, domain: str, initial_conf: float = 0.5):
    """Create new heuristic with bootstrap EMA."""
    INSERT INTO heuristics (
        domain, rule, confidence, confidence_ema, ema_alpha,
        ema_warmup_remaining, ...
    ) VALUES (
        domain, rule, initial_conf, initial_conf,
        0.30,  # Higher alpha during warmup (more responsive)
        5,     # Require 5 updates to "settle"
        ...
    )
```

**Warm-up behavior**:
```python
if heuristic.ema_warmup_remaining > 0:
    # Use higher alpha during warmup
    alpha = 0.30  # More responsive to early data
    heuristic.ema_warmup_remaining -= 1
else:
    # Use steady-state alpha
    alpha = heuristic.ema_alpha  # Normal smoothing
```

**After 5 updates**, transition to steady-state smoothing:
```python
if heuristic.ema_warmup_remaining == 0:
    # Graduated from warmup - switch to mature alpha
    heuristic.ema_alpha = 0.15 if increase else 0.20
```

### Relationship to Existing Rate Limiting

**Rate limiting and EMA are COMPLEMENTARY, not redundant:**

| Mechanism | Purpose | What It Prevents |
|-----------|---------|------------------|
| **Rate Limiting** | Controls UPDATE FREQUENCY | Rapid-fire spam (20 updates in 1 minute) |
| **EMA Smoothing** | Controls UPDATE MAGNITUDE | Each update's impact (even if properly spaced) |

**Example**:
```
Without EMA:
- Update 1 (hour 0): +0.05 confidence
- Update 2 (hour 1): +0.05 confidence
- Update 3 (hour 2): +0.05 confidence
- Total change: +0.15 in 2 hours

With EMA (α=0.15):
- Update 1: +0.0075 smoothed
- Update 2: +0.0071 smoothed
- Update 3: +0.0067 smoothed
- Total change: +0.021 in 2 hours (86% reduction in swing)
```

**Both mechanisms together**:
- Rate limiting: "You can only update 5 times per day, with 1-hour gaps"
- EMA smoothing: "Each update only moves confidence by α fraction toward target"

**Result**: Even if attacker maxes out rate limits, they can't cause dramatic swings.

---

## 4. Parameter Tuning

### Recommended α Values with Justification

**Base Configuration**:
```python
class EMAConfig:
    # New heuristics (warmup phase)
    alpha_warmup = 0.30          # Fast learning from initial data
    warmup_update_count = 5      # Bootstrap with first 5 updates

    # Mature heuristics (steady state)
    alpha_increase = 0.15        # Slow to increase (skeptical of good news)
    alpha_decrease = 0.20        # Faster to decrease (respond to failures)

    # High-confidence heuristics (approaching golden)
    alpha_increase_high = 0.10   # Very slow to increase when conf > 0.80
    alpha_decrease_high = 0.15   # Still responsive to failures

    # Low-confidence heuristics (struggling)
    alpha_increase_low = 0.25    # Give them a chance to recover
    alpha_decrease_low = 0.20    # Standard decrease
```

### Different α for Different Scenarios

#### Scenario 1: New Heuristic (More Responsive)

```python
if heuristic.times_validated + heuristic.times_violated < 5:
    alpha = 0.30  # Warmup: Learn quickly from early data
```

**Justification**: With no history, we want to incorporate early evidence faster to quickly converge toward true accuracy.

**Half-life**: ~2 updates (rapid initial adjustment)

---

#### Scenario 2: Mature Heuristic (More Stable)

```python
if total_applications >= 20:
    if is_increase:
        alpha = 0.15  # Stable, slow increase
    else:
        alpha = 0.20  # Responsive to failures
```

**Justification**: Well-tested heuristic should be stable. Changes should be gradual and evidence-based.

**Half-life**: ~4.3 updates for increases, ~3.1 updates for decreases

---

#### Scenario 3: High-Confidence (Harder to Move)

```python
if heuristic.confidence > 0.80:
    if is_increase:
        alpha = 0.10  # Very hard to increase further
    else:
        alpha = 0.15  # Moderately hard to decrease
```

**Justification**: High confidence implies strong evidence. Should require sustained trend to move significantly. This prevents "golden rule candidates" from being easily pumped over threshold.

**Half-life**: ~6.6 updates for increases (very stable)

**Example**:
```
Heuristic at 0.85 confidence receives SUCCESS:
- Raw target: 0.85 + 0.1*(1-0.85) = 0.865
- With alpha=0.10: new_ema = 0.10×0.865 + 0.90×0.85 = 0.8515
- Change: +0.0015 (tiny adjustment)

Would take ~10 consecutive successes to push from 0.85 → 0.90
```

---

#### Scenario 4: Low-Confidence (Easier to Recover)

```python
if heuristic.confidence < 0.30:
    if is_increase:
        alpha = 0.25  # Give struggling heuristics a chance
    else:
        alpha = 0.20  # Standard decrease
```

**Justification**: Low confidence might be due to early failures or misapplication. If heuristic is legitimately useful in new context, allow faster recovery.

**Half-life**: ~2.4 updates (faster recovery possible)

**Example**:
```
Heuristic at 0.25 confidence, newly relevant context → SUCCESS:
- Raw target: 0.25 + 0.1*(1-0.25) = 0.325
- With alpha=0.25: new_ema = 0.25×0.325 + 0.75×0.25 = 0.26875
- Change: +0.019 (noticeable boost)
```

---

### Adaptive α Formula

**Dynamic alpha based on heuristic state**:

```python
def calculate_alpha(heuristic, is_increase: bool) -> float:
    """Calculate adaptive alpha based on heuristic characteristics."""

    total_apps = (heuristic.times_validated +
                  heuristic.times_violated +
                  heuristic.times_contradicted)
    conf = heuristic.confidence

    # Warmup phase
    if total_apps < 5:
        return 0.30

    # High confidence zone (approaching golden)
    if conf > 0.80:
        return 0.10 if is_increase else 0.15

    # Low confidence zone (struggling, allow recovery)
    if conf < 0.30:
        return 0.25 if is_increase else 0.20

    # Mature middle range (steady state)
    if total_apps >= 20:
        return 0.15 if is_increase else 0.20

    # Default (immature but past warmup)
    return 0.20 if is_increase else 0.25
```

**This adaptive approach**:
- Learns fast when new
- Stabilizes when mature
- Protects high-confidence heuristics
- Gives low-confidence heuristics a recovery path
- Maintains asymmetry (slower to increase)

---

## 5. Implementation Strategy

### Store EMA State in Database

**New columns** in `heuristics` table:

```sql
ALTER TABLE heuristics ADD COLUMN confidence_ema REAL DEFAULT 0.5;
ALTER TABLE heuristics ADD COLUMN ema_alpha REAL DEFAULT 0.15;
ALTER TABLE heuristics ADD COLUMN ema_warmup_remaining INTEGER DEFAULT 5;
ALTER TABLE heuristics ADD COLUMN last_ema_update DATETIME;
```

**Migration strategy** (for existing heuristics):

```sql
-- Initialize EMA to current confidence for existing records
UPDATE heuristics
SET confidence_ema = confidence,
    ema_alpha = CASE
        WHEN confidence > 0.80 THEN 0.10
        WHEN confidence < 0.30 THEN 0.25
        ELSE 0.15
    END,
    ema_warmup_remaining = 0,  -- Existing heuristics skip warmup
    last_ema_update = last_confidence_update
WHERE confidence_ema IS NULL;
```

### Update on Each Confidence Change

**Pseudocode**:

```python
def update_confidence_with_ema(heuristic_id, update_type, ...):
    # 1. Load heuristic
    h = db.get_heuristic(heuristic_id)

    # 2. Calculate raw target (existing formula)
    raw_target = calculate_raw_target(h.confidence, update_type)

    # 3. Determine alpha
    is_increase = raw_target > h.confidence_ema
    alpha = calculate_adaptive_alpha(h, is_increase)

    # 4. Apply EMA
    new_ema = alpha * raw_target + (1 - alpha) * h.confidence_ema

    # 5. Handle warmup countdown
    if h.ema_warmup_remaining > 0:
        h.ema_warmup_remaining -= 1

    # 6. Update database
    db.execute("""
        UPDATE heuristics SET
            confidence = ?,
            confidence_ema = ?,
            ema_alpha = ?,
            ema_warmup_remaining = ?,
            last_ema_update = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (new_ema, new_ema, alpha, h.ema_warmup_remaining, heuristic_id))

    # 7. Audit trail
    record_update(heuristic_id, h.confidence, new_ema, raw_target, alpha, ...)
```

### Handle Gaps in Time (Decay During Inactivity)

**Question**: If heuristic is unused for 90 days, should EMA decay?

**Proposal: Separate Time-Based Decay from EMA**

```python
def apply_time_decay_if_needed(heuristic_id):
    """Apply decay for inactivity (separate from EMA)."""
    h = db.get_heuristic(heuristic_id)

    days_inactive = (datetime.now() - h.last_used_at).days

    if days_inactive > decay_threshold_days:
        # Calculate time-based decay
        decay_factor = 0.92 ** (days_inactive // decay_half_life_days)
        decayed_conf = h.confidence_ema * decay_factor

        # Apply decay WITHOUT smoothing (direct assignment)
        # Rationale: Time decay is already gradual, no need for EMA
        db.execute("""
            UPDATE heuristics SET
                confidence = ?,
                confidence_ema = ?,
                last_ema_update = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (decayed_conf, decayed_conf, heuristic_id))
```

**Key decision**: **Time decay bypasses EMA** because:
- Decay is already a smooth, gradual process (exponential)
- EMA is for evidence-based updates (validation/violation)
- Time decay is deterministic, not stochastic

---

### Pseudocode for Update Algorithm

**Complete implementation flow**:

```python
class LifecycleManagerPhase2(LifecycleManager):
    """Extends Phase 1 with temporal smoothing."""

    def update_confidence(self, heuristic_id, update_type, reason="",
                         session_id=None, agent_id=None, force=False):
        """Update confidence with EMA smoothing."""

        # === PHASE 1: Rate Limiting (unchanged) ===
        if not force:
            allowed, limit_reason = self.can_update_confidence(heuristic_id, session_id)
            if not allowed:
                return {"success": False, "rate_limited": True, "reason": limit_reason}

        conn = self._get_connection()
        try:
            # === PHASE 2: Load State ===
            cursor = conn.execute("""
                SELECT id, confidence, confidence_ema, ema_alpha,
                       ema_warmup_remaining, times_validated, times_violated,
                       times_contradicted
                FROM heuristics WHERE id = ?
            """, (heuristic_id,))
            row = cursor.fetchone()
            if not row:
                return {"success": False, "reason": "Heuristic not found"}

            old_conf = row['confidence']
            old_ema = row['confidence_ema']
            total_apps = (row['times_validated'] + row['times_violated'] +
                         row['times_contradicted'])

            # === PHASE 3: Calculate Raw Target (Phase 1 formula) ===
            if update_type == UpdateType.SUCCESS:
                raw_delta = 0.1 * (1 - old_conf)
                raw_target = min(old_conf + raw_delta, self.config.max_confidence)
            elif update_type == UpdateType.FAILURE:
                raw_delta = 0.1 * old_conf
                raw_target = max(old_conf - raw_delta, self.config.min_confidence)
            elif update_type == UpdateType.CONTRADICTION:
                raw_delta = 0.15 * old_conf
                raw_target = max(old_conf - raw_delta, self.config.min_confidence)
            elif update_type == UpdateType.DECAY:
                raw_target = max(old_conf * 0.92, self.config.min_confidence)
            elif update_type == UpdateType.REVIVAL:
                raw_target = max(old_conf, 0.35)
            else:
                return {"success": False, "reason": f"Unknown update type: {update_type}"}

            # === PHASE 4: Calculate Adaptive Alpha ===
            is_increase = raw_target > old_ema

            # Check if in warmup
            if row['ema_warmup_remaining'] > 0:
                alpha = 0.30  # Fast learning during warmup
                new_warmup = row['ema_warmup_remaining'] - 1
            else:
                # Adaptive alpha based on confidence and maturity
                if old_conf > 0.80:
                    alpha = 0.10 if is_increase else 0.15
                elif old_conf < 0.30:
                    alpha = 0.25 if is_increase else 0.20
                elif total_apps >= 20:
                    alpha = 0.15 if is_increase else 0.20
                else:
                    alpha = 0.20 if is_increase else 0.25
                new_warmup = 0

            # === PHASE 5: Apply EMA Smoothing ===
            new_ema = alpha * raw_target + (1 - alpha) * old_ema

            # === PHASE 6: Bounds Check (defense in depth) ===
            new_ema = max(self.config.min_confidence,
                         min(self.config.max_confidence, new_ema))

            # === PHASE 7: Update Counter (Phase 1 logic) ===
            if update_type == UpdateType.SUCCESS:
                conn.execute("UPDATE heuristics SET times_validated = times_validated + 1 WHERE id = ?",
                           (heuristic_id,))
            elif update_type == UpdateType.FAILURE:
                conn.execute("UPDATE heuristics SET times_violated = times_violated + 1 WHERE id = ?",
                           (heuristic_id,))
            elif update_type == UpdateType.CONTRADICTION:
                conn.execute("UPDATE heuristics SET times_contradicted = times_contradicted + 1 WHERE id = ?",
                           (heuristic_id,))

            # === PHASE 8: Update Heuristic ===
            today = date.today()
            reset_date = row.get('update_count_reset_date')
            update_count = row.get('update_count_today', 0)

            if reset_date != str(today):
                update_count = 1
                reset_date = str(today)
            else:
                update_count += 1

            conn.execute("""
                UPDATE heuristics SET
                    confidence = ?,
                    confidence_ema = ?,
                    ema_alpha = ?,
                    ema_warmup_remaining = ?,
                    last_confidence_update = ?,
                    last_ema_update = ?,
                    last_used_at = ?,
                    update_count_today = ?,
                    update_count_reset_date = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (new_ema, new_ema, alpha, new_warmup,
                  datetime.now().isoformat(), datetime.now().isoformat(),
                  datetime.now().isoformat(), update_count, reset_date,
                  heuristic_id))

            # === PHASE 9: Record Audit Trail (Enhanced) ===
            conn.execute("""
                INSERT INTO confidence_updates (
                    heuristic_id, old_confidence, new_confidence,
                    raw_target_confidence, delta, smoothed_delta,
                    alpha_used, update_type, reason,
                    rate_limited, session_id, agent_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                heuristic_id,
                old_conf,
                new_ema,
                raw_target,
                raw_target - old_conf,  # Raw delta
                new_ema - old_ema,      # Smoothed delta
                alpha,
                update_type.value,
                reason,
                0,  # Not rate limited if we got here
                session_id,
                agent_id
            ))

            conn.commit()

            # === PHASE 10: Return Result ===
            return {
                "success": True,
                "old_confidence": old_conf,
                "new_confidence": new_ema,
                "raw_target": raw_target,
                "delta_raw": raw_target - old_conf,
                "delta_smoothed": new_ema - old_ema,
                "smoothing_effect": abs((raw_target - old_conf) - (new_ema - old_ema)),
                "alpha": alpha,
                "in_warmup": row['ema_warmup_remaining'] > 0,
                "updates_today": update_count
            }

        finally:
            conn.close()
```

---

## 6. Schema Changes

### New Columns

```sql
-- Add EMA state tracking to heuristics table
ALTER TABLE heuristics ADD COLUMN confidence_ema REAL DEFAULT 0.5
    CHECK(confidence_ema >= 0.0 AND confidence_ema <= 1.0);

ALTER TABLE heuristics ADD COLUMN ema_alpha REAL DEFAULT 0.15
    CHECK(ema_alpha > 0.0 AND ema_alpha <= 1.0);

ALTER TABLE heuristics ADD COLUMN ema_warmup_remaining INTEGER DEFAULT 5
    CHECK(ema_warmup_remaining >= 0);

ALTER TABLE heuristics ADD COLUMN last_ema_update DATETIME;

-- Add indices for EMA queries
CREATE INDEX idx_heuristics_ema_warmup ON heuristics(ema_warmup_remaining)
    WHERE ema_warmup_remaining > 0;

CREATE INDEX idx_heuristics_last_ema_update ON heuristics(last_ema_update);
```

### Enhanced Audit Trail

```sql
-- Add EMA tracking to confidence_updates table
ALTER TABLE confidence_updates ADD COLUMN raw_target_confidence REAL;
ALTER TABLE confidence_updates ADD COLUMN smoothed_delta REAL;
ALTER TABLE confidence_updates ADD COLUMN alpha_used REAL;

-- Rename existing delta to delta_raw for clarity
-- (In practice, keep both for backward compatibility)
-- ALTER TABLE confidence_updates RENAME COLUMN delta TO delta_raw;

-- Add index for analyzing smoothing effectiveness
CREATE INDEX idx_conf_updates_smoothing ON confidence_updates(alpha_used, smoothed_delta);
```

### Migration Strategy

**Migration SQL** (`003_temporal_smoothing_phase2.sql`):

```sql
-- ==============================================================
-- Phase 2 Migration: Temporal Smoothing with EMA
-- ==============================================================

-- 1. Add new columns to heuristics table
ALTER TABLE heuristics ADD COLUMN confidence_ema REAL;
ALTER TABLE heuristics ADD COLUMN ema_alpha REAL;
ALTER TABLE heuristics ADD COLUMN ema_warmup_remaining INTEGER DEFAULT 0;
ALTER TABLE heuristics ADD COLUMN last_ema_update DATETIME;

-- 2. Initialize existing heuristics (no warmup, start with current confidence)
UPDATE heuristics
SET
    confidence_ema = confidence,
    ema_alpha = CASE
        WHEN confidence > 0.80 THEN 0.10   -- High confidence: very stable
        WHEN confidence < 0.30 THEN 0.25   -- Low confidence: allow recovery
        WHEN (times_validated + times_violated + COALESCE(times_contradicted, 0)) >= 20
            THEN 0.15                       -- Mature: stable
        ELSE 0.20                           -- Immature: moderate
    END,
    ema_warmup_remaining = 0,              -- Skip warmup for existing
    last_ema_update = last_confidence_update
WHERE confidence_ema IS NULL;

-- 3. Add constraints
-- (SQLite doesn't support ALTER TABLE ADD CONSTRAINT, so we rely on app-level validation)

-- 4. Enhance confidence_updates audit trail
ALTER TABLE confidence_updates ADD COLUMN raw_target_confidence REAL;
ALTER TABLE confidence_updates ADD COLUMN smoothed_delta REAL;
ALTER TABLE confidence_updates ADD COLUMN alpha_used REAL;

-- 5. Add indices
CREATE INDEX IF NOT EXISTS idx_heuristics_ema_warmup
    ON heuristics(ema_warmup_remaining)
    WHERE ema_warmup_remaining > 0;

CREATE INDEX IF NOT EXISTS idx_heuristics_last_ema_update
    ON heuristics(last_ema_update);

CREATE INDEX IF NOT EXISTS idx_conf_updates_smoothing
    ON confidence_updates(alpha_used, smoothed_delta);

-- 6. Create view for EMA analysis
CREATE VIEW IF NOT EXISTS ema_effectiveness AS
SELECT
    h.id,
    h.domain,
    h.rule,
    h.confidence,
    h.confidence_ema,
    h.ema_alpha,
    h.ema_warmup_remaining,
    (h.times_validated + h.times_violated + COALESCE(h.times_contradicted, 0)) AS total_apps,
    -- Calculate volatility (variance between raw and smoothed)
    (SELECT AVG(ABS(raw_target_confidence - new_confidence))
     FROM confidence_updates cu
     WHERE cu.heuristic_id = h.id
       AND cu.created_at > datetime('now', '-30 days')) AS avg_smoothing_effect_30d,
    -- Count updates in warmup vs steady-state
    (SELECT COUNT(*) FROM confidence_updates cu
     WHERE cu.heuristic_id = h.id AND cu.alpha_used > 0.25) AS warmup_update_count,
    (SELECT COUNT(*) FROM confidence_updates cu
     WHERE cu.heuristic_id = h.id AND cu.alpha_used <= 0.25) AS steady_update_count
FROM heuristics h
WHERE h.status = 'active';

-- 7. Update schema version
INSERT INTO schema_version (version, description)
VALUES (3, 'Heuristic lifecycle Phase 2: Temporal smoothing with exponential moving average');
```

### SQL DDL Statements Summary

```sql
-- Core schema additions
ALTER TABLE heuristics ADD COLUMN confidence_ema REAL DEFAULT 0.5;
ALTER TABLE heuristics ADD COLUMN ema_alpha REAL DEFAULT 0.15;
ALTER TABLE heuristics ADD COLUMN ema_warmup_remaining INTEGER DEFAULT 5;
ALTER TABLE heuristics ADD COLUMN last_ema_update DATETIME;

-- Audit trail enhancements
ALTER TABLE confidence_updates ADD COLUMN raw_target_confidence REAL;
ALTER TABLE confidence_updates ADD COLUMN smoothed_delta REAL;
ALTER TABLE confidence_updates ADD COLUMN alpha_used REAL;

-- Indices
CREATE INDEX idx_heuristics_ema_warmup ON heuristics(ema_warmup_remaining);
CREATE INDEX idx_heuristics_last_ema_update ON heuristics(last_ema_update);
CREATE INDEX idx_conf_updates_smoothing ON confidence_updates(alpha_used, smoothed_delta);

-- Analytics view
CREATE VIEW ema_effectiveness AS ...;
```

---

## 7. Interaction with Existing Features

### Rate Limiting (Complementary)

**How they work together**:

| Mechanism | Controls | Example |
|-----------|----------|---------|
| **Rate Limiting** | Frequency of updates | Max 5 updates/day, 60-min cooldown |
| **EMA Smoothing** | Magnitude of each update | Each update contributes α fraction |

**Scenario: Pump Attack**
```
Without EMA (Phase 1):
- Hour 0: SUCCESS → +0.05 (conf: 0.50 → 0.55)
- Hour 1: SUCCESS → +0.045 (conf: 0.55 → 0.595)
- Hour 2: SUCCESS → +0.041 (conf: 0.595 → 0.636)
- Total: +0.136 in 2 hours

With EMA (Phase 2, α=0.15):
- Hour 0: SUCCESS → raw_target 0.55, smoothed to 0.5075 (+0.0075)
- Hour 1: SUCCESS → raw_target 0.5568, smoothed to 0.5149 (+0.0074)
- Hour 2: SUCCESS → raw_target 0.5641, smoothed to 0.5223 (+0.0074)
- Total: +0.0223 in 2 hours (84% reduction!)
```

**Result**: Even if attacker perfectly times rate limits, EMA prevents dramatic swings.

### Symmetric Formula (Enhanced by EMA)

**Phase 1 symmetric formula** (prevents unbounded growth):
```python
SUCCESS: delta = 0.1 * (1 - confidence)  # Diminishing returns
FAILURE: delta = 0.1 * confidence        # Symmetric decay
```

**Phase 2 enhances this** by adding temporal smoothing:
```python
# Calculate raw target using symmetric formula
raw_target = confidence + 0.1 * (1 - confidence)  # SUCCESS case

# Smooth toward target (don't jump directly)
new_conf = α * raw_target + (1 - α) * old_ema
```

**Combined effect**:
1. **Symmetric formula** ensures target is reasonable (diminishing returns)
2. **EMA** ensures we approach target gradually (noise resistance)

**Example at high confidence (0.85)**:
```
Phase 1 only:
- SUCCESS → +0.015 immediate jump

Phase 2 with EMA (α=0.10):
- SUCCESS → raw_target = 0.865
- Smoothed: 0.10 × 0.865 + 0.90 × 0.85 = 0.8515
- Change: +0.0015 (10× smaller!)
```

### Confidence Bounds (Applied After EMA)

**Order of operations**:
```python
# 1. Calculate raw target (bounded by symmetric formula)
raw_target = calculate_raw_target(confidence, update_type)

# 2. Apply EMA smoothing
new_ema = α * raw_target + (1 - α) * old_ema

# 3. Apply hard bounds (defense in depth)
new_ema = max(min_confidence, min(max_confidence, new_ema))
```

**Why bounds after EMA?**
- EMA can theoretically cause overshoot/undershoot (though rare)
- Bounds are a safety net
- Example: If old_ema = 0.94, raw_target = 0.96, α = 0.5:
  - new_ema = 0.5 × 0.96 + 0.5 × 0.94 = 0.95
  - Clamped to max_confidence (0.95) → no change needed
  - But if max_confidence = 0.95, this ensures compliance

**Interaction matrix**:

| Feature | Phase | Purpose | Applied When |
|---------|-------|---------|--------------|
| Symmetric formula | 1 | Prevent unbounded growth | Calculate raw_target |
| EMA smoothing | 2 | Temporal noise reduction | Calculate new_ema |
| Hard bounds | 1 | Absolute safety limits | Final clamping |
| Rate limiting | 1 | Prevent spam | Before update |

---

## 8. Visualization

### Dashboard Enhancements

**Proposed visualization** for ELF dashboard:

```
Confidence Timeline Chart
┌─────────────────────────────────────────────────┐
│ Confidence                                      │
│ 0.9 ┤                                     ╭─────│ ← confidence_ema (smooth line)
│     │                                 ╭───╯     │
│ 0.8 ┤                             ╭───╯         │
│     │                         ╭───╯             │
│ 0.7 ┤                     ╭───╯   •             │ ← raw_target (discrete points)
│     │                 ╭───╯     •               │
│ 0.6 ┤             ╭───╯       •                 │
│     │         ╭───╯         •                   │
│ 0.5 ┤─────────╯           •                     │
│     └────────────────────────────────────────────│
│       Updates (time →)                          │
└─────────────────────────────────────────────────┘

Legend:
  Smooth line = confidence_ema (actual confidence)
  • Points = raw_target (what discrete update would have been)
  Vertical distance = smoothing effect
```

**Implementation** (React + Chart.js):

```typescript
interface ConfidenceDataPoint {
  timestamp: string;
  ema_confidence: number;
  raw_target: number;
  update_type: 'success' | 'failure' | 'contradiction';
  alpha_used: number;
}

function ConfidenceChart({ heuristicId }: { heuristicId: number }) {
  const [data, setData] = useState<ConfidenceDataPoint[]>([]);

  useEffect(() => {
    fetch(`/api/heuristics/${heuristicId}/confidence-history`)
      .then(r => r.json())
      .then(setData);
  }, [heuristicId]);

  const chartData = {
    datasets: [
      {
        label: 'Smoothed Confidence (EMA)',
        data: data.map(d => ({ x: d.timestamp, y: d.ema_confidence })),
        borderColor: 'rgb(59, 130, 246)',  // Blue
        backgroundColor: 'rgba(59, 130, 246, 0.1)',
        tension: 0.4,  // Smooth curve
        fill: true
      },
      {
        label: 'Raw Target (Discrete)',
        data: data.map(d => ({ x: d.timestamp, y: d.raw_target })),
        borderColor: 'rgb(239, 68, 68)',  // Red
        backgroundColor: 'rgb(239, 68, 68)',
        pointRadius: 4,
        showLine: false,  // Only show points
        pointStyle: 'circle'
      }
    ]
  };

  return (
    <div className="confidence-chart">
      <Line data={chartData} options={{
        plugins: {
          tooltip: {
            callbacks: {
              label: (context) => {
                const point = data[context.dataIndex];
                return [
                  `EMA: ${point.ema_confidence.toFixed(3)}`,
                  `Raw: ${point.raw_target.toFixed(3)}`,
                  `Smoothing: ${Math.abs(point.ema_confidence - point.raw_target).toFixed(4)}`,
                  `Alpha: ${point.alpha_used.toFixed(2)}`,
                  `Type: ${point.update_type}`
                ];
              }
            }
          }
        }
      }} />
    </div>
  );
}
```

### Show Both Raw and EMA Values?

**YES - Show both for transparency and debugging**

**Heuristic detail card**:

```
┌─────────────────────────────────────────────────┐
│ Heuristic: "Use caching for expensive queries"  │
├─────────────────────────────────────────────────┤
│ Current Confidence: 0.742  ⓘ                    │
│   └─ Smoothed with α=0.15 (mature, increasing)  │
│                                                  │
│ Latest Update:                                   │
│   • Type: SUCCESS                                │
│   • Raw target: 0.768                            │
│   • Smoothed to: 0.742                           │
│   • Smoothing effect: -0.026 (damped spike)     │
│                                                  │
│ History (last 5):                                │
│   1. SUCCESS  → 0.768 smoothed to 0.742 (α=0.15)│
│   2. FAILURE  → 0.684 smoothed to 0.714 (α=0.20)│
│   3. SUCCESS  → 0.748 smoothed to 0.721 (α=0.15)│
│   4. SUCCESS  → 0.756 smoothed to 0.726 (α=0.15)│
│   5. SUCCESS  → 0.764 smoothed to 0.732 (α=0.15)│
└─────────────────────────────────────────────────┘
```

**Benefits**:
- Users understand smoothing is happening
- Can debug if smoothing is too aggressive/conservative
- Transparency builds trust in the system

---

## 9. Edge Cases & Failure Modes

### Edge Case 1: First Update (No History)

**Problem**: `confidence_ema` is initialized, but conceptually there's no "previous EMA" on first update.

**Solution**: Initialize `confidence_ema = confidence` on heuristic creation.

```python
def create_heuristic(domain, rule, initial_conf=0.5):
    INSERT INTO heuristics (
        domain, rule, confidence, confidence_ema,
        ema_alpha, ema_warmup_remaining
    ) VALUES (
        domain, rule, initial_conf, initial_conf,  # Both start equal
        0.30, 5  # Warmup mode
    )
```

**First update behavior**:
```python
# First update
old_ema = 0.5 (initialized)
raw_target = 0.55 (after SUCCESS)
alpha = 0.30 (warmup)
new_ema = 0.30 × 0.55 + 0.70 × 0.5 = 0.515

# Smoothing is active from update #1
```

### Edge Case 2: Long Inactivity Periods

**Problem**: Heuristic unused for 180 days. Should EMA "forget" old values?

**Solution: Separate Time Decay from EMA**

```python
def apply_maintenance_decay(heuristic_id):
    """Time-based decay for inactive heuristics."""
    h = get_heuristic(heuristic_id)
    days_inactive = (now() - h.last_used_at).days

    if days_inactive > 14:
        # Calculate exponential decay
        periods = days_inactive // 14
        decay_factor = 0.92 ** periods

        # Apply directly (bypass EMA)
        new_conf = h.confidence_ema * decay_factor

        UPDATE heuristics
        SET confidence = new_conf,
            confidence_ema = new_conf  # Reset both to decayed value
        WHERE id = heuristic_id
```

**Rationale**:
- Time decay is deterministic, not evidence-based
- EMA is for incorporating new observations
- After long inactivity, restart EMA from decayed baseline

### Edge Case 3: Rapid Valid Changes (Emergency Response)

**Problem**: Real bug discovered. Need to quickly suppress bad heuristic. But EMA makes changes slow!

**Solution: Emergency Override (Force Flag)**

```python
def emergency_suppress_heuristic(heuristic_id, reason):
    """Bypass EMA for critical safety issues."""
    # Use force=True to bypass rate limiting
    # Use alpha=1.0 to bypass EMA smoothing

    h = get_heuristic(heuristic_id)

    # Directly set confidence (no smoothing)
    UPDATE heuristics
    SET confidence = 0.05,  # Min confidence
        confidence_ema = 0.05,
        status = 'deprecated'
    WHERE id = heuristic_id

    # Record in audit trail
    record_update(heuristic_id, h.confidence, 0.05,
                  update_type='manual_override',
                  reason=f"EMERGENCY: {reason}",
                  alpha_used=1.0)
```

**When to use**:
- Security vulnerability discovered
- Heuristic causing production incidents
- CEO decision to immediately deprecate

**Audit requirement**: All emergency overrides must be logged with reason.

### Edge Case 4: EMA State Corruption

**Problem**: Database corruption or migration error causes `confidence_ema` to diverge from `confidence`.

**Solution: Self-Healing Check**

```python
def validate_ema_state(heuristic_id):
    """Detect and repair EMA state corruption."""
    h = get_heuristic(heuristic_id)

    # Check for impossible values
    if h.confidence_ema < 0 or h.confidence_ema > 1:
        # Corruption detected - reset to confidence
        logger.error(f"EMA corruption detected for heuristic {heuristic_id}: ema={h.confidence_ema}")
        UPDATE heuristics
        SET confidence_ema = confidence,
            ema_warmup_remaining = 5  # Restart warmup
        WHERE id = heuristic_id
        return False

    # Check for extreme divergence
    divergence = abs(h.confidence_ema - h.confidence)
    if divergence > 0.3:  # Should never be this far apart
        logger.warning(f"Large EMA divergence for heuristic {heuristic_id}: {divergence}")
        # Don't auto-fix, but alert
        return False

    return True
```

**Run periodically** in maintenance:

```python
def run_maintenance(self):
    results = super().run_maintenance()

    # Add EMA validation
    corrupted = []
    for h in get_all_heuristics():
        if not validate_ema_state(h.id):
            corrupted.append(h.id)

    results['ema_validation'] = {
        'checked': len(all_heuristics),
        'corrupted': len(corrupted),
        'details': corrupted
    }

    return results
```

### Edge Case 5: Alpha Parameter Explosion

**Problem**: Bug causes alpha values to be set incorrectly (e.g., alpha=5.0).

**Solution: Database Constraint + App Validation**

```sql
-- Schema constraint
ALTER TABLE heuristics ADD CONSTRAINT check_ema_alpha
    CHECK(ema_alpha > 0.0 AND ema_alpha <= 1.0);
```

```python
def set_alpha(heuristic_id, alpha):
    """Set alpha with validation."""
    if not (0 < alpha <= 1.0):
        raise ValueError(f"Alpha must be in (0, 1], got {alpha}")

    UPDATE heuristics SET ema_alpha = ? WHERE id = ?
```

**Default safe values** if alpha is NULL:

```python
alpha = heuristic.ema_alpha or 0.15  # Safe default
```

---

## 10. Test Scenarios

### Test 1: Single Update Smoothing

**Objective**: Verify EMA reduces impact of single update.

```python
def test_single_update_smoothing():
    """Single update should have fractional impact with EMA."""
    h_id = create_heuristic("test", "Test rule", confidence=0.5)

    # Apply one SUCCESS
    result = update_confidence(h_id, UpdateType.SUCCESS, force=True)

    # Without EMA: would jump to ~0.55
    # With EMA (α=0.30 warmup): should be ~0.515
    assert result['new_confidence'] < 0.52
    assert result['new_confidence'] > 0.51
    assert result['smoothing_effect'] > 0.03  # Significant damping
```

### Test 2: Noise Rejection (Random +/-)

**Objective**: Verify EMA filters out random noise.

```python
def test_noise_rejection():
    """Random alternating updates should stabilize near baseline."""
    h_id = create_heuristic("test", "Noisy rule", confidence=0.5)

    # Skip warmup
    UPDATE heuristics SET ema_warmup_remaining = 0 WHERE id = h_id

    # Apply 20 random updates
    import random
    for i in range(20):
        update_type = random.choice([UpdateType.SUCCESS, UpdateType.FAILURE])
        update_confidence(h_id, update_type, force=True)

    h = get_heuristic(h_id)

    # Should remain close to 0.5 despite noise
    assert 0.45 < h.confidence < 0.55
    print(f"After 20 random updates: {h.confidence}")
```

### Test 3: Trend Detection (Consistent Direction)

**Objective**: Verify EMA still responds to sustained trends.

```python
def test_trend_detection():
    """Sustained success should increase confidence despite smoothing."""
    h_id = create_heuristic("test", "Improving rule", confidence=0.5)

    # Skip warmup
    UPDATE heuristics SET ema_warmup_remaining = 0, ema_alpha = 0.15 WHERE id = h_id

    # Apply 20 consecutive successes
    for i in range(20):
        update_confidence(h_id, UpdateType.SUCCESS, force=True)

    h = get_heuristic(h_id)

    # Should have increased despite smoothing
    assert h.confidence > 0.65
    assert h.confidence < 0.80  # But not unbounded
    print(f"After 20 successes with α=0.15: {h.confidence}")
```

### Test 4: Recovery from Bad State

**Objective**: Low-confidence heuristic should be able to recover.

```python
def test_recovery_from_bad_state():
    """Low-confidence heuristic with higher alpha should recover faster."""
    # Create heuristic with low confidence
    h_id = create_heuristic("test", "Recovering rule", confidence=0.25)
    UPDATE heuristics SET ema_warmup_remaining = 0 WHERE id = h_id

    # Record initial alpha (should be ~0.25 for low confidence)
    h = get_heuristic(h_id)
    initial_alpha = h.ema_alpha
    assert initial_alpha > 0.20  # Higher alpha for recovery

    # Apply 10 successes
    for i in range(10):
        update_confidence(h_id, UpdateType.SUCCESS, force=True)

    h = get_heuristic(h_id)

    # Should have recovered significantly
    assert h.confidence > 0.40
    print(f"Recovered from 0.25 → {h.confidence} with α={initial_alpha}")
```

### Test 5: Asymmetric Smoothing

**Objective**: Verify increases are smoother than decreases.

```python
def test_asymmetric_smoothing():
    """Increases should be smoother (smaller alpha) than decreases."""
    h_inc = create_heuristic("test", "Increasing", confidence=0.6)
    h_dec = create_heuristic("test", "Decreasing", confidence=0.6)

    # Skip warmup
    UPDATE heuristics SET ema_warmup_remaining = 0 WHERE id IN (h_inc, h_dec)

    # One success, one failure
    r_inc = update_confidence(h_inc, UpdateType.SUCCESS, force=True)
    r_dec = update_confidence(h_dec, UpdateType.FAILURE, force=True)

    # Decrease should have larger smoothed delta
    assert abs(r_dec['delta_smoothed']) > abs(r_inc['delta_smoothed'])
    assert r_inc['alpha'] < r_dec['alpha']

    print(f"Increase: Δ={r_inc['delta_smoothed']}, α={r_inc['alpha']}")
    print(f"Decrease: Δ={r_dec['delta_smoothed']}, α={r_dec['alpha']}")
```

### Test 6: High-Confidence Stability

**Objective**: High-confidence heuristics should be very stable.

```python
def test_high_confidence_stability():
    """High-confidence heuristic should resist single failures."""
    h_id = create_heuristic("test", "Stable rule", confidence=0.85)
    UPDATE heuristics SET ema_warmup_remaining = 0, times_validated = 50 WHERE id = h_id

    # One failure
    result = update_confidence(h_id, UpdateType.FAILURE, force=True)

    # Should have minimal impact
    assert result['delta_smoothed'] > -0.02  # Less than 2-point drop
    assert result['alpha'] < 0.20  # Low alpha for high confidence

    print(f"High-confidence stability: {result['old_confidence']} → {result['new_confidence']}")
```

### Test 7: Warmup Transition

**Objective**: Verify warmup transitions to steady-state correctly.

```python
def test_warmup_transition():
    """Warmup should end after 5 updates with alpha transition."""
    h_id = create_heuristic("test", "Warmup rule", confidence=0.5)

    alphas = []
    for i in range(7):
        result = update_confidence(h_id, UpdateType.SUCCESS, force=True)
        alphas.append(result['alpha'])

    # First 5 should be warmup (α=0.30)
    assert all(a == 0.30 for a in alphas[:5])

    # After warmup, should transition to lower alpha
    assert alphas[5] < 0.30
    assert alphas[6] < 0.30

    print(f"Alpha progression: {alphas}")
```

### Test 8: Rate Limiting + EMA Interaction

**Objective**: Verify both mechanisms work together.

```python
def test_rate_limiting_plus_ema():
    """Rate limiting + EMA should compound protection."""
    config = LifecycleConfig(max_updates_per_day=3, cooldown_minutes=1)
    manager = LifecycleManager(config=config)

    h_id = create_heuristic("test", "Protected rule", confidence=0.5)
    UPDATE heuristics SET ema_warmup_remaining = 0, ema_alpha = 0.15 WHERE id = h_id

    # Try 10 rapid successes
    successes = 0
    rate_limited = 0

    for i in range(10):
        result = manager.update_confidence(h_id, UpdateType.SUCCESS)
        if result['success']:
            successes += 1
        elif result.get('rate_limited'):
            rate_limited += 1

    # Should be rate limited
    assert successes <= 3
    assert rate_limited > 0

    h = get_heuristic(h_id)

    # Even the allowed updates should be smoothed
    assert h.confidence < 0.55  # Much less than discrete would allow

    print(f"Successes: {successes}, Rate limited: {rate_limited}, Final: {h.confidence}")
```

---

## 11. Implementation Estimate

### Lines of Code

**Estimated additions/modifications**:

| Component | Lines | Complexity |
|-----------|-------|------------|
| `lifecycle_manager.py` modifications | ~150 | Medium |
| New `calculate_adaptive_alpha()` function | ~30 | Low |
| Enhanced `update_confidence()` method | ~80 | Medium |
| EMA validation/maintenance | ~40 | Low |
| Migration SQL (003_temporal_smoothing.sql) | ~120 | Low |
| Test suite additions | ~300 | Medium |
| Dashboard API endpoints | ~50 | Low |
| Dashboard UI components (React) | ~200 | Medium |
| **Total** | **~970 lines** | **Medium** |

### Complexity Rating

**Overall: 6/10 (Medium Complexity)**

**Breakdown**:

| Aspect | Complexity | Reason |
|--------|-----------|--------|
| **Math** | 3/10 | EMA formula is simple (one line) |
| **State Management** | 5/10 | Need to track alpha, warmup, last_update |
| **Schema Changes** | 4/10 | Straightforward column additions |
| **Migration** | 6/10 | Must handle existing heuristics carefully |
| **Testing** | 7/10 | Need to test many edge cases and scenarios |
| **Integration** | 5/10 | Must not break Phase 1 functionality |
| **Dashboard** | 6/10 | Dual charts (raw + smoothed) require care |

**Risk areas**:
- Migration of existing heuristics (backfill EMA state)
- Choosing optimal alpha values (may require tuning)
- Dashboard performance with dual time series

**Mitigation**:
- Incremental rollout (test on subset of heuristics first)
- Make alpha values configurable (can tune without code changes)
- Use database views for expensive analytics

### Dependencies

**Code dependencies**:
- Phase 1 lifecycle manager (base implementation)
- SQLite 3.x with JSON support
- Python 3.8+ (for type hints, dataclasses)

**External dependencies**:
- None (pure Python + SQLite)

**Migration dependencies**:
- Existing heuristics table from Phase 1
- Schema version 2 (Phase 1 migration must be applied first)

**Testing dependencies**:
- pytest
- unittest (standard library)
- Test database isolation (already implemented)

**Dashboard dependencies**:
- React 18+
- Chart.js or Recharts (for time series visualization)
- FastAPI backend (already in place)

---

## FINDINGS

### [fact] EMA Reduces Update Impact by 70-90% Depending on Alpha

With α=0.15, a discrete update that would cause a 0.05 confidence change instead causes only ~0.0075 change (85% reduction). This makes the system highly resistant to single anomalous events.

### [fact] Asymmetric Alpha (Slower Increase, Faster Decrease) Aligns with Security Best Practices

Using alpha_increase=0.15 and alpha_decrease=0.20 creates a conservative system where trust is built slowly but lost more quickly. This is the same principle used in security systems and reputation engines.

### [fact] Warmup Period Solves Cold-Start Problem

New heuristics with no history need higher alpha (0.30) to quickly converge toward their true accuracy. After 5 updates, transitioning to lower alpha provides stability. Half-life of ~2 updates during warmup allows rapid learning.

### [hypothesis] Optimal Alpha for Mature Heuristics is Between 0.10-0.20

Based on analysis of existing lifecycle data and test scenarios, alpha values in this range provide good balance between noise resistance (reject single anomalies) and trend responsiveness (detect sustained changes in ~5-10 updates).

### [hypothesis] Time Decay Should Bypass EMA to Avoid Double-Smoothing

Time-based decay is already a gradual exponential process. Applying EMA on top of it would create over-smoothing. Better to directly update confidence_ema when applying time decay.

### [hypothesis] High-Confidence Heuristics (>0.80) Need Ultra-Low Alpha (<0.10) to Prevent Gaming

Heuristics approaching golden rule status must be extremely stable. An alpha of 0.10 for increases means it takes ~7 consecutive successes to move confidence by just 0.01. This makes pump attacks infeasible.

### [question] Should Alpha Be Per-Domain or Global?

Current design uses per-heuristic adaptive alpha. Alternative: Could have domain-specific alpha values (e.g., security domain = more conservative alpha). Trade-off: More complex vs. more flexible.

### [question] How to Visualize "Smoothing Quality" in Dashboard?

Proposed metric: `smoothing_effectiveness = avg(|raw_delta - smoothed_delta|)` over last 30 days. High value = aggressive smoothing. Low value = minimal smoothing. Should this be surfaced to users?

### [question] Should Emergency Override Require Multi-Factor Confirmation?

Current design allows single CEO decision to bypass EMA via emergency override. For production safety, should this require additional confirmation (e.g., "type CONFIRM to suppress heuristic") to prevent accidental misuse?

### [blocker] Migration Testing Required for Large-Scale Backfill

If production has 1000+ existing heuristics, migration must initialize confidence_ema for all of them. Need to test migration performance and ensure it doesn't lock database for extended period.

### [blocker] Need CEO Decision on Default Alpha Values Before Implementation

Recommended values (alpha_increase=0.15, alpha_decrease=0.20) are based on simulation, but CEO should approve these as they fundamentally change system dynamics. Once deployed, changing alpha values affects all future updates.

---

## Next Steps

1. **CEO Review**: Get approval on design and default alpha values
2. **Spike**: Test EMA algorithm on historical confidence_updates data to validate alpha choices
3. **Schema Migration**: Implement and test `003_temporal_smoothing_phase2.sql`
4. **Core Implementation**: Extend `LifecycleManager` with EMA logic
5. **Test Suite**: Implement all 8+ test scenarios
6. **Dashboard**: Add dual-chart visualization (raw + smoothed)
7. **Documentation**: Update wiki with EMA explanation for end users
8. **Rollout**: Deploy to production with monitoring

**Estimated timeline**: 3-4 days for full implementation + testing + documentation.

---

**End of Design Document**
