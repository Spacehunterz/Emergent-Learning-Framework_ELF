# Fraud Detection System Design - Phase 2
## Heuristic Lifecycle Security Enhancement

**Author:** Agent 1 (Ultrathink Swarm)
**Date:** 2025-12-12
**Status:** Design Proposal
**Prerequisites:** Phase 1 (Rate Limiting, Dormant Recovery, Rate-based Contradictions)

---

## Executive Summary

Phase 1 implemented basic protections (rate limiting, confidence bounds, symmetric updates). However, sophisticated manipulation is still possible through:
- Selective validation (cherry-picking easy tasks)
- Timing attacks (exploiting cooldown boundaries)
- Coordinated manipulation (multi-agent gaming)
- Pattern exploitation (learning and gaming decay/revival cycles)

This design proposes a **multi-layered fraud detection system** using:
1. **Anomaly scoring** - Combine weak signals into strong detections
2. **Behavioral analysis** - Detect suspicious patterns over time
3. **Statistical baselines** - Compare against domain/system norms
4. **Cross-validation** - Multiple detection algorithms voting

---

## 1. Threat Model

### 1.1 Pump-and-Dump Attack (Enhanced)

**Attack Vector:**
- Attacker stays within rate limits (5 updates/day, 60-min cooldown)
- Selectively applies heuristic ONLY to tasks likely to succeed
- Avoids applying to hard/ambiguous tasks that might fail
- Waits for cooldown to expire, then repeats

**Example Timeline:**
```
Day 1: 09:00 - Apply to easy task → SUCCESS (+0.05)
       10:01 - Apply to easy task → SUCCESS (+0.045)
       11:02 - Apply to easy task → SUCCESS (+0.041)
       12:03 - Apply to easy task → SUCCESS (+0.037)
       13:04 - Apply to easy task → SUCCESS (+0.034)
       [5 updates reached, stays within limit]

Day 2: [Repeat pattern, confidence now 0.707]
Day 3: [Continue, confidence 0.836]
```

**Detection Signals:**
- Success rate significantly above domain average
- Update intervals clustered around exactly 60-61 minutes
- All updates from same session/agent
- Heuristic confidence grows faster than statistical baseline
- Zero failures despite high application count

---

### 1.2 Selective Validation (Cherry-Picking)

**Attack Vector:**
- Agent examines task before deciding to apply heuristic
- Only applies when confidence of success is very high
- Creates artificial success rate by biased sampling

**Example:**
```python
# Adversarial agent logic
def should_apply_heuristic(task, heuristic):
    if task.difficulty == "easy" and task.domain == heuristic.sweet_spot:
        return True  # Only apply when we know it'll work
    else:
        return False  # Skip hard tasks
```

**Detection Signals:**
- Heuristic success rate >> system baseline for that domain
- Application count much lower than query context frequency
- Confidence grows despite low application count
- Temporal correlation: successes cluster, no attempts during "hard work" periods

---

### 1.3 Timing Attacks

**Attack Vector:**
- Exploit cooldown window boundaries
- Game daily reset timing (update 5 times before midnight, 5 times after)
- Synchronize updates across multiple heuristics to maximize manipulation

**Example Timeline:**
```
Day 1: 23:00 - Update heuristic A
       23:05 - Update heuristic B
       23:10 - Update heuristic C

Day 2: 00:05 - Update heuristic A (daily counter reset!)
       00:10 - Update heuristic B (daily counter reset!)
       00:15 - Update heuristic C (daily counter reset!)

Result: 10 updates/day instead of intended 5
```

**Detection Signals:**
- Update timestamps clustered around midnight (daily reset boundary)
- Update intervals exactly at cooldown minimum (60-61 minutes)
- Non-random distribution of update timing
- Multiple heuristics updated in rapid succession by same agent

---

### 1.4 Coordinated Manipulation (Multi-Agent)

**Attack Vector:**
- Multiple agents coordinate to boost same heuristic
- Each stays within rate limits individually
- Combined effect accelerates confidence manipulation

**Example:**
```
Agent A: 5 updates/day → SUCCESS
Agent B: 5 updates/day → SUCCESS
Agent C: 5 updates/day → SUCCESS

Result: 15 updates/day on same heuristic (3x rate limit)
```

**Detection Signals:**
- Multiple distinct agents updating same heuristic
- Temporal correlation between different agent sessions
- Suspiciously similar update patterns across agents
- All agents show above-average success rates for same heuristic

---

### 1.5 Revival Gaming

**Attack Vector:**
- Learn which dormant heuristics have favorable revival conditions
- Trigger revivals selectively for "good" heuristics
- Let "bad" heuristics stay dormant

**Example:**
```
Context injection attack:
"I'm working on Redis caching distributed session management..."
[Triggers revival of favorable caching heuristics]

Meanwhile: Never mention contexts that would revive unfavorable heuristics
```

**Detection Signals:**
- Same agent repeatedly reviving specific heuristics
- Revival rate significantly above baseline
- Revived heuristics consistently show high success rates
- Revival triggers suspiciously aligned with agent's task preferences

---

### 1.6 Confidence Oscillation

**Attack Vector:**
- Keep confidence bouncing between thresholds
- Avoid deprecation by staying just above contradiction threshold
- Avoid dormancy by occasional applications

**Example:**
```
Confidence drifts down to 0.25 → Apply 2 successes → Back to 0.30
Wait for decay → 0.23 → Apply 2 successes → 0.28
[Keeps heuristic alive indefinitely despite low utility]
```

**Detection Signals:**
- Confidence oscillates around dormancy threshold (0.20)
- Update timing correlated with approaching thresholds
- Minimal net confidence change over long periods
- Low application rate with strategic timing

---

## 2. Detection Algorithms

### 2.1 Success Rate Anomaly Detection

**Algorithm:**
```python
def detect_success_rate_anomaly(heuristic_id: int) -> AnomalyScore:
    """
    Compare heuristic success rate to domain baseline.

    Anomaly if:
    - Success rate > (domain_avg + 2*stddev) AND
    - Applications > 10 AND
    - Z-score > 2.5
    """
    h = get_heuristic(heuristic_id)
    domain_stats = get_domain_baseline(h.domain)

    # Calculate success rate
    total = h.times_validated + h.times_violated + h.times_contradicted
    if total < 10:
        return AnomalyScore(0, "insufficient_data")

    success_rate = h.times_validated / total

    # Compare to domain baseline
    domain_avg = domain_stats.avg_success_rate
    domain_std = domain_stats.std_success_rate

    z_score = (success_rate - domain_avg) / domain_std

    # Anomaly threshold
    if z_score > 2.5:  # >99% percentile
        return AnomalyScore(
            score=min(z_score / 5.0, 1.0),  # Normalize to 0-1
            reason=f"Success rate {success_rate:.2%} is {z_score:.1f}σ above domain average {domain_avg:.2%}",
            severity="high" if z_score > 3.5 else "medium"
        )

    return AnomalyScore(0, "normal")
```

**False Positive Mitigation:**
- Require minimum application count (10+)
- Use domain-specific baselines (not global)
- Account for heuristic age (newer heuristics may have variance)
- Whitelist golden rules (they SHOULD have high success rates)

---

### 2.2 Temporal Pattern Analysis

