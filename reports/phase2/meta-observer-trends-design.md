# Meta-Observer Rolling Window Trend Analysis - Phase 2 Design

**Agent:** Agent 4 (Ultrathink Swarm Phase 2)
**Date:** 2025-12-12
**Status:** Design Document
**Complexity:** High
**Implementation Estimate:** 400-600 LOC

---

## 1. PROBLEM STATEMENT

### 1.1 Why Snapshots Are Insufficient

The current `get_lifecycle_stats()` method (lifecycle_manager.py:792-833) provides **point-in-time snapshots**:

```python
# Current implementation
def get_lifecycle_stats(self) -> Dict[str, Any]:
    stats = {}
    # Returns current status distribution
    # Returns current domain health
    # Returns at-risk heuristics RIGHT NOW
    # Returns recent updates (7 days)
```

**Critical Limitations:**

1. **No Historical Context:** Cannot tell if avg_confidence=0.65 is improving or declining
2. **Cannot Detect Trends:** Is contradiction rate spiking or stable?
3. **Misses Velocity:** A domain going from 0.8→0.7→0.6→0.5 looks fine at each snapshot
4. **No Anomaly Detection:** Cannot identify "this week is unusual compared to last month"
5. **Alert Fatigue Risk:** Threshold alerts fire on temporary spikes (false positives)

### 1.2 Examples of Missed Trends

**Scenario 1: Gradual Confidence Erosion**
```
Nov 1:  avg_confidence = 0.75 (snapshot: "healthy")
Nov 15: avg_confidence = 0.68 (snapshot: "healthy")
Dec 1:  avg_confidence = 0.61 (snapshot: "healthy")
Dec 15: avg_confidence = 0.54 (snapshot: "WARNING")

Problem: Each snapshot looked fine, but 30-day trend shows -28% decline
```

**Scenario 2: Contradiction Rate Spike**
```
Baseline: 5% contradiction rate (normal for this system)
Today: 15% contradiction rate

Snapshot alert: "Contradiction rate high!"
Reality: This is 3x normal, not just "high" in absolute terms
```

**Scenario 3: Domain Activity Collapse**
```
Domain "api" normally gets 50 updates/week
Last 7 days: 3 updates

Snapshot: "Domain has 3 heuristics with avg_confidence 0.72" (looks fine)
Trend: Domain activity dropped 94% - domain is dying
```

### 1.3 Gaming via Snapshot Timing

**Attack Vector:**
An adversarial agent could:
1. Pump heuristic confidence before scheduled snapshot
2. Let it decay after snapshot
3. Repeat to maintain artificially high snapshot metrics

**Defense:**
Rolling windows capture behavior **between** snapshots, making timing manipulation ineffective.

---

## 2. ROLLING WINDOW FUNDAMENTALS

### 2.1 Window Definitions

| Window Size | Use Case | Granularity | Retention |
|-------------|----------|-------------|-----------|
| **1 hour** | Real-time alerting, anomaly detection | 1-minute bins | 72 hours |
| **24 hour** | Daily health checks, detect spikes | 10-minute bins | 30 days |
| **7 day** | Weekly trends, pattern detection | 1-hour bins | 90 days |
| **30 day** | Long-term health, seasonality | 6-hour bins | 1 year |

### 2.2 Sliding vs. Tumbling Windows

**Sliding Windows (RECOMMENDED):**
```
Continuous movement, overlapping data points
Example: Last 24 hours, recalculated every minute

Timeline:  [----24h----]
              [----24h----]
                 [----24h----]

Advantages:
+ Smooth trends
+ Early anomaly detection
+ No boundary artifacts
```

**Tumbling Windows (for aggregation only):**
```
Non-overlapping, discrete chunks
Example: Daily rollups (00:00-23:59)

Day 1: [----24h----]
Day 2:             [----24h----]

Use for:
+ Storage efficiency (pre-aggregate to hourly/daily)
+ Historical queries (show me "last Wednesday")
```

**Hybrid Approach (DESIGN CHOICE):**
- **Sliding windows** for live trend calculation
- **Tumbling windows** for storage aggregation

### 2.3 Storage Requirements

**Granular Data (observations table):**
```
Metric sample every 5 minutes:
- 1 hour window: 12 samples × 8 metrics = 96 values
- 24 hour window: 288 samples × 8 metrics = 2,304 values
- 7 day window: 2,016 samples × 8 metrics = 16,128 values

Retention: 90 days
Total samples: 90 × 288 × 8 = 207,360 samples
Storage: ~2-3 MB (with indexes)
```

**Aggregated Data (rollups table):**
```
Hourly rollups: 24/day × 90 days = 2,160 rows
Daily rollups: 90 rows
Weekly rollups: 12 rows

Storage: <100 KB
```

**Total Storage: ~3 MB (negligible)**

### 2.4 Query Patterns

**Pattern 1: Current Window Value**
```sql
-- Get avg_confidence for last 24 hours
SELECT AVG(value) as avg_confidence_24h
FROM metric_observations
WHERE metric_name = 'avg_confidence'
  AND observed_at > datetime('now', '-24 hours');
```

**Pattern 2: Trend Detection (slope)**
```sql
-- Calculate trend direction over 7 days
WITH numbered AS (
    SELECT
        value,
        ROW_NUMBER() OVER (ORDER BY observed_at) as x,
        observed_at
    FROM metric_observations
    WHERE metric_name = 'avg_confidence'
      AND observed_at > datetime('now', '-7 days')
)
SELECT
    -- Linear regression: slope = (n*Σxy - ΣxΣy) / (n*Σx² - (Σx)²)
    (COUNT(*) * SUM(x * value) - SUM(x) * SUM(value)) /
    (COUNT(*) * SUM(x * x) - SUM(x) * SUM(x)) as slope
FROM numbered;
```

**Pattern 3: Anomaly Detection**
```sql
-- Detect if current value is outside normal range
WITH baseline AS (
    SELECT
        AVG(value) as mean,
        -- Use percentile for robust std estimation
        (MAX(value) - MIN(value)) / 6.0 as robust_std
    FROM metric_observations
    WHERE metric_name = 'contradiction_rate'
      AND observed_at BETWEEN datetime('now', '-30 days')
                          AND datetime('now', '-7 days')
),
current AS (
    SELECT AVG(value) as current_value
    FROM metric_observations
    WHERE metric_name = 'contradiction_rate'
      AND observed_at > datetime('now', '-1 hour')
)
SELECT
    current.current_value,
    baseline.mean,
    baseline.robust_std,
    ABS(current.current_value - baseline.mean) / baseline.robust_std as z_score,
    CASE
        WHEN ABS(current.current_value - baseline.mean) > 3 * baseline.robust_std
        THEN 1 ELSE 0
    END as is_anomaly
FROM current, baseline;
```

---