**Algorithm:**
```python
def detect_temporal_manipulation(heuristic_id: int) -> AnomalyScore:
    """
    Detect suspicious timing patterns in updates.

    Signals:
    1. Updates clustered at cooldown boundary (60-65 min intervals)
    2. Updates clustered at midnight (daily reset gaming)
    3. Non-random distribution (Chi-squared test)
    """
    updates = get_confidence_updates(heuristic_id, days=30)

    if len(updates) < 5:
        return AnomalyScore(0, "insufficient_data")

    # Calculate inter-update intervals
    intervals = []
    for i in range(1, len(updates)):
        delta = (updates[i].timestamp - updates[i-1].timestamp).total_seconds() / 60
        intervals.append(delta)

    # Signal 1: Cooldown boundary clustering
    cooldown_cluster = sum(1 for iv in intervals if 60 <= iv <= 65) / len(intervals)

    # Signal 2: Midnight clustering
    midnight_updates = sum(1 for u in updates if 0 <= u.timestamp.hour <= 1 or 23 <= u.timestamp.hour <= 24)
    midnight_rate = midnight_updates / len(updates)
    expected_midnight_rate = 3/24  # 3 hours out of 24

    # Signal 3: Interval variance (too regular = suspicious)
    if len(intervals) >= 3:
        interval_std = std(intervals)
        interval_mean = mean(intervals)
        coefficient_of_variation = interval_std / interval_mean if interval_mean > 0 else 0

        # Low CV = very regular timing (suspicious)
        regularity_suspicion = 1.0 - min(coefficient_of_variation / 0.5, 1.0)
    else:
        regularity_suspicion = 0

    # Combine signals
    anomaly_score = (
        0.4 * cooldown_cluster +  # 40% weight on cooldown gaming
        0.3 * max(0, midnight_rate - expected_midnight_rate) * 4 +  # 30% on midnight gaming
        0.3 * regularity_suspicion  # 30% on too-regular timing
    )

    if anomaly_score > 0.5:
        return AnomalyScore(
            score=anomaly_score,
            reason=f"Temporal anomalies: {cooldown_cluster:.0%} at cooldown boundary, {midnight_rate:.0%} at midnight, CV={coefficient_of_variation:.2f}",
            severity="high" if anomaly_score > 0.7 else "medium"
        )

    return AnomalyScore(0, "normal")
```

**False Positive Mitigation:**
- Require pattern over multiple updates (5+ minimum)
- Account for legitimate work schedules (some users DO work at midnight)
- Use threshold bands, not exact values
- Consider timezone differences

---

### 2.3 Multi-Agent Correlation Detection

**Algorithm:**
```python
def detect_coordinated_manipulation(heuristic_id: int) -> AnomalyScore:
    """
    Detect multiple agents suspiciously targeting same heuristic.

    Signals:
    1. Multiple distinct agents (3+) updating same heuristic
    2. Temporal correlation (updates within 24h windows)
    3. Similar update patterns (all successes, similar intervals)
    """
    updates = get_confidence_updates(heuristic_id, days=30)

    # Group by agent
    agent_updates = defaultdict(list)
    for u in updates:
        if u.agent_id:
            agent_updates[u.agent_id].append(u)

    num_agents = len(agent_updates)

    if num_agents < 2:
        return AnomalyScore(0, "single_agent")

    # Signal 1: Multiple agents (normalized)
    multi_agent_score = min((num_agents - 1) / 4, 1.0)  # 5+ agents = max score

    # Signal 2: Temporal correlation
    temporal_correlation = 0
    if num_agents >= 2:
        # Check if different agents update within same 24h windows
        update_days = [u.timestamp.date() for u in updates]
        day_agent_count = Counter(update_days)
        multi_agent_days = sum(1 for count in day_agent_count.values() if count >= 2)
        temporal_correlation = multi_agent_days / len(set(update_days)) if update_days else 0

    # Signal 3: Pattern similarity (all agents show high success rate)
    agent_success_rates = []
    for agent_id, agent_upd in agent_updates.items():
        successes = sum(1 for u in agent_upd if u.update_type == 'success')
        agent_success_rates.append(successes / len(agent_upd) if agent_upd else 0)

    pattern_similarity = 0
    if len(agent_success_rates) >= 2:
        avg_success = mean(agent_success_rates)
        if avg_success > 0.75:  # All agents have >75% success
            pattern_similarity = min(avg_success, 1.0)

    # Combine signals
    anomaly_score = (
        0.3 * multi_agent_score +
        0.4 * temporal_correlation +
        0.3 * pattern_similarity
    )

    if anomaly_score > 0.5:
        return AnomalyScore(
            score=anomaly_score,
            reason=f"Coordinated manipulation: {num_agents} agents, {temporal_correlation:.0%} temporal overlap, {mean(agent_success_rates):.0%} avg success",
            severity="critical" if anomaly_score > 0.75 else "high"
        )

    return AnomalyScore(0, "normal")
```

**False Positive Mitigation:**
- Multiple agents is NORMAL for shared domains (e.g., "git", "python")
- Only flag if BOTH multi-agent AND other suspicious patterns
- Weight recent updates more than historical
- Consider heuristic age (older = more agents expected)

---

### 2.4 Confidence Trajectory Analysis

**Algorithm:**
```python
def detect_unnatural_confidence_growth(heuristic_id: int) -> AnomalyScore:
    """
    Detect confidence growth patterns inconsistent with natural learning.

    Natural learning: noisy, plateaus, occasional drops
    Manipulated: smooth, monotonic, too fast
    """
    updates = get_confidence_updates(heuristic_id, days=60)

    if len(updates) < 10:
        return AnomalyScore(0, "insufficient_data")

    # Extract confidence trajectory
    confidences = [u.new_confidence for u in updates]

    # Signal 1: Monotonic growth (never drops)
    monotonic = all(confidences[i] >= confidences[i-1] for i in range(1, len(confidences)))

    # Signal 2: Growth rate (slope)
    time_days = [(updates[i].timestamp - updates[0].timestamp).days for i in range(len(updates))]
    if time_days[-1] > 0:
        slope = (confidences[-1] - confidences[0]) / time_days[-1]  # Confidence per day
    else:
        slope = 0

    # Signal 3: Smoothness (low variance in deltas)
    deltas = [confidences[i] - confidences[i-1] for i in range(1, len(confidences))]
    delta_variance = var(deltas) if len(deltas) > 1 else 0

    # Natural learning has noisy deltas, manipulation is smooth
    smoothness_score = 1.0 - min(delta_variance / 0.01, 1.0)  # Low variance = suspicious

    # Combine signals
    anomaly_score = (
        0.3 * (1.0 if monotonic and len(updates) > 10 else 0) +
        0.4 * min(slope / 0.02, 1.0) +  # >0.02 conf/day = suspicious
        0.3 * smoothness_score
    )

    if anomaly_score > 0.5:
        return AnomalyScore(
            score=anomaly_score,
            reason=f"Unnatural growth: monotonic={monotonic}, slope={slope:.4f}/day, smoothness={smoothness_score:.2f}",
            severity="medium"
        )

    return AnomalyScore(0, "normal")
```

**False Positive Mitigation:**
- Some heuristics ARE consistently good (golden rules)
- Require COMBINATION of signals (monotonic + fast + smooth)
- Whitelist heuristics with high validation counts (proven good)
- Age-dependent thresholds (newer heuristics can grow fast legitimately)

---

### 2.5 Application Selectivity Detection

**Algorithm:**
```python
def detect_application_selectivity(heuristic_id: int) -> AnomalyScore:
    """
    Detect if heuristic is being selectively applied (cherry-picking).

    Signal: Context mentions heuristic keywords but heuristic isn't applied.

    This requires access to session context logs (see schema changes).
    """
    h = get_heuristic(heuristic_id)
    keywords = extract_keywords(h.rule)

    # Get session contexts from last 30 days
    contexts = get_session_contexts(days=30)

    # Count how often keywords appear
    keyword_mentions = 0
    for ctx in contexts:
        if any(kw in ctx.text.lower() for kw in keywords):
            keyword_mentions += 1

    # Count how often heuristic was actually applied
    applications = h.times_validated + h.times_violated + h.times_contradicted

    # Expected: application rate should roughly match keyword mention rate
    # (with some variance for context relevance)

    if keyword_mentions < 10:
        return AnomalyScore(0, "insufficient_context_data")

    application_rate = applications / keyword_mentions

    # Suspiciously low application rate despite keyword matches
    if application_rate < 0.1:  # Applied <10% of the time keywords appeared
        return AnomalyScore(
            score=1.0 - application_rate * 10,  # Closer to 0 = higher score
            reason=f"Selective application: {applications} applications despite {keyword_mentions} keyword mentions ({application_rate:.0%} rate)",
            severity="medium"
        )

    return AnomalyScore(0, "normal")
```

**Note:** This requires new schema to track context (see Section 4).

**False Positive Mitigation:**
- Keywords may appear in irrelevant contexts
- Some heuristics are domain-specific (legitimately rare)
- Require minimum keyword mention count (10+)
- Compare to domain baseline application rates

---

### 2.6 Revival Pattern Analysis

**Algorithm:**
```python
def detect_revival_gaming(heuristic_id: int) -> AnomalyScore:
    """
    Detect suspicious revival patterns.

    Signals:
    1. Frequent revival/dormancy cycles
    2. Same agent repeatedly reviving
    3. Revived heuristics consistently high success
    """
    h = get_heuristic(heuristic_id)

    if h.times_revived == 0:
        return AnomalyScore(0, "never_revived")

    # Signal 1: Revival frequency
    age_days = (datetime.now() - h.created_at).days
    revival_rate = h.times_revived / (age_days / 30)  # Revivals per month

    # Signal 2: Agent concentration
    revival_events = get_confidence_updates(heuristic_id, update_type='revival')
    revival_agents = [r.agent_id for r in revival_events if r.agent_id]
    agent_diversity = len(set(revival_agents)) / len(revival_agents) if revival_agents else 0

    # Low diversity = same agent reviving repeatedly
    agent_concentration = 1.0 - agent_diversity

    # Signal 3: Post-revival success rate
    post_revival_updates = []
    for i, u in enumerate(get_confidence_updates(heuristic_id)):
        if u.update_type == 'revival':
            # Get next 5 updates after revival
            post_revival_updates.extend(get_confidence_updates(heuristic_id)[i+1:i+6])

    if post_revival_updates:
        post_revival_success = sum(1 for u in post_revival_updates if u.update_type == 'success') / len(post_revival_updates)
    else:
        post_revival_success = 0

    # Combine signals
    anomaly_score = (
        0.3 * min(revival_rate / 2, 1.0) +  # >2 revivals/month = suspicious
        0.4 * agent_concentration +  # Same agent = suspicious
        0.3 * max(0, post_revival_success - 0.7)  # >70% success after revival = cherry-picking
    )

    if anomaly_score > 0.5:
        return AnomalyScore(
            score=anomaly_score,
            reason=f"Revival gaming: {revival_rate:.1f} revivals/month, {agent_concentration:.0%} agent concentration, {post_revival_success:.0%} post-revival success",
            severity="medium"
        )

    return AnomalyScore(0, "normal")
```

**False Positive Mitigation:**
- Some heuristics ARE legitimately useful in cycles (e.g., seasonal work)
- Revival by multiple agents is normal for shared knowledge
- High post-revival success may indicate genuinely good heuristic
- Require COMBINATION of high revival rate + concentration + success

---

## 3. Anomaly Scoring System

### 3.1 Multi-Signal Fusion

**Approach:** Bayesian combination of weak signals into strong detection.

```python
@dataclass
class AnomalyScore:
    score: float  # 0.0 - 1.0
    reason: str
    severity: str  # "low", "medium", "high", "critical"
    algorithm: str  # Which detector produced this

class FraudDetector:
    """Main fraud detection orchestrator."""

    def analyze_heuristic(self, heuristic_id: int) -> FraudReport:
        """
        Run all detection algorithms and combine results.
        """
        # Run all detectors
        signals = []

        signals.append(detect_success_rate_anomaly(heuristic_id))
        signals.append(detect_temporal_manipulation(heuristic_id))
        signals.append(detect_coordinated_manipulation(heuristic_id))
        signals.append(detect_unnatural_confidence_growth(heuristic_id))
        signals.append(detect_application_selectivity(heuristic_id))
        signals.append(detect_revival_gaming(heuristic_id))

        # Filter out "normal" signals
        anomalies = [s for s in signals if s.score > 0]

        if not anomalies:
            return FraudReport(
                heuristic_id=heuristic_id,
                fraud_score=0.0,
                classification="clean",
                signals=[]
            )

        # Bayesian fusion: P(fraud | signals)
        # Using naive Bayes approximation

        # Prior probability of fraud (base rate)
        prior_fraud = 0.05  # Assume 5% of heuristics are manipulated

        # Likelihood ratios for each signal
        likelihood_ratios = []
        for anomaly in anomalies:
            # Higher score = stronger evidence
            # Convert score to likelihood ratio
            # LR = P(signal | fraud) / P(signal | clean)

            # Assume:
            # - P(signal | fraud) = 0.8 * score (manipulated heuristics likely show signal)
            # - P(signal | clean) = 0.1 * score (clean heuristics rarely show signal)

            p_signal_given_fraud = 0.8 * anomaly.score
            p_signal_given_clean = 0.1 * anomaly.score

            if p_signal_given_clean > 0:
                lr = p_signal_given_fraud / p_signal_given_clean
            else:
                lr = 10.0  # Default high LR

            likelihood_ratios.append(lr)

        # Combine likelihood ratios
        combined_lr = product(likelihood_ratios)

        # Posterior odds = prior odds * LR
        prior_odds = prior_fraud / (1 - prior_fraud)
        posterior_odds = prior_odds * combined_lr

        # Convert back to probability
        posterior_prob = posterior_odds / (1 + posterior_odds)

        # Classification thresholds
        if posterior_prob > 0.8:
            classification = "fraud_confirmed"
        elif posterior_prob > 0.5:
            classification = "fraud_likely"
        elif posterior_prob > 0.2:
            classification = "suspicious"
        else:
            classification = "low_confidence"

        return FraudReport(
            heuristic_id=heuristic_id,
            fraud_score=posterior_prob,
            classification=classification,
            signals=anomalies,
            likelihood_ratio=combined_lr,
            timestamp=datetime.now()
        )
```

### 3.2 Threshold Tuning Strategy

**Adaptive Thresholds:**

1. **Baseline Establishment (Cold Start)**
   - First 30 days: Collect data, NO enforcement
   - Establish domain-specific baselines
   - Calculate statistical distributions (mean, stddev, percentiles)

2. **Conservative Phase (Days 31-90)**
   - Only flag "fraud_confirmed" (>80% posterior)
   - Manual review of all detections
   - Tune false positive rate to <1%

3. **Active Enforcement (Day 90+)**
   - Auto-respond to "fraud_likely" (>50% posterior)
   - CEO escalation for "suspicious" (>20% posterior)
   - Continuous monitoring of false positive/negative rates