## 3. METRICS TO TRACK

### 3.1 Core Metrics (with rolling windows)

| Metric | Description | Window Sizes | Alert Condition |
|--------|-------------|--------------|-----------------|
| **avg_confidence** | System-wide average confidence | 1h, 24h, 7d, 30d | 7d slope < -0.02/day for 3+ days |
| **avg_confidence_by_domain** | Per-domain average | 24h, 7d, 30d | Domain 7d slope < -0.05/day |
| **contradiction_rate** | Contradictions / total applications | 1h, 24h, 7d | 24h rate > 2× baseline |
| **promotion_rate** | Heuristics promoted / total | 7d, 30d | 30d rate < 0.01 (stagnation) |
| **dormancy_rate** | Active → dormant transitions | 24h, 7d, 30d | 7d rate > 2× baseline |
| **revival_rate** | Dormant → active transitions | 7d, 30d | 30d rate < baseline (no recovery) |
| **churn_rate** | (New + evicted) / total | 7d, 30d | 7d rate > 0.5 (unstable) |
| **validation_velocity** | Validations per day | 7d, 30d | 7d velocity < 0.5× baseline |

### 3.2 Derived Metrics

**Confidence Velocity (rate of change):**
```python
# Change in avg_confidence per day
velocity = (current_24h_avg - previous_24h_avg) / 1  # per day
```

**Domain Health Score (composite):**
```python
health_score = (
    0.4 * avg_confidence +
    0.3 * (1 - contradiction_rate) +
    0.2 * activity_score +
    0.1 * stability_score
)
```

**Activity Score:**
```python
# Normalized by domain baseline
activity_score = min(1.0, current_7d_validations / baseline_7d_validations)
```

**Stability Score:**
```python
# Inverse of churn rate
stability_score = max(0, 1 - churn_rate)
```

### 3.3 Observation Collection

**Trigger Points:**
1. **Scheduled (cron-like):** Every 5 minutes via `run_maintenance()`
2. **Event-driven:** After confidence update, after domain enforcement
3. **On-demand:** When dashboard queries stats

**Collection Method:**
```python
def collect_observations():
    """Snapshot current metrics into time-series table."""
    timestamp = datetime.now()

    # System-wide metrics
    record_observation('avg_confidence', calc_avg_confidence(), timestamp)
    record_observation('contradiction_rate', calc_contradiction_rate(), timestamp)
    record_observation('validation_velocity', calc_validation_velocity(), timestamp)

    # Per-domain metrics
    for domain in get_active_domains():
        record_observation(
            f'domain_{domain}_confidence',
            calc_domain_confidence(domain),
            timestamp
        )
```

---

## 4. TREND DETECTION ALGORITHMS

### 4.1 Linear Regression (Trend Direction)

**Purpose:** Detect if metric is increasing/decreasing over time

**Algorithm:**
```python
def calculate_trend(metric_name: str, window_hours: int) -> Dict:
    """
    Calculate linear trend (slope) over window.

    Returns:
        {
            'slope': float,  # Change per hour
            'direction': 'increasing' | 'stable' | 'decreasing',
            'r_squared': float,  # Goodness of fit
            'confidence': 'high' | 'medium' | 'low'
        }
    """
    observations = get_observations(metric_name, window_hours)

    if len(observations) < 10:
        return {'confidence': 'low', 'reason': 'insufficient_data'}

    # Convert to numpy arrays
    x = np.arange(len(observations))  # Time index
    y = np.array([o.value for o in observations])

    # Linear regression: y = mx + b
    slope, intercept, r_value, p_value, std_err = scipy.stats.linregress(x, y)

    # Determine direction (with significance threshold)
    if abs(slope) < std_err * 2:  # Not statistically significant
        direction = 'stable'
    elif slope > 0:
        direction = 'increasing'
    else:
        direction = 'decreasing'

    return {
        'slope': slope,
        'direction': direction,
        'r_squared': r_value ** 2,
        'p_value': p_value,
        'confidence': 'high' if p_value < 0.05 else 'medium' if p_value < 0.1 else 'low'
    }
```

**Interpretation:**
```
slope > 0.01:  Improving rapidly
slope > 0.001: Improving gradually
slope ~ 0:     Stable
slope < -0.001: Declining gradually
slope < -0.01:  Declining rapidly
```

### 4.2 Change Point Detection

**Purpose:** Detect sudden shifts in metric behavior

**Algorithm: CUSUM (Cumulative Sum)**
```python
def detect_change_points(metric_name: str, window_hours: int, threshold: float = 5.0):
    """
    Detect abrupt changes using CUSUM algorithm.

    Args:
        threshold: Sensitivity (lower = more sensitive)

    Returns:
        List of timestamps where changes detected
    """
    observations = get_observations(metric_name, window_hours)

    values = np.array([o.value for o in observations])
    timestamps = [o.observed_at for o in observations]

    # Calculate baseline mean and std
    baseline_mean = np.mean(values[:len(values)//3])  # First third
    baseline_std = np.std(values[:len(values)//3])

    # CUSUM
    cusum_pos = 0
    cusum_neg = 0
    change_points = []

    for i, value in enumerate(values):
        deviation = (value - baseline_mean) / baseline_std

        cusum_pos = max(0, cusum_pos + deviation - 0.5)
        cusum_neg = max(0, cusum_neg - deviation - 0.5)

        if cusum_pos > threshold:
            change_points.append({
                'timestamp': timestamps[i],
                'type': 'upward_shift',
                'magnitude': cusum_pos
            })
            cusum_pos = 0  # Reset

        if cusum_neg > threshold:
            change_points.append({
                'timestamp': timestamps[i],
                'type': 'downward_shift',
                'magnitude': cusum_neg
            })
            cusum_neg = 0  # Reset

    return change_points
```

**Use Cases:**
- Detect when contradiction rate suddenly spikes
- Identify when domain confidence drops abruptly
- Find anomalous periods in system behavior

### 4.3 Anomaly Detection (Statistical Outliers)

**Algorithm: Z-Score with Robust Estimation**
```python
def detect_anomalies(metric_name: str,
                     baseline_window_hours: int = 720,  # 30 days
                     current_window_hours: int = 1,      # Last hour
                     std_threshold: float = 3.0):
    """
    Detect if current window is anomalous vs. baseline.

    Uses robust statistics (median, MAD) instead of mean/std
    to avoid outlier contamination.
    """
    # Baseline (historical normal)
    baseline_obs = get_observations(
        metric_name,
        baseline_window_hours,
        exclude_recent_hours=current_window_hours
    )

    baseline_values = [o.value for o in baseline_obs]

    # Robust statistics
    baseline_median = np.median(baseline_values)
    # MAD = Median Absolute Deviation
    mad = np.median([abs(v - baseline_median) for v in baseline_values])
    # Convert MAD to std-equivalent (for normal distribution)
    baseline_std = mad * 1.4826

    # Current window
    current_obs = get_observations(metric_name, current_window_hours)
    current_value = np.mean([o.value for o in current_obs])

    # Calculate Z-score
    z_score = (current_value - baseline_median) / baseline_std

    is_anomaly = abs(z_score) > std_threshold

    return {
        'current_value': current_value,
        'baseline_median': baseline_median,
        'baseline_std': baseline_std,
        'z_score': z_score,
        'is_anomaly': is_anomaly,
        'severity': 'critical' if abs(z_score) > 4 else
                   'warning' if abs(z_score) > 3 else 'normal'
    }
```