4. **Continuous Learning**
   - Track detection accuracy (false positives/negatives)
   - Adjust likelihood ratios based on observed performance
   - Update baselines monthly

---

## 4. Schema Changes

### 4.1 New Tables

```sql
-- ============================================
-- Fraud Detection Tables
-- ============================================

-- Store fraud detection reports
CREATE TABLE fraud_reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    heuristic_id INTEGER NOT NULL,
    fraud_score REAL NOT NULL,  -- 0.0 - 1.0 posterior probability
    classification TEXT NOT NULL CHECK(classification IN
        ('clean', 'low_confidence', 'suspicious', 'fraud_likely', 'fraud_confirmed')),
    likelihood_ratio REAL,
    signal_count INTEGER,  -- Number of anomalies detected
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    reviewed_at DATETIME,
    reviewed_by TEXT,  -- CEO/admin who reviewed
    review_outcome TEXT CHECK(review_outcome IN
        ('false_positive', 'true_positive', 'pending', NULL)),
    FOREIGN KEY (heuristic_id) REFERENCES heuristics(id) ON DELETE CASCADE
);

CREATE INDEX idx_fraud_reports_heuristic ON fraud_reports(heuristic_id);
CREATE INDEX idx_fraud_reports_score ON fraud_reports(fraud_score DESC);
CREATE INDEX idx_fraud_reports_classification ON fraud_reports(classification);
CREATE INDEX idx_fraud_reports_pending ON fraud_reports(review_outcome)
    WHERE review_outcome = 'pending' OR review_outcome IS NULL;

-- Store individual anomaly signals
CREATE TABLE anomaly_signals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fraud_report_id INTEGER NOT NULL,
    algorithm TEXT NOT NULL,  -- Which detector produced this
    score REAL NOT NULL,  -- 0.0 - 1.0
    severity TEXT NOT NULL CHECK(severity IN ('low', 'medium', 'high', 'critical')),
    reason TEXT NOT NULL,  -- Human-readable explanation
    metadata TEXT,  -- JSON with algorithm-specific details
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (fraud_report_id) REFERENCES fraud_reports(id) ON DELETE CASCADE
);

CREATE INDEX idx_anomaly_signals_report ON anomaly_signals(fraud_report_id);
CREATE INDEX idx_anomaly_signals_algorithm ON anomaly_signals(algorithm);

-- Store domain baselines for anomaly detection
CREATE TABLE domain_baselines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    domain TEXT NOT NULL UNIQUE,
    avg_success_rate REAL,
    std_success_rate REAL,
    avg_applications_per_heuristic REAL,
    avg_confidence_growth_rate REAL,  -- Confidence units per day
    avg_update_interval_minutes REAL,
    std_update_interval_minutes REAL,
    sample_size INTEGER,  -- Number of heuristics in baseline
    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_domain_baselines_domain ON domain_baselines(domain);

-- Track session contexts for application selectivity detection
CREATE TABLE session_contexts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    agent_id TEXT,
    context_text TEXT NOT NULL,  -- User query or task description
    context_hash TEXT,  -- For deduplication
    heuristics_applied TEXT,  -- JSON array of heuristic IDs applied in this context
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_session_contexts_session ON session_contexts(session_id);
CREATE INDEX idx_session_contexts_timestamp ON session_contexts(timestamp DESC);
CREATE INDEX idx_session_contexts_hash ON session_contexts(context_hash);

-- Full-text search on contexts for keyword matching
CREATE VIRTUAL TABLE session_contexts_fts USING fts5(
    context_text,
    content='session_contexts',
    content_rowid='id'
);

-- Trigger to keep FTS in sync
CREATE TRIGGER session_contexts_fts_insert AFTER INSERT ON session_contexts
BEGIN
    INSERT INTO session_contexts_fts(rowid, context_text)
    VALUES (new.id, new.context_text);
END;

-- Response actions taken by system
CREATE TABLE fraud_responses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fraud_report_id INTEGER NOT NULL,
    response_type TEXT NOT NULL CHECK(response_type IN
        ('confidence_freeze', 'confidence_reset', 'status_quarantine',
         'rate_limit_tighten', 'ceo_escalation', 'auto_deprecate')),
    parameters TEXT,  -- JSON with response-specific params
    executed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    executed_by TEXT,  -- System or admin
    rollback_at DATETIME,  -- When was this reversed, if applicable
    FOREIGN KEY (fraud_report_id) REFERENCES fraud_reports(id) ON DELETE CASCADE
);

CREATE INDEX idx_fraud_responses_report ON fraud_responses(fraud_report_id);
CREATE INDEX idx_fraud_responses_type ON fraud_responses(response_type);
```

### 4.2 Additional Columns for Existing Tables

```sql
-- Add fraud tracking to heuristics table
ALTER TABLE heuristics ADD COLUMN is_quarantined INTEGER DEFAULT 0;
ALTER TABLE heuristics ADD COLUMN quarantine_reason TEXT;
ALTER TABLE heuristics ADD COLUMN quarantine_since DATETIME;
ALTER TABLE heuristics ADD COLUMN fraud_flags INTEGER DEFAULT 0;  -- Count of fraud detections
ALTER TABLE heuristics ADD COLUMN last_fraud_check DATETIME;

-- Add context tracking to confidence_updates
ALTER TABLE confidence_updates ADD COLUMN context_id INTEGER REFERENCES session_contexts(id);
ALTER TABLE confidence_updates ADD COLUMN pre_update_fraud_score REAL;  -- Fraud score before this update
```

### 4.3 Views

```sql
-- High-risk heuristics requiring attention
CREATE VIEW high_risk_heuristics AS
SELECT
    h.id,
    h.domain,
    h.rule,
    h.confidence,
    h.status,
    h.fraud_flags,
    fr.fraud_score,
    fr.classification,
    fr.created_at as last_fraud_check,
    COUNT(as_tbl.id) as anomaly_count
FROM heuristics h
LEFT JOIN fraud_reports fr ON h.id = fr.heuristic_id
    AND fr.id = (SELECT MAX(id) FROM fraud_reports WHERE heuristic_id = h.id)
LEFT JOIN anomaly_signals as_tbl ON fr.id = as_tbl.fraud_report_id
WHERE fr.classification IN ('suspicious', 'fraud_likely', 'fraud_confirmed')
   OR h.is_quarantined = 1
GROUP BY h.id
ORDER BY fr.fraud_score DESC;

-- Fraud detection performance metrics
CREATE VIEW fraud_detection_metrics AS
SELECT
    classification,
    COUNT(*) as total_reports,
    SUM(CASE WHEN review_outcome = 'true_positive' THEN 1 ELSE 0 END) as true_positives,
    SUM(CASE WHEN review_outcome = 'false_positive' THEN 1 ELSE 0 END) as false_positives,
    SUM(CASE WHEN review_outcome IS NULL THEN 1 ELSE 0 END) as pending_review,
    AVG(fraud_score) as avg_fraud_score,
    MIN(created_at) as first_detection,
    MAX(created_at) as last_detection
FROM fraud_reports
GROUP BY classification;

-- Domain fraud statistics
CREATE VIEW domain_fraud_stats AS
SELECT
    h.domain,
    COUNT(DISTINCT h.id) as total_heuristics,
    COUNT(DISTINCT fr.heuristic_id) as flagged_heuristics,
    AVG(fr.fraud_score) as avg_fraud_score,
    SUM(CASE WHEN h.is_quarantined = 1 THEN 1 ELSE 0 END) as quarantined_count
FROM heuristics h
LEFT JOIN fraud_reports fr ON h.id = fr.heuristic_id
    AND fr.classification IN ('suspicious', 'fraud_likely', 'fraud_confirmed')
GROUP BY h.domain
HAVING flagged_heuristics > 0
ORDER BY avg_fraud_score DESC;
```

---

## 5. Response Actions

### 5.1 Response Matrix

| Fraud Score | Classification | Automatic Actions | CEO Escalation |
|-------------|----------------|-------------------|----------------|
| 0.0 - 0.2 | clean | None | No |
| 0.2 - 0.5 | suspicious | Log warning, increase monitoring frequency | No (report available) |
| 0.5 - 0.8 | fraud_likely | Confidence freeze, tighten rate limits (3/day, 90-min cooldown) | Yes (notification) |
| 0.8 - 1.0 | fraud_confirmed | Quarantine heuristic, reset confidence to 0.5, CEO escalation | Yes (requires approval to restore) |

### 5.2 Confidence Freeze

**Trigger:** fraud_likely or fraud_confirmed

**Action:**
```python
def freeze_confidence(heuristic_id: int, fraud_report_id: int):
    """
    Prevent any confidence updates until fraud investigation complete.
    """
    conn.execute("""
        UPDATE heuristics SET
            is_quarantined = 1,
            quarantine_reason = 'Fraud detection: confidence manipulation detected',
            quarantine_since = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (heuristic_id,))

    # Record response action
    conn.execute("""
        INSERT INTO fraud_responses
        (fraud_report_id, response_type, parameters, executed_by)
        VALUES (?, 'confidence_freeze', '{}', 'system')
    """, (fraud_report_id,))

    # All future update_confidence() calls will check is_quarantined flag
```

**Impact:**
- `update_confidence()` returns `{"success": False, "reason": "Heuristic quarantined for fraud investigation"}`
- Heuristic remains in query results but marked as quarantined
- Can be manually unfrozen by CEO after review

### 5.3 Confidence Reset

**Trigger:** fraud_confirmed + CEO approval

**Action:**
```python
def reset_confidence(heuristic_id: int, fraud_report_id: int, reason: str):
    """
    Reset manipulated confidence to neutral baseline.
    """
    old_confidence = get_heuristic(heuristic_id).confidence
    new_confidence = 0.5  # Reset to neutral

    conn.execute("""
        UPDATE heuristics SET
            confidence = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (new_confidence, heuristic_id))

    # Record in audit trail
    conn.execute("""
        INSERT INTO confidence_updates
        (heuristic_id, old_confidence, new_confidence, delta,
         update_type, reason, agent_id)
        VALUES (?, ?, ?, ?, 'manual', ?, 'fraud_detector')
    """, (heuristic_id, old_confidence, new_confidence,
          new_confidence - old_confidence, reason))

    # Record response
    conn.execute("""
        INSERT INTO fraud_responses
        (fraud_report_id, response_type, parameters, executed_by)
        VALUES (?, 'confidence_reset', ?, 'ceo')
    """, (fraud_report_id, json.dumps({"old_confidence": old_confidence})))
```

### 5.4 Rate Limit Tightening

**Trigger:** fraud_likely

**Action:**
```python
def tighten_rate_limits(heuristic_id: int, fraud_report_id: int):
    """
    Apply stricter rate limits to suspicious heuristic.
    """
    # Store per-heuristic rate limit overrides
    conn.execute("""
        INSERT INTO heuristic_rate_overrides
        (heuristic_id, max_updates_per_day, cooldown_minutes, reason)
        VALUES (?, 3, 90, 'Fraud detection: suspicious update patterns')
    """, (heuristic_id,))

    conn.execute("""
        INSERT INTO fraud_responses
        (fraud_report_id, response_type, parameters, executed_by)
        VALUES (?, 'rate_limit_tighten',
                '{"max_updates_per_day": 3, "cooldown_minutes": 90}',
                'system')
    """, (fraud_report_id,))
```

**New Schema for Overrides:**
```sql
CREATE TABLE heuristic_rate_overrides (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    heuristic_id INTEGER NOT NULL UNIQUE,
    max_updates_per_day INTEGER,
    cooldown_minutes INTEGER,
    reason TEXT,
    applied_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    expires_at DATETIME,  -- Optional auto-expiry
    FOREIGN KEY (heuristic_id) REFERENCES heuristics(id) ON DELETE CASCADE
);
```

### 5.5 CEO Escalation

**Trigger:** fraud_likely or fraud_confirmed

**Action:**
```python
def escalate_to_ceo(heuristic_id: int, fraud_report: FraudReport):
    """
    Create CEO inbox item for fraud investigation.
    """
    h = get_heuristic(heuristic_id)

    # Generate detailed report
    report_content = f"""# Fraud Detection Alert: {h.domain} - {h.rule}

## Classification: {fraud_report.classification.upper()}
**Fraud Score:** {fraud_report.fraud_score:.1%}
**Likelihood Ratio:** {fraud_report.likelihood_ratio:.2f}
**Detection Date:** {fraud_report.timestamp}

## Heuristic Details
- **ID:** {h.id}
- **Domain:** {h.domain}
- **Rule:** {h.rule}
- **Current Confidence:** {h.confidence:.2f}
- **Status:** {h.status}
- **Validations:** {h.times_validated}
- **Violations:** {h.times_violated}
- **Contradictions:** {h.times_contradicted}

## Detected Anomalies

"""
    for signal in fraud_report.signals:
        report_content += f"""### {signal.algorithm} ({signal.severity})
**Score:** {signal.score:.2f}
**Reason:** {signal.reason}

"""

    report_content += f"""## Automatic Actions Taken
- Confidence freeze: {"YES" if h.is_quarantined else "NO"}
- Rate limit tightened: [Check fraud_responses table]

## CEO Decision Required

Please review the evidence and choose:

1. **False Positive** - Unfreeze heuristic, restore normal operation
2. **True Positive - Minor** - Keep frozen, tighten rate limits, monitor
3. **True Positive - Major** - Reset confidence, deprecate, or delete
4. **Need More Data** - Keep frozen, run for 30 more days, re-evaluate

### Decision
[ ] False Positive
[ ] True Positive - Minor
[ ] True Positive - Major
[ ] Need More Data

**Notes:**

---

**File:** `ceo-inbox/{datetime.now().strftime('%Y-%m-%d')}-fraud-alert-{h.id}.md`
"""

    # Write to ceo-inbox
    inbox_path = Path.home() / ".claude/emergent-learning/ceo-inbox"
    filename = f"{datetime.now().strftime('%Y-%m-%d')}-fraud-alert-h{h.id}.md"

    with open(inbox_path / filename, 'w') as f:
        f.write(report_content)

    # Record escalation
    conn.execute("""
        INSERT INTO fraud_responses
        (fraud_report_id, response_type, parameters, executed_by)
        VALUES (?, 'ceo_escalation', ?, 'system')
    """, (fraud_report.id, json.dumps({"inbox_file": str(filename)})))
```

### 5.6 Remediation Strategies

After CEO review, possible remediation paths:

**Path 1: False Positive**
```python
def clear_false_positive(fraud_report_id: int):
    # Mark as reviewed
    conn.execute("""
        UPDATE fraud_reports SET
            reviewed_at = CURRENT_TIMESTAMP,
            reviewed_by = 'ceo',
            review_outcome = 'false_positive'
        WHERE id = ?
    """, (fraud_report_id,))

    # Unfreeze heuristic
    heuristic_id = get_fraud_report(fraud_report_id).heuristic_id
    conn.execute("""
        UPDATE heuristics SET
            is_quarantined = 0,
            quarantine_reason = NULL,
            quarantine_since = NULL
        WHERE id = ?
    """, (heuristic_id,))

    # Remove rate overrides
    conn.execute("DELETE FROM heuristic_rate_overrides WHERE heuristic_id = ?",
                 (heuristic_id,))

    # Update detection algorithm (this is a false positive signal for learning)
    update_detection_parameters(fraud_report_id, outcome='false_positive')
```

**Path 2: True Positive - Remediate**
```python
def remediate_fraud(fraud_report_id: int, action: str):
    heuristic_id = get_fraud_report(fraud_report_id).heuristic_id

    if action == 'reset_confidence':
        reset_confidence(heuristic_id, fraud_report_id,
                        "CEO decision: confidence manipulation confirmed")

    elif action == 'deprecate':
        conn.execute("""
            UPDATE heuristics SET
                status = 'deprecated',
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (heuristic_id,))

    elif action == 'delete':
        # Soft delete (archive, don't actually remove)
        conn.execute("""
            UPDATE heuristics SET
                status = 'archived',
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (heuristic_id,))

    # Mark as reviewed
    conn.execute("""
        UPDATE fraud_reports SET
            reviewed_at = CURRENT_TIMESTAMP,
            reviewed_by = 'ceo',
            review_outcome = 'true_positive'
        WHERE id = ?
    """, (fraud_report_id,))

    # Update detection algorithm (this is a true positive signal for learning)
    update_detection_parameters(fraud_report_id, outcome='true_positive')
```

---

## 6. Edge Cases & Failure Modes

### 6.1 Legitimate High Success Rates

**Scenario:** Golden rule with genuinely 95%+ success rate flagged as fraud.

**Mitigation:**
- Whitelist golden rules (is_golden = 1) from success rate anomaly detector
- Require MULTIPLE signals for fraud_confirmed (not just high success rate)
- CEO review for all high-confidence detections
- Track false positive rate, tune thresholds

### 6.2 Domain-Specific Baselines

**Scenario:** "Security" domain has naturally high success rates (good practices work). System flags all security heuristics.

**Mitigation:**
- Use domain-specific baselines, not global
- Require sufficient sample size (10+ heuristics) before establishing baseline
- Compare to percentiles within domain, not absolute thresholds
- Allow manual baseline adjustments per domain

### 6.3 Legitimate Coordinated Work

**Scenario:** Team of agents working on same project legitimately validates same heuristics.

**Mitigation:**
- Multi-agent flag requires temporal correlation + pattern similarity
- Don't flag if agents have different success rates (legitimate learning)
- Weight by diversity of update types (all success = suspicious, mixed = normal)
- CEO can whitelist agent groups for specific domains

### 6.4 Seasonal/Cyclical Work

**Scenario:** "Tax" domain heuristics used heavily in March-April, dormant rest of year. Revival pattern looks suspicious.

**Mitigation:**
- Track seasonal patterns in domain baselines
- Revival frequency normalized by time-since-creation (not absolute count)
- Require concentration (same agent reviving) for fraud flag
- Context-aware thresholds (revival during "tax season" = normal)

### 6.5 New Heuristics (Cold Start)

**Scenario:** Newly added heuristic has <10 applications, insufficient data for most detectors.

**Mitigation:**
- Minimum application count requirements for each detector
- Return "insufficient_data" instead of "normal" (distinguishable)
- Lighter-weight monitoring for new heuristics (temporal patterns only)
- Grace period (first 30 days) with reduced sensitivity

### 6.6 Detector Gaming

**Scenario:** Adversary learns detection algorithms and adapts manipulation to avoid them.

**Mitigation:**
- Don't expose detector thresholds publicly
- Randomize thresholds slightly (±10%) per heuristic
- Use ensemble of algorithms (hard to evade all simultaneously)
- Continuous learning: update algorithms as new attack patterns emerge
- CEO review provides human judgment layer

### 6.7 False Positive Cascade

**Scenario:** Detection tuning error causes mass false positives, freezes half the heuristics.

**Mitigation:**
- Conservative phase: Manual review before enforcement
- Rate-limit fraud responses (max 5 freezes per day)
- Alert CEO if >10 heuristics quarantined in 24h (likely detector bug)
- Easy batch unfreeze mechanism for CEO
- Rollback mechanism: undo last N fraud responses

```python
def check_fraud_response_rate():
    """Safety: prevent runaway fraud detector."""
    recent_freezes = conn.execute("""
        SELECT COUNT(*) FROM fraud_responses
        WHERE response_type IN ('confidence_freeze', 'status_quarantine')
          AND executed_at > datetime('now', '-24 hours')
    """).fetchone()[0]

    if recent_freezes > 10:
        # Alert CEO
        escalate_detector_malfunction(f"{recent_freezes} heuristics quarantined in 24h")
        # Disable auto-enforcement
        set_detector_mode('manual_review_only')
```

### 6.8 Context Tracking Privacy

**Scenario:** Storing session contexts raises privacy concerns (user queries may be sensitive).

**Mitigation:**
- Hash sensitive content, store only hashes for deduplication
- Truncate contexts to first 500 chars (enough for keyword matching)
- Encrypt context_text column
- Retention policy: delete contexts older than 90 days
- Allow users to opt out (disables application_selectivity detector only)

### 6.9 Performance Impact

**Scenario:** Running 6 detection algorithms on every heuristic update is too slow.

**Mitigation:**
- Run detectors asynchronously (background job)
- Tier detectors: Fast detectors on every update, slow detectors nightly
  - Fast: Success rate, temporal patterns (O(log n) queries)
  - Slow: Multi-agent correlation, confidence trajectory (O(n) scans)
- Cache domain baselines (update monthly, not on-demand)
- Index all foreign keys, timestamps
- Batch analyze: Check 100 heuristics per run, not all 1000+

**Tiered Schedule:**
```python
# On every confidence update (synchronous)
- Check is_quarantined flag (instant)

# After every confidence update (async background job)
- detect_success_rate_anomaly (fast: 1 query)
- detect_temporal_manipulation (fast: 1 query + calculation)

# Nightly batch job (12am)
- detect_coordinated_manipulation (moderate: joins)
- detect_unnatural_confidence_growth (moderate: trajectory analysis)
- detect_application_selectivity (slow: FTS search)
- detect_revival_gaming (fast: 2 queries)

# Weekly (Sunday midnight)
- Update domain baselines
- Retune detector thresholds based on false positive rate
```

---

## 7. Test Scenarios

### 7.1 Test 1: Pump-and-Dump Detection

**Setup:**
```python
# Create mediocre heuristic
h_id = create_heuristic("testing", "Mediocre rule", confidence=0.35)

# Simulate pump-and-dump
for day in range(7):
    for update in range(5):
        # Wait exactly 61 minutes (just past cooldown)
        time.sleep(61 * 60)
        update_confidence(h_id, UpdateType.SUCCESS,
                         session_id="attacker", agent_id="agent_malicious")
```

**Expected Detection:**
- `detect_temporal_manipulation()` → score >0.7 (cooldown clustering)
- `detect_success_rate_anomaly()` → score >0.6 (100% success rate)
- `detect_unnatural_confidence_growth()` → score >0.5 (monotonic, smooth)
- **Combined fraud_score:** >0.8 (fraud_confirmed)