### 4.4 Seasonal Adjustment

**Purpose:** Account for known cyclical patterns (e.g., weekday vs. weekend)

```python
def adjust_for_seasonality(metric_name: str, observations: List):
    """
    Decompose metric into trend + seasonal + residual.

    Uses simple moving average for de-trending.
    """
    # Group by day of week
    by_weekday = defaultdict(list)
    for obs in observations:
        weekday = obs.observed_at.weekday()
        by_weekday[weekday].append(obs.value)

    # Calculate weekday factors (median by weekday / overall median)
    overall_median = np.median([o.value for o in observations])
    weekday_factors = {
        day: np.median(values) / overall_median
        for day, values in by_weekday.items()
    }

    # Adjust observations
    adjusted = []
    for obs in observations:
        factor = weekday_factors[obs.observed_at.weekday()]
        adjusted.append(obs.value / factor)

    return adjusted, weekday_factors
```

**When to Use:**
- If validation activity drops on weekends (expected pattern)
- If certain domains have cyclical activity (e.g., tax domain active in Q1)

---

## 5. ALERT CONDITIONS

### 5.1 Trend-Based Alerts (NOT threshold-based)

**Alert: Sustained Confidence Decline**
```yaml
Condition:
  - 7-day trend slope < -0.02 per day
  - AND trend confidence > medium
  - AND decline persists for 3+ consecutive days

Severity: warning

Message: "System confidence declining -2% per day for 3 days straight.
         Current: 0.65, started at 0.71. Investigate domain health."
```

**Alert: Contradiction Rate Spike**
```yaml
Condition:
  - 24-hour contradiction_rate > 2× 30-day baseline
  - OR z-score > 3.0

Severity: critical

Message: "Contradiction rate spiked to 15% (baseline: 5%).
         3× normal. Check recent heuristic conflicts."
```

**Alert: Domain Stagnation**
```yaml
Condition:
  - Domain validation_velocity < 0.5× baseline for 7+ days
  - AND no new heuristics in 14+ days

Severity: info

Message: "Domain 'api' has 80% drop in activity over 7 days.
         Possible disuse or knowledge saturation."
```

**Alert: Negative Velocity Across Multiple Domains**
```yaml
Condition:
  - 3+ domains with 7-day confidence slope < -0.05
  - Indicates system-wide problem

Severity: critical

Message: "Multi-domain confidence decline detected.
         Domains affected: api, security, caching. System-level issue suspected."
```

### 5.2 Severity Levels

| Severity | Meaning | Response | Escalation |
|----------|---------|----------|------------|
| **info** | FYI, non-urgent | Log to alerts table | None |
| **warning** | Attention needed | Dashboard notification | If persists 7 days → CEO |
| **critical** | Immediate action | Dashboard + console | Immediate CEO inbox |

### 5.3 Alert Deduplication

**Problem:** Trend alerts can fire repeatedly (alert fatigue)

**Solution: Alert State Machine**
```python
class AlertState(Enum):
    NEW = "new"              # First detection
    ACTIVE = "active"        # Still ongoing
    ACKNOWLEDGED = "ack"     # User saw it
    RESOLVED = "resolved"    # Condition cleared
    SUPPRESSED = "suppressed" # User muted

def process_alert(alert_condition):
    """Smart alert handling with state tracking."""
    alert_id = hash(alert_condition)  # Same condition = same ID

    existing_alert = get_alert(alert_id)

    if not existing_alert:
        # New alert
        create_alert(alert_id, state=AlertState.NEW)
        notify_dashboard(alert_id)
    elif existing_alert.state == AlertState.RESOLVED:
        # Re-fire after resolution
        update_alert(alert_id, state=AlertState.NEW)
        notify_dashboard(alert_id, is_recurrence=True)
    elif existing_alert.state == AlertState.SUPPRESSED:
        # User muted, don't notify
        pass
    else:
        # Update last_seen timestamp
        update_alert(alert_id, last_seen=datetime.now())
```

---

## 6. SCHEMA DESIGN

### 6.1 Time-Series Storage Strategy

**Option A: Wide Table (one metric per column)**
```sql
-- Simple but inflexible
CREATE TABLE metric_snapshots (
    id INTEGER PRIMARY KEY,
    observed_at TIMESTAMP,
    avg_confidence REAL,
    contradiction_rate REAL,
    -- ... 20 columns ...
);
```
❌ **Rejected:** Hard to add new metrics, inefficient queries

**Option B: Narrow Table (EAV pattern) ✅ RECOMMENDED**
```sql
-- Flexible, scalable
CREATE TABLE metric_observations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    metric_name TEXT NOT NULL,        -- e.g., 'avg_confidence'
    value REAL NOT NULL,
    observed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    domain TEXT,                      -- NULL for system-wide metrics
    metadata TEXT,                    -- JSON for additional context

    UNIQUE(metric_name, observed_at, domain)
);

CREATE INDEX idx_obs_metric_time ON metric_observations(metric_name, observed_at);
CREATE INDEX idx_obs_domain_time ON metric_observations(domain, observed_at) WHERE domain IS NOT NULL;
```

**Advantages:**
- Easy to add new metrics (no schema change)
- Efficient range queries (indexed by metric_name + time)
- Supports domain-specific metrics

### 6.2 Aggregation Tables (Rollups)

**Hourly Rollups (pre-computed for fast queries)**
```sql
CREATE TABLE metric_hourly_rollups (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    metric_name TEXT NOT NULL,
    hour_start TIMESTAMP NOT NULL,  -- Truncated to hour
    domain TEXT,

    -- Aggregates
    min_value REAL,
    max_value REAL,
    avg_value REAL,
    median_value REAL,
    stddev_value REAL,
    sample_count INTEGER,

    UNIQUE(metric_name, hour_start, domain)
);

CREATE INDEX idx_rollup_metric_hour ON metric_hourly_rollups(metric_name, hour_start);
```

**Daily Rollups (for long-term trends)**
```sql
CREATE TABLE metric_daily_rollups (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    metric_name TEXT NOT NULL,
    date DATE NOT NULL,
    domain TEXT,

    min_value REAL,
    max_value REAL,
    avg_value REAL,
    p50_value REAL,  -- Median
    p95_value REAL,  -- 95th percentile
    sample_count INTEGER,

    UNIQUE(metric_name, date, domain)
);
```