**Expected Response:**
- Heuristic quarantined
- CEO escalation created
- Rate limits tightened (if not already quarantined)

---

### 7.2 Test 2: Selective Validation

**Setup:**
```python
# Create heuristic about "caching"
h_id = create_heuristic("performance", "Use Redis for caching", confidence=0.5)

# Log many contexts mentioning "cache" / "Redis"
for i in range(50):
    log_session_context(f"Task {i}: optimize cache performance with Redis")

# Only apply heuristic to 3 of them (selective)
for i in [5, 12, 33]:  # Cherry-picked easy tasks
    update_confidence(h_id, UpdateType.SUCCESS)
```

**Expected Detection:**
- `detect_application_selectivity()` → score >0.7 (3/50 = 6% application rate)
- **Combined fraud_score:** >0.5 (fraud_likely)

**Expected Response:**
- Warning logged
- CEO notification (not immediate quarantine)

---

### 7.3 Test 3: Coordinated Manipulation

**Setup:**
```python
# Create target heuristic
h_id = create_heuristic("security", "Validate all inputs", confidence=0.5)

# 5 different agents coordinate
for agent_id in ["agent1", "agent2", "agent3", "agent4", "agent5"]:
    for _ in range(5):
        update_confidence(h_id, UpdateType.SUCCESS,
                         agent_id=agent_id,
                         session_id=f"session_{agent_id}")
```

**Expected Detection:**
- `detect_coordinated_manipulation()` → score >0.8 (5 agents, all successes)
- **Combined fraud_score:** >0.7 (fraud_likely or fraud_confirmed)

**Expected Response:**
- Quarantine
- CEO escalation

---

### 7.4 Test 4: Revival Gaming

**Setup:**
```python
# Create heuristic, make dormant
h_id = create_heuristic("embedded", "Use interrupts", confidence=0.45)
make_dormant(h_id)

# Same agent repeatedly revives and re-dormates
for cycle in range(5):
    revive_heuristic(h_id, agent_id="agent_cycler")
    # Apply only to easy tasks
    for _ in range(3):
        update_confidence(h_id, UpdateType.SUCCESS, agent_id="agent_cycler")
    # Let decay back to dormant
    make_dormant(h_id)
```

**Expected Detection:**
- `detect_revival_gaming()` → score >0.6 (5 revivals, same agent, high post-revival success)
- **Combined fraud_score:** >0.5 (fraud_likely)

**Expected Response:**
- Rate limit tightening on revivals
- CEO notification

---

### 7.5 Test 5: False Positive - Golden Rule

**Setup:**
```python
# Create golden rule (genuinely excellent)
h_id = create_heuristic("git", "Always commit before branching",
                       confidence=0.92, is_golden=True)

# Apply to 100 tasks, 95 successes (legitimately good)
for i in range(95):
    update_confidence(h_id, UpdateType.SUCCESS, force=True)
for i in range(5):
    update_confidence(h_id, UpdateType.FAILURE, force=True)
```

**Expected Detection:**
- `detect_success_rate_anomaly()` → score >0.6 (95% success)
- BUT: Whitelisted because is_golden=True
- **Combined fraud_score:** 0.0 (clean)

**Expected Response:**
- No action

---

### 7.6 Test 6: Timing Attack - Midnight Reset Gaming

**Setup:**
```python
# Create heuristic
h_id = create_heuristic("testing", "Test rule", confidence=0.5)

# Game daily reset: 5 updates before midnight, 5 after
for hour in [22, 22.5, 23, 23.5, 23.9]:  # Day 1
    set_system_time(hour)
    update_confidence(h_id, UpdateType.SUCCESS, agent_id="attacker")

for hour in [0.1, 0.5, 1, 1.5, 2]:  # Day 2
    set_system_time(hour)
    update_confidence(h_id, UpdateType.SUCCESS, agent_id="attacker")

# Result: 10 updates in ~4 hours, despite 5/day limit
```

**Expected Detection:**
- `detect_temporal_manipulation()` → score >0.8 (midnight clustering)
- **Combined fraud_score:** >0.7 (fraud_likely)

**Expected Response:**
- Quarantine
- CEO escalation

---

### 7.7 Test 7: Legitimate Team Work (No False Positive)

**Setup:**
```python
# Create heuristic
h_id = create_heuristic("python", "Use type hints", confidence=0.6)

# 3 agents apply it legitimately with mixed results
agents = ["alice", "bob", "charlie"]
for agent in agents:
    for _ in range(10):
        # Realistic: ~70% success rate
        update_type = UpdateType.SUCCESS if random() < 0.7 else UpdateType.FAILURE
        update_confidence(h_id, update_type, agent_id=agent)
```

**Expected Detection:**
- `detect_coordinated_manipulation()` checks:
  - Multiple agents: YES (3 agents)
  - Pattern similarity: NO (mixed success/failure, different rates)
  - Temporal correlation: MODERATE
- **Combined fraud_score:** <0.2 (low_confidence or clean)

**Expected Response:**
- No action (legitimate collaboration)

---

## 8. Implementation Estimate

### 8.1 Lines of Code

| Component | Estimated LOC | Complexity |
|-----------|---------------|------------|
| Detection algorithms (6 detectors) | 600 | Medium-High |
| Anomaly scoring & Bayesian fusion | 200 | High |
| Schema migrations (SQL) | 300 | Low |
| Response actions | 250 | Medium |
| CEO escalation formatting | 150 | Low |
| Baseline calculation & maintenance | 200 | Medium |
| Test suite (7 scenarios) | 800 | Medium |
| CLI interface | 150 | Low |
| **TOTAL** | **~2,650 LOC** | **Medium-High** |

### 8.2 Complexity Rating

**Overall: 7/10** (High complexity)

**Breakdown:**
- **Data structures:** 6/10 (multiple new tables, complex joins)
- **Algorithms:** 8/10 (statistical analysis, Bayesian fusion, pattern detection)
- **Integration:** 6/10 (hooks into existing lifecycle_manager.py)
- **Testing:** 7/10 (adversarial scenarios, false positive validation)
- **Maintenance:** 7/10 (threshold tuning, baseline updates, algorithm evolution)

**Risk Factors:**
- False positive rate tuning will require iteration
- Domain baseline calculation needs sufficient data (cold start problem)
- Performance impact of running 6 detectors (mitigated by async + tiering)
- Adversarial adaptation (attackers will learn and evolve)

### 8.3 Dependencies

**Python Standard Library:**
- `sqlite3` - Database operations
- `statistics` - Mean, variance, stdev calculations
- `datetime` - Temporal analysis
- `json` - Metadata storage
- `collections` - Counter, defaultdict

**No External Dependencies Required** (everything in stdlib)

**New Database Requirements:**
- SQLite FTS5 (full-text search for context keyword matching)
- If FTS5 unavailable (Windows/MSYS), fallback to FTS4 or LIKE queries

### 8.4 Implementation Phases

**Phase 2A: Core Detection (Week 1-2)**
- Implement 6 detection algorithms
- Schema migration
- Unit tests for each detector

**Phase 2B: Scoring & Response (Week 3)**
- Bayesian fusion system
- Response actions (freeze, reset, escalate)
- Integration with lifecycle_manager.py

**Phase 2C: Baselines & Tuning (Week 4)**
- Domain baseline calculation
- Cold start handling
- Threshold tuning based on test data