### 6.3 Alerts Table

```sql
CREATE TABLE meta_alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    alert_type TEXT NOT NULL,         -- 'confidence_decline', 'contradiction_spike', etc.
    severity TEXT NOT NULL,           -- 'info' | 'warning' | 'critical'
    state TEXT NOT NULL DEFAULT 'new', -- 'new' | 'active' | 'ack' | 'resolved' | 'suppressed'

    metric_name TEXT,                 -- Which metric triggered
    current_value REAL,
    threshold_value REAL,

    message TEXT NOT NULL,            -- Human-readable description
    context TEXT,                     -- JSON with trend data, affected domains, etc.

    first_seen TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_seen TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    acknowledged_at TIMESTAMP,
    resolved_at TIMESTAMP,

    created_by TEXT DEFAULT 'meta_observer'
);

CREATE INDEX idx_alerts_state ON meta_alerts(state, severity);
CREATE INDEX idx_alerts_metric ON meta_alerts(metric_name, first_seen);
```

### 6.4 Meta-Observer Configuration

```sql
CREATE TABLE meta_observer_config (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    metric_name TEXT UNIQUE NOT NULL,

    -- Alert thresholds (can be auto-tuned)
    threshold REAL,
    threshold_type TEXT,              -- 'absolute' | 'relative' | 'z_score'
    auto_adjust BOOLEAN DEFAULT 1,

    -- Trend detection config
    trend_window_hours INTEGER DEFAULT 168,  -- 7 days
    trend_sensitivity REAL DEFAULT 0.05,     -- Slope threshold

    -- Anomaly detection config
    baseline_window_hours INTEGER DEFAULT 720,  -- 30 days
    z_score_threshold REAL DEFAULT 3.0,

    -- Adjustment history (for self-tuning)
    adjustment_history TEXT,          -- JSON array of past changes
    last_adjusted TIMESTAMP,
    false_positive_count INTEGER DEFAULT 0,
    true_positive_count INTEGER DEFAULT 0,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 6.5 Complete DDL

```sql
-- ============================================================================
-- PHASE 2: META-OBSERVER TREND ANALYSIS SCHEMA
-- ============================================================================

-- Time-series observations (narrow table, flexible)
CREATE TABLE IF NOT EXISTS metric_observations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    metric_name TEXT NOT NULL,
    value REAL NOT NULL,
    observed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    domain TEXT,
    metadata TEXT,

    UNIQUE(metric_name, observed_at, COALESCE(domain, ''))
);

CREATE INDEX IF NOT EXISTS idx_obs_metric_time
    ON metric_observations(metric_name, observed_at DESC);
CREATE INDEX IF NOT EXISTS idx_obs_domain_time
    ON metric_observations(domain, observed_at DESC)
    WHERE domain IS NOT NULL;

-- Hourly aggregations (for fast windowed queries)
CREATE TABLE IF NOT EXISTS metric_hourly_rollups (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    metric_name TEXT NOT NULL,
    hour_start TIMESTAMP NOT NULL,
    domain TEXT,

    min_value REAL,
    max_value REAL,
    avg_value REAL,
    median_value REAL,
    stddev_value REAL,
    sample_count INTEGER,

    UNIQUE(metric_name, hour_start, COALESCE(domain, ''))
);

CREATE INDEX IF NOT EXISTS idx_rollup_metric_hour
    ON metric_hourly_rollups(metric_name, hour_start DESC);

-- Daily aggregations (for long-term trends)
CREATE TABLE IF NOT EXISTS metric_daily_rollups (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    metric_name TEXT NOT NULL,
    date DATE NOT NULL,
    domain TEXT,

    min_value REAL,
    max_value REAL,
    avg_value REAL,
    p50_value REAL,
    p95_value REAL,
    sample_count INTEGER,

    UNIQUE(metric_name, date, COALESCE(domain, ''))
);

CREATE INDEX IF NOT EXISTS idx_daily_metric_date
    ON metric_daily_rollups(metric_name, date DESC);

-- Alerts with state tracking
CREATE TABLE IF NOT EXISTS meta_alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    alert_type TEXT NOT NULL,
    severity TEXT NOT NULL CHECK(severity IN ('info', 'warning', 'critical')),
    state TEXT NOT NULL DEFAULT 'new' CHECK(state IN ('new', 'active', 'ack', 'resolved', 'suppressed')),

    metric_name TEXT,
    current_value REAL,
    threshold_value REAL,

    message TEXT NOT NULL,
    context TEXT,

    first_seen TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_seen TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    acknowledged_at TIMESTAMP,
    resolved_at TIMESTAMP,

    created_by TEXT DEFAULT 'meta_observer'
);

CREATE INDEX IF NOT EXISTS idx_alerts_state
    ON meta_alerts(state, severity, first_seen DESC);
CREATE INDEX IF NOT EXISTS idx_alerts_metric
    ON meta_alerts(metric_name, first_seen DESC);