**Phase 2D: Production Hardening (Week 5)**
- Performance optimization (async, tiering)
- False positive mitigation
- CEO escalation formatting
- Full test suite (7 scenarios)

**Total Estimated Time: 4-5 weeks** (for single developer)

---

## 9. FINDINGS

### [fact] Current System Protections
- Phase 1 implements: Rate limiting (5/day, 60-min cooldown), confidence bounds (0.05-0.95), symmetric updates, rate-based contradictions (>30% over 10+ apps), eviction policy, dormant recovery
- Audit trail exists: `confidence_updates` table tracks all changes with session_id, agent_id, timestamps
- Schema supports extensions: Can add columns to existing tables without breaking changes

### [fact] Attack Surface Remains
- **Selective validation** is completely undefended (no context tracking yet)
- **Timing attacks** exploit cooldown/daily reset boundaries (rate limiting checks cooldown but doesn't analyze patterns)
- **Coordinated manipulation** undetected (no multi-agent analysis)
- **Pattern exploitation** possible (decay/revival cycles can be gamed)

### [hypothesis] Bayesian Fusion Effectiveness
- Combining weak signals (each 50-70% accurate) via Bayesian fusion should yield >90% accuracy
- Assumption: Signals are conditionally independent (may not hold in practice)
- Needs validation: Track false positive/negative rates in production
- Alternative: Could use ML classifier (logistic regression) if Bayesian approach shows poor performance

### [hypothesis] Domain Baselines Will Stabilize
- Assumption: Each domain has stable statistical properties (avg success rate, update frequency)
- Risk: Small domains (<10 heuristics) will have high variance in baselines
- Mitigation: Require minimum sample size (10), fallback to global baseline for small domains
- Alternative: Hierarchical Bayesian model (domain-specific + global priors)

### [hypothesis] Performance Impact Manageable
- Fast detectors (success rate, temporal) can run synchronously: <10ms overhead
- Slow detectors (multi-agent, selectivity) deferred to nightly batch: <1s per heuristic
- Assumption: Heuristic count stays <10,000 (nightly batch completes in <3 hours)
- Needs monitoring: If heuristic count grows significantly, may need distributed processing

### [blocker] Context Tracking Not Yet Implemented
- `detect_application_selectivity()` requires session_contexts table
- Needs integration point: Where to capture user queries/task descriptions?
- Options:
  1. Hook into query.py --context calls
  2. Instrument Claude agent to log every user message
  3. Parse JSONL session files retroactively
- **CEO decision needed:** Is context tracking acceptable? Privacy implications?

### [blocker] False Positive Tolerance Unclear
- What false positive rate is acceptable? 1%? 5%? 10%?
- Trade-off: Tighter thresholds = fewer false positives but more false negatives
- **CEO decision needed:** Conservative (catch 60%, 1% FP) or aggressive (catch 90%, 5% FP)?

### [question] Golden Rule Whitelist Scope
- Should ALL golden rules be whitelisted from fraud detection?
- Or only whitelist from specific detectors (e.g., success_rate but not temporal)?
- Risk: Attacker could manipulate heuristic to golden status, then exploit
- **CEO decision needed:** Full whitelist, partial whitelist, or no whitelist?

### [question] Quarantine vs. Soft Limits
- Current design: fraud_confirmed → hard quarantine (complete freeze)
- Alternative: fraud_likely → soft limits (allow 1 update/week, not 5/day)
- Softer approach may reduce false positive impact
- **CEO decision needed:** Hard freeze or graduated response?

### [question] Adversarial Adaptation Timeline
- How long until sophisticated attackers learn detection algorithms?
- If thresholds/algorithms are visible in open source, immediate
- If kept private, 3-6 months based on trial-and-error
- Should detection algorithms be open-sourced or kept proprietary?
- **CEO decision needed:** Transparency vs. security-through-obscurity?

### [fact] Schema Changes Are Additive
- All new tables (fraud_reports, anomaly_signals, domain_baselines, session_contexts)
- Minimal changes to existing tables (4 new columns on heuristics, 2 on confidence_updates)
- Migration is reversible (can drop new tables/columns without data loss on old schema)
- **No breaking changes to Phase 1 functionality**

### [hypothesis] Detector Ensemble Robustness
- Using 6 different algorithms makes evasion harder (must evade ALL to avoid detection)
- Each detector has different blind spots, ensemble covers more attack surface
- Risk: Correlated detectors (e.g., success_rate and confidence_growth both flag same thing)
- May need to test detector independence empirically

### [question] Baseline Update Frequency
- Current design: Update domain baselines monthly
- Too frequent: Attacker can slowly shift baseline (boiling frog)
- Too infrequent: Legitimate domain evolution (new tools, practices) not reflected
- **CEO decision needed:** Monthly, quarterly, or adaptive (update when domain changes >10%)?

### [fact] Test Coverage Identifies 7 Scenarios
- 3 attack scenarios (pump-and-dump, selective validation, coordinated)
- 2 edge cases (golden rule false positive, legitimate teamwork)
- 2 advanced attacks (revival gaming, timing attack)
- **Missing:** Cross-domain attacks, slow burn (just under thresholds), detector evasion
- **Recommendation:** Add 3 more tests for completeness

### [hypothesis] CEO Review Overhead Is Manageable
- Estimated escalation rate: 1-5% of heuristics (if 100 heuristics, 1-5 escalations)
- Each review takes ~10 minutes (read report, check evidence, decide)
- Total: 10-50 minutes per week
- **Acceptable if escalation rate <5%**
- If escalation rate >10%, detector is too sensitive (tune down)

### [blocker] FTS5 Availability on Windows
- SQLite FTS5 not available in default Python SQLite on Windows/MSYS (learned from spike report)
- Options:
  1. Use FTS4 (available, different syntax)
  2. Use LIKE queries (slower, but works)
  3. Require FTS5 compile (complex install)
- **Recommendation:** Implement with FTS4 fallback for Windows compatibility

---

## Appendix: Pseudocode Summary

```python
# Main fraud detection flow
def run_fraud_detection(heuristic_id: int) -> FraudReport:
    # Run all detectors
    signals = [
        detect_success_rate_anomaly(heuristic_id),
        detect_temporal_manipulation(heuristic_id),
        detect_coordinated_manipulation(heuristic_id),
        detect_unnatural_confidence_growth(heuristic_id),
        detect_application_selectivity(heuristic_id),
        detect_revival_gaming(heuristic_id)
    ]

    # Bayesian fusion
    fraud_score = bayesian_combine(signals, prior=0.05)

    # Classify
    classification = classify_fraud_score(fraud_score)

    # Store report
    report_id = store_fraud_report(heuristic_id, fraud_score, classification, signals)

    # Take action
    if classification == "fraud_confirmed":
        freeze_confidence(heuristic_id, report_id)
        escalate_to_ceo(heuristic_id, report_id)
    elif classification == "fraud_likely":
        tighten_rate_limits(heuristic_id, report_id)
        escalate_to_ceo(heuristic_id, report_id)
    elif classification == "suspicious":
        log_warning(heuristic_id, report_id)

    return FraudReport(...)

# Integration point: After every confidence update
def update_confidence(...):
    # Phase 1 logic (existing)
    result = phase1_update_confidence(...)

    # Phase 2: Async fraud detection
    if result["success"]:
        schedule_background_job(run_fraud_detection, heuristic_id)

    return result
```

---

**END OF DESIGN DOCUMENT**