-- Meta-Observer configuration (self-tuning thresholds)
CREATE TABLE IF NOT EXISTS meta_observer_config (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    metric_name TEXT UNIQUE NOT NULL,

    threshold REAL,
    threshold_type TEXT DEFAULT 'absolute',
    auto_adjust BOOLEAN DEFAULT 1,

    trend_window_hours INTEGER DEFAULT 168,
    trend_sensitivity REAL DEFAULT 0.05,

    baseline_window_hours INTEGER DEFAULT 720,
    z_score_threshold REAL DEFAULT 3.0,

    adjustment_history TEXT,
    last_adjusted TIMESTAMP,
    false_positive_count INTEGER DEFAULT 0,
    true_positive_count INTEGER DEFAULT 0,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Default configurations for core metrics
INSERT OR IGNORE INTO meta_observer_config
    (metric_name, threshold, threshold_type, trend_sensitivity, z_score_threshold)
VALUES
    ('avg_confidence', 0.5, 'absolute', -0.02, 3.0),
    ('contradiction_rate', 0.15, 'absolute', 0.05, 3.0),
    ('validation_velocity', 10.0, 'absolute', -5.0, 2.5),
    ('dormancy_rate', 0.1, 'relative', 0.05, 3.0),
    ('revival_rate', 0.05, 'relative', -0.02, 2.0);
```

---

## 7. SELF-TUNING THRESHOLDS

### 7.1 Learning "Normal" for This System

**Problem:** Hardcoded thresholds don't fit all systems
- System A might normally have 5% contradiction rate
- System B might normally have 15% contradiction rate
- Same threshold would mis-fire on one of them

**Solution: Adaptive Baselines**

```python
def learn_baseline(metric_name: str, learning_period_days: int = 30):
    """
    Calculate baseline statistics from historical data.

    Assumes first 30 days are "normal" (no alerts during bootstrap).
    """
    observations = get_observations_between(
        metric_name,
        start=datetime.now() - timedelta(days=learning_period_days),
        end=datetime.now()
    )

    values = [o.value for o in observations]

    baseline = {
        'mean': np.mean(values),
        'median': np.median(values),
        'std': np.std(values),
        'mad': median_absolute_deviation(values),
        'p95': np.percentile(values, 95),
        'p5': np.percentile(values, 5),
        'learned_at': datetime.now().isoformat()
    }

    # Store in config
    config = get_config(metric_name)
    config.baseline = json.dumps(baseline)
    config.save()

    return baseline
```

### 7.2 False Positive Tracking

**Alert Outcome Recording:**
```python
def record_alert_outcome(alert_id: int, outcome: str, reason: str = ""):
    """
    Track whether alert was true/false positive.

    Args:
        outcome: 'true_positive' | 'false_positive' | 'unclear'
        reason: Human explanation
    """
    alert = get_alert(alert_id)

    # Update alert
    alert.outcome = outcome
    alert.outcome_reason = reason
    alert.save()

    # Update metric config stats
    config = get_config(alert.metric_name)

    if outcome == 'true_positive':
        config.true_positive_count += 1
    elif outcome == 'false_positive':
        config.false_positive_count += 1

    config.save()

    # Trigger threshold adjustment if needed
    evaluate_threshold_adjustment(alert.metric_name)
```

### 7.3 Threshold Adjustment Algorithm

```python
def evaluate_threshold_adjustment(metric_name: str):
    """
    Adjust thresholds based on false positive/negative rates.

    Target: 5-10% false positive rate (balance sensitivity vs. noise)
    """
    config = get_config(metric_name)

    total_alerts = config.true_positive_count + config.false_positive_count

    if total_alerts < 10:
        # Insufficient data
        return

    false_positive_rate = config.false_positive_count / total_alerts

    # Adjustment rules
    if false_positive_rate > 0.3:
        # Too many false alarms - decrease sensitivity
        new_threshold = config.z_score_threshold * 1.2
        adjust_threshold(metric_name, new_threshold, reason="high_false_positive_rate")

    elif false_positive_rate < 0.05 and config.true_positive_count > 5:
        # Very accurate - can increase sensitivity
        new_threshold = config.z_score_threshold * 0.9
        adjust_threshold(metric_name, new_threshold, reason="low_false_positive_rate")
```

**Example Adaptation:**
```
Initial:  z_score_threshold = 3.0
Week 1:   10 alerts, 5 false positives (50% FPR) → threshold = 3.6
Week 2:   8 alerts, 2 false positives (25% FPR) → threshold = 4.3
Week 3:   5 alerts, 0 false positives (0% FPR) → threshold = 3.9
Result:   Self-tuned to 3.9 for this system's normal variance
```

### 7.4 Adjustment History

```python
def adjust_threshold(metric_name: str, new_threshold: float, reason: str):
    """Record threshold adjustment for transparency."""
    config = get_config(metric_name)

    # Add to history
    adjustment = {
        'timestamp': datetime.now().isoformat(),
        'old_threshold': config.z_score_threshold,
        'new_threshold': new_threshold,
        'reason': reason,
        'false_positive_rate': config.false_positive_count /
                              (config.true_positive_count + config.false_positive_count),
        'alert_count': config.true_positive_count + config.false_positive_count
    }

    history = json.loads(config.adjustment_history or '[]')
    history.append(adjustment)

    config.adjustment_history = json.dumps(history)
    config.z_score_threshold = new_threshold
    config.last_adjusted = datetime.now()
    config.save()

    # Log to dashboard
    log_info(f"Adjusted {metric_name} threshold: {config.z_score_threshold:.2f} → {new_threshold:.2f} ({reason})")
```

---

## 8. DASHBOARD INTEGRATION

### 8.1 Trend Charts (Sparklines)

**Component: TrendSparkline**
```tsx
interface TrendSparklineProps {
    metricName: string;
    windowHours: number;
    width?: number;
    height?: number;
}

function TrendSparkline({ metricName, windowHours, width = 100, height = 30 }: TrendSparklineProps) {
    const [data, setData] = useState<number[]>([]);
    const [trend, setTrend] = useState<'up' | 'down' | 'stable'>('stable');

    useEffect(() => {
        fetch(`/api/metrics/${metricName}/window?hours=${windowHours}`)
            .then(res => res.json())
            .then(result => {
                setData(result.values);
                setTrend(result.trend.direction);
            });
    }, [metricName, windowHours]);

    // Render SVG sparkline with color based on trend
    const color = trend === 'up' ? 'green' : trend === 'down' ? 'red' : 'gray';

    return (
        <svg width={width} height={height}>
            <polyline
                points={data.map((v, i) => `${i * (width / data.length)},${height - v * height}`).join(' ')}
                fill="none"
                stroke={color}
                strokeWidth="2"
            />
        </svg>
    );
}
```

### 8.2 Comparison (Current vs. Historical)

**Component: MetricComparison**
```tsx
function MetricComparison({ metricName }: { metricName: string }) {
    const [current, setCurrent] = useState(0);
    const [baseline, setBaseline] = useState(0);
    const [change, setChange] = useState(0);

    useEffect(() => {
        fetch(`/api/metrics/${metricName}/comparison`)
            .then(res => res.json())
            .then(data => {
                setCurrent(data.current_24h);
                setBaseline(data.baseline_30d);
                setChange(((data.current_24h - data.baseline_30d) / data.baseline_30d) * 100);
            });
    }, [metricName]);

    return (
        <div className="metric-comparison">
            <div className="current">{current.toFixed(2)}</div>
            <div className={`change ${change > 0 ? 'positive' : 'negative'}`}>
                {change > 0 ? '↑' : '↓'} {Math.abs(change).toFixed(1)}%
            </div>
            <div className="baseline">vs. 30d avg: {baseline.toFixed(2)}</div>
        </div>
    );
}
```

### 8.3 Drill-Down (Time-Series Chart)

**Component: MetricTimeSeries**
```tsx
function MetricTimeSeries({ metricName, domain }: { metricName: string, domain?: string }) {
    const [chartData, setChartData] = useState([]);
    const [anomalies, setAnomalies] = useState([]);

    useEffect(() => {
        const params = new URLSearchParams({
            window: '7d',
            granularity: '1h',
            ...(domain && { domain })
        });

        fetch(`/api/metrics/${metricName}/timeseries?${params}`)
            .then(res => res.json())
            .then(data => {
                setChartData(data.observations);
                setAnomalies(data.anomalies);
            });
    }, [metricName, domain]);

    return (
        <ResponsiveContainer width="100%" height={300}>
            <LineChart data={chartData}>
                <XAxis dataKey="timestamp" />
                <YAxis />
                <Tooltip />
                <Line type="monotone" dataKey="value" stroke="#8884d8" />

                {/* Highlight anomalies */}
                {anomalies.map(a => (
                    <ReferenceArea
                        key={a.timestamp}
                        x1={a.timestamp}
                        x2={a.timestamp}
                        fill="red"
                        fillOpacity={0.2}
                    />
                ))}
            </LineChart>
        </ResponsiveContainer>
    );
}
```

### 8.4 API Endpoints

**GET /api/metrics/{metric_name}/window**
```python
@app.get("/api/metrics/{metric_name}/window")
def get_metric_window(metric_name: str, hours: int = 24, domain: Optional[str] = None):
    """Get windowed metric with trend analysis."""
    observations = meta_observer.get_observations(metric_name, hours, domain)
    trend = meta_observer.calculate_trend(metric_name, hours, domain)

    return {
        'values': [o.value for o in observations],
        'timestamps': [o.observed_at.isoformat() for o in observations],
        'trend': trend,
        'window_hours': hours
    }
```

**GET /api/metrics/{metric_name}/comparison**
```python
@app.get("/api/metrics/{metric_name}/comparison")
def compare_metric(metric_name: str, domain: Optional[str] = None):
    """Compare current vs. baseline."""
    current = meta_observer.get_window_average(metric_name, 24, domain)
    baseline = meta_observer.get_baseline(metric_name, domain)

    return {
        'current_24h': current,
        'baseline_30d': baseline['median'],
        'baseline_range': [baseline['p5'], baseline['p95']],
        'z_score': (current - baseline['median']) / baseline['mad']
    }
```

**GET /api/alerts/active**
```python
@app.get("/api/alerts/active")
def get_active_alerts(severity: Optional[str] = None):
    """Get all active/new alerts."""
    alerts = meta_observer.get_alerts(
        states=['new', 'active'],
        severity=severity
    )

    return {
        'alerts': [alert.to_dict() for alert in alerts],
        'count': len(alerts)
    }
```

---

## 9. EDGE CASES & FAILURE MODES

### 9.1 Cold Start (No History)

**Problem:** System just installed, no baseline data

**Solution: Bootstrap Mode**
```python
def is_bootstrap_mode(metric_name: str) -> bool:
    """Check if we have enough data for reliable trends."""
    observation_count = count_observations(metric_name)

    # Need at least 1 week of data (5-min samples = 2016 samples)
    return observation_count < 2000

def handle_cold_start(metric_name: str):
    """Different behavior during bootstrap."""
    if is_bootstrap_mode(metric_name):
        # Don't fire alerts, just collect data
        return {
            'mode': 'bootstrap',
            'message': 'Collecting baseline data',
            'progress': count_observations(metric_name) / 2000
        }
    else:
        # Normal operation
        return run_trend_analysis(metric_name)
```

**Bootstrap Period: 7 days minimum**

### 9.2 Data Gaps

**Problem:** Observations missing due to system downtime

**Detection:**
```python
def detect_data_gaps(metric_name: str, window_hours: int):
    """Find gaps in observation timeline."""
    observations = get_observations(metric_name, window_hours)

    gaps = []
    for i in range(1, len(observations)):
        prev = observations[i-1]
        curr = observations[i]

        expected_interval = timedelta(minutes=5)  # Normal sampling rate
        actual_interval = curr.observed_at - prev.observed_at

        if actual_interval > expected_interval * 2:  # More than 2x expected
            gaps.append({
                'start': prev.observed_at,
                'end': curr.observed_at,
                'duration_minutes': actual_interval.total_seconds() / 60
            })

    return gaps
```

**Handling:**
```python
def interpolate_gaps(observations: List):
    """Fill small gaps with linear interpolation."""
    # Only interpolate gaps < 1 hour
    # Larger gaps: treat as missing data, don't interpolate
    for gap in gaps:
        if gap['duration_minutes'] < 60:
            # Linear interpolation
            fill_gap(gap['start'], gap['end'])
        else:
            # Flag as missing, exclude from trend analysis
            mark_missing(gap['start'], gap['end'])
```

### 9.3 Clock Skew

**Problem:** Timestamps from different sources might be slightly off

**Mitigation:**
```python
def normalize_timestamp(timestamp: datetime) -> datetime:
    """Truncate to nearest 5-minute bin to handle slight clock skew."""
    # Round down to 5-minute boundary
    minutes = (timestamp.minute // 5) * 5
    return timestamp.replace(minute=minutes, second=0, microsecond=0)
```

**Impact:** Max 5-minute error, acceptable for hourly/daily windows

### 9.4 Storage Growth Management

**Retention Policy:**
```python
RETENTION_POLICY = {
    'metric_observations': timedelta(days=90),    # 3 months granular
    'metric_hourly_rollups': timedelta(days=365), # 1 year hourly
    'metric_daily_rollups': None,                 # Keep forever (tiny)
    'meta_alerts': timedelta(days=180)            # 6 months
}

def cleanup_old_data():
    """Run nightly to enforce retention."""
    for table, retention in RETENTION_POLICY.items():
        if retention is None:
            continue

        cutoff = datetime.now() - retention

        conn.execute(f"""
            DELETE FROM {table}
            WHERE
                (observed_at < ? AND table = 'metric_observations')
                OR (hour_start < ? AND table = 'metric_hourly_rollups')
                OR (first_seen < ? AND table = 'meta_alerts')
        """, (cutoff, cutoff, cutoff))
```

**Storage Growth Rate:**
- Observations: ~3 MB per 90 days
- Rollups: ~100 KB per year
- Alerts: ~50 KB per month
- **Total: <5 MB per year** (negligible)

### 9.5 Migration from Snapshot System

**Backfill Historical Data:**
```python
def backfill_historical_stats():
    """
    Generate historical observations from existing confidence_updates table.

    Phase 1 has confidence_updates with timestamps - use those to reconstruct trends.
    """
    # Get all confidence updates, grouped by hour
    updates = conn.execute("""
        SELECT
            datetime(created_at, 'start of hour') as hour,
            AVG(new_confidence) as avg_conf,
            COUNT(*) as update_count
        FROM confidence_updates
        WHERE created_at > datetime('now', '-90 days')
        GROUP BY datetime(created_at, 'start of hour')
        ORDER BY hour
    """).fetchall()

    # Insert as observations
    for row in updates:
        insert_observation(
            metric_name='avg_confidence',
            value=row['avg_conf'],
            observed_at=row['hour'],
            metadata=json.dumps({'source': 'backfill', 'sample_count': row['update_count']})
        )
```

---

## 10. TEST SCENARIOS

### 10.1 Gradual Decline Detection

**Test: Confidence Erosion**
```python
def test_detect_gradual_confidence_decline():
    """Verify 7-day declining trend triggers alert."""
    # Setup: Insert observations with -2% per day decline
    base_confidence = 0.75

    for day in range(7):
        for hour in range(24):
            timestamp = datetime.now() - timedelta(days=7-day, hours=23-hour)
            value = base_confidence - (day * 0.02)  # -2% per day

            insert_observation('avg_confidence', value, timestamp)

    # Run trend detection
    trend = meta_observer.calculate_trend('avg_confidence', window_hours=168)

    # Assertions
    assert trend['direction'] == 'decreasing'
    assert trend['slope'] < -0.015  # At least -1.5% per day
    assert trend['confidence'] == 'high'

    # Check alert triggered
    alerts = meta_observer.check_alerts()
    assert any(a['alert_type'] == 'confidence_decline' for a in alerts)
```

### 10.2 Sudden Spike Detection

**Test: Contradiction Rate Anomaly**
```python
def test_detect_contradiction_spike():
    """Verify sudden contradiction spike triggers anomaly alert."""
    # Setup: 30 days baseline at 5% contradiction rate
    baseline_rate = 0.05

    for day in range(30):
        for sample in range(24):  # Hourly samples
            timestamp = datetime.now() - timedelta(days=30-day, hours=23-sample)
            # Add slight noise
            value = baseline_rate + random.gauss(0, 0.01)
            insert_observation('contradiction_rate', value, timestamp)

    # Spike today to 15%
    for sample in range(12):  # Last 12 hours
        timestamp = datetime.now() - timedelta(hours=11-sample)
        insert_observation('contradiction_rate', 0.15, timestamp)

    # Run anomaly detection
    anomaly = meta_observer.detect_anomalies('contradiction_rate',
                                             baseline_window_hours=720,
                                             current_window_hours=12)

    # Assertions
    assert anomaly['is_anomaly'] == True
    assert anomaly['z_score'] > 3.0
    assert anomaly['severity'] == 'critical'

    # Check alert
    alerts = meta_observer.check_alerts()
    assert any(a['alert_type'] == 'contradiction_spike' for a in alerts)
```

### 10.3 False Positive Avoidance

**Test: Normal Variance Should Not Alert**
```python
def test_normal_variance_no_alert():
    """Verify normal statistical variance doesn't trigger false alarms."""
    # Setup: 30 days of data with normal variance (σ = 0.05)
    mean = 0.70
    std = 0.05

    for day in range(30):
        for sample in range(24):
            timestamp = datetime.now() - timedelta(days=30-day, hours=23-sample)
            value = random.gauss(mean, std)
            insert_observation('avg_confidence', value, timestamp)

    # Today: still within normal range (1.5 std devs)
    for sample in range(12):
        timestamp = datetime.now() - timedelta(hours=11-sample)
        value = mean + 1.5 * std  # 0.775 (within tolerance)
        insert_observation('avg_confidence', value, timestamp)

    # Run anomaly detection
    anomaly = meta_observer.detect_anomalies('avg_confidence')

    # Should NOT be anomaly (z < 3)
    assert anomaly['is_anomaly'] == False
    assert anomaly['z_score'] < 3.0

    # No alert triggered
    alerts = meta_observer.check_alerts()
    assert not any(a['metric_name'] == 'avg_confidence' for a in alerts)
```

### 10.4 Seasonal Pattern Handling

**Test: Weekend Drop Is Normal**
```python
def test_weekend_seasonality_not_anomaly():
    """Verify expected weekend activity drop doesn't alert."""
    # Setup: 4 weeks of data with weekend pattern
    weekday_activity = 50  # validations per day
    weekend_activity = 10  # 80% drop on weekends

    for week in range(4):
        for day in range(7):
            timestamp = datetime.now() - timedelta(weeks=4-week, days=6-day)

            # Weekends (Sat=5, Sun=6) have lower activity
            activity = weekend_activity if day >= 5 else weekday_activity

            insert_observation('validation_velocity', activity, timestamp)

    # This weekend: activity drops again (expected)
    for day in range(2):  # Sat, Sun
        timestamp = datetime.now() - timedelta(days=1-day)
        insert_observation('validation_velocity', weekend_activity, timestamp)

    # Adjust for seasonality
    adjusted, factors = meta_observer.adjust_for_seasonality('validation_velocity')

    # After adjustment, weekend should look normal
    anomaly = meta_observer.detect_anomalies('validation_velocity',
                                              use_seasonal_adjustment=True)

    assert anomaly['is_anomaly'] == False
```

### 10.5 Self-Tuning Threshold Test

**Test: Threshold Adjusts After False Positives**
```python
def test_threshold_self_tuning():
    """Verify threshold increases after repeated false positives."""
    metric_name = 'test_metric'

    # Initial threshold
    config = get_or_create_config(metric_name)
    initial_threshold = config.z_score_threshold  # 3.0

    # Simulate 10 alerts
    for i in range(10):
        alert = create_alert(metric_name, z_score=3.5)

        # Mark 7 as false positives
        if i < 7:
            record_alert_outcome(alert.id, 'false_positive', 'Normal variance')
        else:
            record_alert_outcome(alert.id, 'true_positive', 'Actual issue')

    # Trigger evaluation
    meta_observer.evaluate_threshold_adjustment(metric_name)

    # Reload config
    config = get_config(metric_name)

    # Threshold should have increased (70% FPR is high)
    assert config.z_score_threshold > initial_threshold
    assert config.z_score_threshold >= 3.5  # Should be at least 3.5 now

    # Check adjustment history
    history = json.loads(config.adjustment_history)
    assert len(history) >= 1
    assert history[-1]['reason'] == 'high_false_positive_rate'
```

---

## 11. IMPLEMENTATION ESTIMATE

### 11.1 Code Breakdown

| Component | Lines of Code | Complexity | Dependencies |
|-----------|--------------|------------|--------------|
| Schema migration (SQL) | 100 | Low | SQLite |
| Observation collection | 80 | Low | None |
| Rolling window queries | 120 | Medium | None |
| Trend detection (linear regression) | 100 | Medium | numpy/scipy OR pure Python |
| Anomaly detection (z-score) | 80 | Low | numpy OR pure Python |
| Change point detection (CUSUM) | 100 | Medium | numpy OR pure Python |
| Alert management | 150 | Medium | None |
| Self-tuning thresholds | 100 | Medium | None |
| Dashboard API endpoints | 80 | Low | FastAPI |
| Maintenance/cleanup | 50 | Low | None |
| Tests | 200 | Medium | pytest |
| **TOTAL** | **1,160 LOC** | **Medium-High** | **Minimal** |

### 11.2 Complexity Rating

**Overall: 7/10 (High)**

**Breakdown:**
- Schema design: 3/10 (straightforward)
- Data collection: 2/10 (trivial)
- SQL queries: 5/10 (window functions, aggregations)
- Trend algorithms: 7/10 (statistics knowledge required)
- Alert logic: 6/10 (state machines, deduplication)
- Self-tuning: 8/10 (meta-learning is subtle)
- Testing: 7/10 (need realistic scenarios)

### 11.3 Dependencies

**Option A: Pure Python (no external deps)**
- Implement linear regression manually (simple)
- Use median/percentiles from SQLite
- Slightly more code, but self-contained

**Option B: numpy/scipy (recommended)**
- Linear regression: `scipy.stats.linregress()`
- Robust statistics: `numpy.median()`, `scipy.stats.median_abs_deviation()`
- Cleaner code, battle-tested algorithms

**Recommendation: Option B** (numpy/scipy already used in other parts of system)

### 11.4 Time Estimate

**For experienced developer:**
- Schema + migration: 2 hours
- Observation collection: 3 hours
- Window queries: 4 hours
- Trend detection: 6 hours
- Anomaly detection: 4 hours
- Alert system: 6 hours
- Self-tuning: 5 hours
- Dashboard integration: 4 hours
- Testing: 6 hours
- Documentation: 2 hours

**Total: 42 developer-hours (~1 week)**

---

## 12. FINDINGS

### [fact] Current System Uses Snapshots Only
The `get_lifecycle_stats()` method in lifecycle_manager.py (lines 792-833) returns point-in-time statistics with no historical context. There is no time-series storage or trend analysis capability.

### [fact] Phase 1 Provides Foundation
Phase 1's `confidence_updates` table has timestamps and delta tracking, which can be used to backfill initial historical data for the trend analysis system.

### [fact] Test File Mentions Meta-Observer But No Implementation
`test_lifecycle_adversarial.py` line 10 mentions "Test 4: Meta-Observer Stability (validates trend-based alerts)" but this test doesn't exist in the file. This indicates Phase 2 was planned but not yet implemented.

### [fact] Creative Proposal Has Excellent Foundation
The file `2025-12-12-creative-heuristic-intelligence-proposals.md` contains PROPOSAL 6 (lines 776-1054) with a comprehensive vision for a self-reflective meta-observer including adaptive thresholds and meta-learning, providing solid conceptual groundwork.

### [hypothesis] Rolling Windows Will Catch Gradual Issues
Snapshot-based monitoring likely misses slow degradation patterns (confidence declining 2%/day over 2 weeks would look normal at each snapshot but represents a 28% total decline). Rolling window trend analysis should detect these.

### [hypothesis] Z-Score Anomaly Detection More Robust Than Thresholds
Using z-scores (standard deviations from baseline) instead of absolute thresholds should reduce false positives across different system configurations (5% contradiction rate might be normal for one system but alarming for another).

### [hypothesis] Self-Tuning Will Reduce Alert Fatigue
Recording alert outcomes (true/false positive) and automatically adjusting thresholds should reduce false alarm rates from initial ~30% to target ~5-10% over first month of operation.

### [blocker] Statistical Library Decision Needed
Must choose between:
1. Pure Python implementation (more code, self-contained)
2. numpy/scipy (cleaner, battle-tested, but adds dependencies)

Recommendation: Use numpy/scipy since they're already in use elsewhere in the system.

### [blocker] Bootstrap Period Strategy
System needs 7+ days of data before reliable trend detection. During bootstrap, must either:
1. Suppress all alerts (collect data silently)
2. Use simplified threshold alerts (less accurate)
3. Use synthetic baseline from Phase 1 stats

Recommendation: Option 1 (bootstrap mode with progress indicator).

### [question] Should Seasonal Adjustment Be Automatic or Opt-In?
If weekend activity naturally drops 80%, should the system:
1. Automatically learn this pattern and adjust (risk: masks real problems)
2. Alert on weekend drops until user teaches it "this is normal" (more control)
3. Require explicit seasonal pattern configuration (most work)

Recommendation: Option 2 (alert + user acknowledgment teaches the system).

### [question] How Aggressive Should Self-Tuning Be?
If threshold adjustments happen too quickly, system might overcorrect on outliers. If too slow, alert fatigue persists. What's the right balance?

Recommendation: Require 10+ alert outcomes before adjustment, move threshold by max 20% per adjustment, re-evaluate every 50 alerts.

### [question] Should Anomalies Block Promotions?
If a heuristic's confidence is anomalously high (z-score > 3), should it be eligible for promotion to golden? Could indicate gaming or unusual circumstances.

Recommendation: Yes, flag as "confidence_anomaly" and require CEO review before promotion.

### [fact] Storage Requirements Are Negligible
Estimated ~3 MB for 90 days of granular data plus rollups. This is trivial for modern systems and should not be a concern.

### [fact] Existing Dashboard Can Be Extended
The dashboard already has panels for stats (StatsBar.tsx, HeuristicPanel.tsx). Adding trend sparklines and time-series charts should integrate cleanly with existing architecture.

---

## 13. NEXT STEPS (Implementation Order)

### Phase 2A: Foundation (Week 1)
1. Schema migration (metric_observations, rollups, alerts tables)
2. Observation collection (integrate into lifecycle_manager.py)
3. Basic window queries (test with 24h, 7d windows)

### Phase 2B: Analysis (Week 2)
4. Trend detection (linear regression)
5. Anomaly detection (z-score with robust stats)
6. Alert system (state machine, deduplication)

### Phase 2C: Intelligence (Week 3)
7. Baseline learning
8. False positive tracking
9. Self-tuning thresholds

### Phase 2D: Integration (Week 4)
10. Dashboard API endpoints
11. Frontend components (sparklines, comparisons)
12. Testing suite
13. Documentation

---

## 14. REFERENCES

**Existing Code:**
- `C:/Users/Evede/.claude/emergent-learning/query/lifecycle_manager.py` (Phase 1)
- `C:/Users/Evede/.claude/emergent-learning/tests/test_lifecycle_adversarial.py` (Test framework)
- `C:/Users/Evede/.claude/emergent-learning/memory/successes/2025-12-12-creative-heuristic-intelligence-proposals.md` (PROPOSAL 6)

**Algorithms:**
- CUSUM change point detection: Page, E.S. (1954). "Continuous Inspection Schemes"
- Z-score anomaly detection: Standard statistical method
- MAD robust statistics: Hampel, F.R. (1974). "The influence curve and its role in robust estimation"

**SQL Time-Series Patterns:**
- Sliding window queries with BETWEEN
- Percentile calculations with NTILE or custom aggregates
- Retention policies with scheduled DELETE

---

**End of Design Document**

**Status:** Ready for review
**Approval needed from:** CEO (user)
**Risk level:** Medium (new system, moderate complexity)
**Impact:** High (enables proactive system health monitoring)
