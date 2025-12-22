# Adaptive Threshold Tuning Design - Phase 2D Agent 2
## Fraud Detection System Enhancement

**Author:** Agent 2 (Phase 3 Swarm)
**Date:** 2025-12-13
**Status:** Design Proposal
**Prerequisites:** Phase 2D fraud detection with TP/FP tracking

---

## Executive Summary

The current fraud detection system uses fixed thresholds for classification:
- `suspicious`: fraud_score > 0.20
- `fraud_likely`: fraud_score > 0.50
- `fraud_confirmed`: fraud_score > 0.80

These fixed values cannot adapt to:
- Different domain characteristics (security domain may need tighter thresholds)
- Varying false positive tolerance over time
- Actual observed performance (TP/FP rates)
- Seasonal patterns or system evolution

This design proposes an **adaptive threshold tuning system** that:
1. Analyzes accumulated TP/FP data per detector
2. Calculates optimal thresholds to meet target FPR (false positive rate)
3. Generates recommendations for CEO review
4. Maintains threshold history for rollback capability
5. Never auto-applies changes (conservative, human-in-loop approach)

---

## 1. Core Concepts

### 1.1 Problem Statement

**Fixed thresholds are suboptimal because:**
- Different detectors have different precision characteristics
  - Example: `success_rate_anomaly` may have 2% FPR at threshold 0.20
  - Example: `temporal_manipulation` may have 10% FPR at same threshold 0.20
- Domain-specific baselines vary
  - Security domain: Naturally high success rates (thresholds should be higher)
  - Experimental domain: Wide variance in success rates (thresholds should be lower)
- System evolves over time
  - As heuristics mature, fraud patterns change
  - Attackers adapt to detection (need threshold adjustment)

**What we need:**
- Per-detector thresholds optimized for target FPR
- Per-domain threshold adjustments
- Periodic re-evaluation based on new TP/FP data
- Human review before applying changes

### 1.2 Design Philosophy

**Conservative Approach:**
- NEVER auto-apply threshold changes
- Generate recommendations only
- CEO reviews and approves all changes
- Maintain rollback capability
- Require minimum sample size (N observations) before tuning

**Statistical Foundation:**
- Use empirical TP/FP rates from actual fraud_reports data
- Calculate thresholds that achieve target FPR (e.g., 5%)
- Bayesian or frequentist approach (both options documented)
- Confidence intervals to indicate uncertainty

**Safety Bounds:**
- Never suggest thresholds below minimum (e.g., 0.10 for suspicious)
- Never suggest thresholds above maximum (e.g., 0.95 for confirmed)
- Require minimum separation between tiers (e.g., suspicious < likely < confirmed)
- Gradual adjustment only (max ±0.10 change per update)

---

## 2. Algorithm Design

### 2.1 Data Collection

**Input: Reviewed fraud reports with outcomes**

```sql
-- Get all reviewed fraud reports with ground truth
SELECT
    fr.id,
    fr.heuristic_id,
    fr.fraud_score,
    fr.classification,
    fr.review_outcome,  -- 'true_positive' or 'false_positive'
    h.domain,
    fr.created_at
FROM fraud_reports fr
JOIN heuristics h ON fr.heuristic_id = h.id
WHERE fr.review_outcome IN ('true_positive', 'false_positive')
ORDER BY fr.created_at DESC;
```

**Per-detector signal data:**

```sql
-- Get signal-level TP/FP data for a specific detector
SELECT
    asig.detector_name,
    asig.score,
    fr.review_outcome,
    h.domain
FROM anomaly_signals asig
JOIN fraud_reports fr ON asig.fraud_report_id = fr.id
JOIN heuristics h ON asig.heuristic_id = h.id
WHERE fr.review_outcome IN ('true_positive', 'false_positive')
  AND asig.detector_name = ?
ORDER BY asig.score ASC;
```

### 2.2 Frequentist Approach (Recommended)

**Rationale:** Simple, interpretable, requires less data than Bayesian

**Algorithm:**
1. Collect all (score, outcome) pairs for a detector
2. Sort by score ascending
3. For each potential threshold t:
   - Count TP: outcomes='true_positive' where score ≥ t
   - Count FP: outcomes='false_positive' where score ≥ t
   - Count TN: outcomes='false_positive' where score < t
   - Count FN: outcomes='true_positive' where score < t
4. Calculate FPR = FP / (FP + TN)
5. Calculate TPR = TP / (TP + FN)
6. Select threshold t where FPR ≤ target_fpr and TPR is maximized

**Pseudocode:**

```python
def calculate_optimal_threshold_frequentist(
    detector_name: str,
    target_fpr: float = 0.05,
    min_samples: int = 30
) -> Dict[str, Any]:
    """
    Calculate optimal threshold for a detector using frequentist approach.

    Args:
        detector_name: Which detector to tune (e.g., 'success_rate_anomaly')
        target_fpr: Maximum acceptable false positive rate (default 5%)
        min_samples: Minimum reviewed samples required (default 30)

    Returns:
        {
            'detector_name': str,
            'current_threshold': float,  # From config
            'recommended_threshold': float,
            'target_fpr': float,
            'achieved_fpr': float,  # Actual FPR at recommended threshold
            'achieved_tpr': float,  # TPR at recommended threshold
            'sample_size': int,
            'tp_count': int,
            'fp_count': int,
            'confidence': str,  # 'low', 'medium', 'high' based on sample size
            'reason': str,
            'evaluated_at': datetime
        }
    """

    # Get signal data
    signals = db.execute("""
        SELECT asig.score, fr.review_outcome
        FROM anomaly_signals asig
        JOIN fraud_reports fr ON asig.fraud_report_id = fr.id
        WHERE fr.review_outcome IN ('true_positive', 'false_positive')
          AND asig.detector_name = ?
        ORDER BY asig.score ASC
    """, (detector_name,)).fetchall()

    if len(signals) < min_samples:
        return {
            'detector_name': detector_name,
            'error': 'insufficient_data',
            'sample_size': len(signals),
            'min_required': min_samples,
            'reason': f'Need {min_samples - len(signals)} more reviewed samples'
        }

    # Extract scores and labels
    scores = [s['score'] for s in signals]
    outcomes = [1 if s['review_outcome'] == 'true_positive' else 0
                for s in signals]

    # Total positives and negatives
    total_positives = sum(outcomes)
    total_negatives = len(outcomes) - total_positives

    # Try all unique score values as potential thresholds
    candidate_thresholds = sorted(set(scores))

    best_threshold = None
    best_tpr = 0
    best_fpr = 1.0

    for threshold in candidate_thresholds:
        # Count TP, FP, TN, FN
        tp = sum(1 for score, outcome in zip(scores, outcomes)
                 if score >= threshold and outcome == 1)
        fp = sum(1 for score, outcome in zip(scores, outcomes)
                 if score >= threshold and outcome == 0)
        tn = total_negatives - fp
        fn = total_positives - tp

        # Calculate rates
        fpr = fp / (fp + tn) if (fp + tn) > 0 else 0
        tpr = tp / (tp + fn) if (tp + fn) > 0 else 0

        # Select if FPR within target and TPR better than current best
        if fpr <= target_fpr and tpr > best_tpr:
            best_threshold = threshold
            best_tpr = tpr
            best_fpr = fpr

    # If no threshold meets target_fpr, select most conservative
    # (highest threshold with lowest FPR)
    if best_threshold is None:
        for threshold in reversed(candidate_thresholds):
            tp = sum(1 for score, outcome in zip(scores, outcomes)
                     if score >= threshold and outcome == 1)
            fp = sum(1 for score, outcome in zip(scores, outcomes)
                     if score >= threshold and outcome == 0)
            tn = total_negatives - fp
            fn = total_positives - tp
            fpr = fp / (fp + tn) if (fp + tn) > 0 else 0
            tpr = tp / (tp + fn) if (tp + fn) > 0 else 0

            if threshold >= 0.10:  # Minimum bound
                best_threshold = threshold
                best_tpr = tpr
                best_fpr = fpr
                break

    # Determine confidence based on sample size
    if len(signals) >= 100:
        confidence = 'high'
    elif len(signals) >= 50:
        confidence = 'medium'
    else:
        confidence = 'low'

    # Get current threshold from config
    current_threshold = get_current_detector_threshold(detector_name)

    return {
        'detector_name': detector_name,
        'current_threshold': current_threshold,
        'recommended_threshold': best_threshold,
        'target_fpr': target_fpr,
        'achieved_fpr': best_fpr,
        'achieved_tpr': best_tpr,
        'sample_size': len(signals),
        'tp_count': total_positives,
        'fp_count': total_negatives,
        'confidence': confidence,
        'reason': f'Achieves {best_fpr:.1%} FPR (target {target_fpr:.1%}) with {best_tpr:.1%} TPR',
        'evaluated_at': datetime.now()
    }
```

### 2.3 Bayesian Approach (Alternative)

**Rationale:** Better for small sample sizes, incorporates prior knowledge

**Algorithm:**
1. Define prior distribution for threshold (Beta distribution)
2. Update with observed TP/FP data (Beta-Binomial conjugate)
3. Compute posterior distribution
4. Select threshold that maximizes expected utility
   - Utility function: U = TPR - λ * FPR (λ controls FP penalty)

**Pseudocode:**

```python
def calculate_optimal_threshold_bayesian(
    detector_name: str,
    target_fpr: float = 0.05,
    min_samples: int = 20,  # Lower requirement due to prior
    prior_alpha: float = 5,  # Prior successes (true positives)
    prior_beta: float = 1    # Prior failures (false positives)
) -> Dict[str, Any]:
    """
    Calculate optimal threshold using Bayesian approach.

    Uses Beta prior and Beta-Binomial posterior.
    Better for small sample sizes.
    """
    from scipy.stats import beta

    # Get signal data (same as frequentist)
    signals = get_detector_signals(detector_name)

    if len(signals) < min_samples:
        return {'error': 'insufficient_data'}

    # Sort by score
    sorted_signals = sorted(signals, key=lambda x: x['score'])

    # For each potential threshold, compute posterior
    candidate_thresholds = sorted(set(s['score'] for s in signals))

    best_threshold = None
    best_utility = -float('inf')

    for threshold in candidate_thresholds:
        # Count TP and FP above threshold
        tp = sum(1 for s in signals
                 if s['score'] >= threshold and s['outcome'] == 'true_positive')
        fp = sum(1 for s in signals
                 if s['score'] >= threshold and s['outcome'] == 'false_positive')

        # Update Beta prior with observed data
        # Posterior: Beta(alpha + tp, beta + fp)
        posterior_alpha = prior_alpha + tp
        posterior_beta = prior_beta + fp

        # Posterior mean (expected precision)
        precision = posterior_alpha / (posterior_alpha + posterior_beta)

        # Expected FPR (1 - precision)
        expected_fpr = 1 - precision

        # Expected TPR (proportion detected)
        total_positives = sum(1 for s in signals if s['outcome'] == 'true_positive')
        expected_tpr = tp / total_positives if total_positives > 0 else 0

        # Utility function: Maximize TPR while penalizing FPR
        # λ = 1/target_fpr gives appropriate penalty
        lambda_penalty = 1 / target_fpr
        utility = expected_tpr - lambda_penalty * expected_fpr

        if utility > best_utility and threshold >= 0.10:
            best_utility = utility
            best_threshold = threshold
            best_fpr = expected_fpr
            best_tpr = expected_tpr

    return {
        'detector_name': detector_name,
        'recommended_threshold': best_threshold,
        'achieved_fpr': best_fpr,
        'achieved_tpr': best_tpr,
        'confidence': 'medium',  # Bayesian gives uncertainty estimate
        'approach': 'bayesian',
        'prior': f'Beta({prior_alpha}, {prior_beta})'
    }
```

**Recommendation:** Use **frequentist approach** as primary, Bayesian as fallback for small samples.

### 2.4 Classification Threshold Tuning

The fraud detection system has THREE threshold levels:
1. `suspicious` (>0.20): Log warning, monitor
2. `fraud_likely` (>0.50): Tighten rate limits, CEO notification
3. `fraud_confirmed` (>0.80): Quarantine, CEO escalation

**How to tune these:**

```python
def calculate_optimal_classification_thresholds(
    target_fpr_suspicious: float = 0.10,  # Allow 10% FP for warnings
    target_fpr_likely: float = 0.05,      # Allow 5% FP for rate limits
    target_fpr_confirmed: float = 0.01,   # Allow 1% FP for quarantine
    min_samples: int = 50
) -> Dict[str, Any]:
    """
    Calculate optimal classification thresholds based on fraud_score.

    Uses combined fraud_score (Bayesian posterior) not individual detector scores.
    """

    # Get all reviewed fraud reports
    reports = db.execute("""
        SELECT fraud_score, review_outcome
        FROM fraud_reports
        WHERE review_outcome IN ('true_positive', 'false_positive')
        ORDER BY fraud_score ASC
    """).fetchall()

    if len(reports) < min_samples:
        return {'error': 'insufficient_data', 'sample_size': len(reports)}

    scores = [r['fraud_score'] for r in reports]
    outcomes = [1 if r['review_outcome'] == 'true_positive' else 0
                for r in reports]

    # Calculate three thresholds
    thresholds = {}

    for level, target_fpr in [
        ('suspicious', target_fpr_suspicious),
        ('fraud_likely', target_fpr_likely),
        ('fraud_confirmed', target_fpr_confirmed)
    ]:
        result = find_threshold_for_fpr(scores, outcomes, target_fpr)
        thresholds[level] = result

    # Enforce ordering: suspicious < likely < confirmed
    thresholds = enforce_threshold_ordering(thresholds)

    # Enforce safety bounds
    thresholds = apply_safety_bounds(thresholds)

    return {
        'suspicious': thresholds['suspicious'],
        'fraud_likely': thresholds['fraud_likely'],
        'fraud_confirmed': thresholds['fraud_confirmed'],
        'evaluated_at': datetime.now(),
        'sample_size': len(reports)
    }

def find_threshold_for_fpr(scores, outcomes, target_fpr):
    """Helper: Find threshold that achieves target FPR."""
    total_negatives = sum(1 for o in outcomes if o == 0)
    total_positives = sum(1 for o in outcomes if o == 1)

    candidate_thresholds = sorted(set(scores))

    for threshold in candidate_thresholds:
        fp = sum(1 for s, o in zip(scores, outcomes)
                 if s >= threshold and o == 0)
        tp = sum(1 for s, o in zip(scores, outcomes)
                 if s >= threshold and o == 1)

        fpr = fp / total_negatives if total_negatives > 0 else 0
        tpr = tp / total_positives if total_positives > 0 else 0

        if fpr <= target_fpr:
            return {
                'threshold': threshold,
                'fpr': fpr,
                'tpr': tpr
            }

    # No threshold meets target, return most conservative
    return {
        'threshold': max(candidate_thresholds),
        'fpr': 0,
        'tpr': 0,
        'warning': 'Could not meet target FPR, using maximum threshold'
    }

def enforce_threshold_ordering(thresholds):
    """Ensure suspicious < likely < confirmed."""
    sus = thresholds['suspicious']['threshold']
    likely = thresholds['fraud_likely']['threshold']
    confirmed = thresholds['fraud_confirmed']['threshold']

    # If ordering violated, adjust
    if likely <= sus:
        likely = sus + 0.05
    if confirmed <= likely:
        confirmed = likely + 0.10

    thresholds['fraud_likely']['threshold'] = likely
    thresholds['fraud_confirmed']['threshold'] = confirmed

    return thresholds

def apply_safety_bounds(thresholds):
    """Enforce min/max bounds."""
    bounds = {
        'suspicious': (0.10, 0.40),
        'fraud_likely': (0.30, 0.70),
        'fraud_confirmed': (0.60, 0.95)
    }

    for level, (min_val, max_val) in bounds.items():
        t = thresholds[level]['threshold']
        thresholds[level]['threshold'] = max(min_val, min(max_val, t))

    return thresholds
```

---

## 3. Implementation

### 3.1 Schema Extensions

```sql
-- Store threshold tuning recommendations
CREATE TABLE threshold_recommendations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    detector_name TEXT,  -- NULL for classification thresholds
    threshold_type TEXT NOT NULL,  -- 'detector' or 'classification'
    level TEXT,  -- 'suspicious', 'fraud_likely', 'fraud_confirmed' (for classification)
    current_threshold REAL,
    recommended_threshold REAL,
    target_fpr REAL,
    achieved_fpr REAL,
    achieved_tpr REAL,
    sample_size INTEGER,
    tp_count INTEGER,
    fp_count INTEGER,
    confidence TEXT CHECK(confidence IN ('low', 'medium', 'high')),
    reason TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    reviewed_at DATETIME,
    reviewed_by TEXT,
    review_decision TEXT CHECK(review_decision IN
        ('approved', 'rejected', 'needs_more_data', NULL)),
    applied_at DATETIME
);

CREATE INDEX idx_threshold_recs_detector ON threshold_recommendations(detector_name);
CREATE INDEX idx_threshold_recs_pending ON threshold_recommendations(review_decision)
    WHERE review_decision IS NULL;

-- Store threshold history (for rollback)
CREATE TABLE threshold_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    detector_name TEXT,
    threshold_type TEXT NOT NULL,
    level TEXT,
    old_threshold REAL,
    new_threshold REAL,
    changed_by TEXT,  -- 'system' or CEO username
    reason TEXT,
    applied_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    reverted_at DATETIME
);

CREATE INDEX idx_threshold_history_detector ON threshold_history(detector_name);
CREATE INDEX idx_threshold_history_applied ON threshold_history(applied_at DESC);

-- Store per-detector threshold overrides (runtime config)
CREATE TABLE detector_thresholds (
    detector_name TEXT PRIMARY KEY,
    threshold REAL NOT NULL,
    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_by TEXT,
    reason TEXT
);

-- Store classification threshold overrides
CREATE TABLE classification_thresholds (
    level TEXT PRIMARY KEY CHECK(level IN
        ('suspicious', 'fraud_likely', 'fraud_confirmed')),
    threshold REAL NOT NULL,
    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_by TEXT,
    reason TEXT
);

-- Initialize with current defaults
INSERT INTO classification_thresholds (level, threshold, updated_by, reason) VALUES
    ('suspicious', 0.20, 'system', 'Initial Phase 2D defaults'),
    ('fraud_likely', 0.50, 'system', 'Initial Phase 2D defaults'),
    ('fraud_confirmed', 0.80, 'system', 'Initial Phase 2D defaults');
```

### 3.2 Core Functions

**File:** `~/.claude/emergent-learning/query/threshold_tuner.py`

```python
#!/usr/bin/env python3
"""
Adaptive Threshold Tuning for Fraud Detection
Phase 2D Enhancement - Agent 2

Analyzes TP/FP data to recommend optimal thresholds.
NEVER auto-applies - generates recommendations for CEO review.
"""

import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass

DB_PATH = Path.home() / ".claude" / "emergent-learning" / "memory" / "index.db"

@dataclass
class ThresholdRecommendation:
    """Recommendation for threshold adjustment."""
    detector_name: Optional[str]
    threshold_type: str  # 'detector' or 'classification'
    level: Optional[str]  # For classification: 'suspicious', 'fraud_likely', 'fraud_confirmed'
    current_threshold: float
    recommended_threshold: float
    target_fpr: float
    achieved_fpr: float
    achieved_tpr: float
    sample_size: int
    tp_count: int
    fp_count: int
    confidence: str
    reason: str

class ThresholdTuner:
    """Adaptive threshold tuning system."""

    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    # =========================================================================
    # DETECTOR-LEVEL THRESHOLD TUNING
    # =========================================================================

    def calculate_optimal_threshold(
        self,
        detector_name: str,
        target_fpr: float = 0.05,
        min_samples: int = 30
    ) -> Dict[str, Any]:
        """
        Calculate optimal threshold for a detector using frequentist approach.

        See algorithm in section 2.2 of design doc.
        """
        conn = self._get_connection()
        try:
            # Get reviewed signal data
            cursor = conn.execute("""
                SELECT asig.score, fr.review_outcome
                FROM anomaly_signals asig
                JOIN fraud_reports fr ON asig.fraud_report_id = fr.id
                WHERE fr.review_outcome IN ('true_positive', 'false_positive')
                  AND asig.detector_name = ?
                ORDER BY asig.score ASC
            """, (detector_name,))

            signals = cursor.fetchall()

            if len(signals) < min_samples:
                return {
                    'detector_name': detector_name,
                    'error': 'insufficient_data',
                    'sample_size': len(signals),
                    'min_required': min_samples,
                    'reason': f'Need {min_samples - len(signals)} more reviewed samples'
                }

            # Extract data
            scores = [s['score'] for s in signals]
            outcomes = [1 if s['review_outcome'] == 'true_positive' else 0
                        for s in signals]

            total_positives = sum(outcomes)
            total_negatives = len(outcomes) - total_positives

            # Try all unique scores as thresholds
            candidate_thresholds = sorted(set(scores))

            best_threshold = None
            best_tpr = 0
            best_fpr = 1.0

            for threshold in candidate_thresholds:
                tp = sum(1 for score, outcome in zip(scores, outcomes)
                         if score >= threshold and outcome == 1)
                fp = sum(1 for score, outcome in zip(scores, outcomes)
                         if score >= threshold and outcome == 0)
                tn = total_negatives - fp
                fn = total_positives - tp

                fpr = fp / (fp + tn) if (fp + tn) > 0 else 0
                tpr = tp / (tp + fn) if (tp + fn) > 0 else 0

                if fpr <= target_fpr and tpr > best_tpr:
                    best_threshold = threshold
                    best_tpr = tpr
                    best_fpr = fpr

            # Fallback: most conservative threshold
            if best_threshold is None:
                for threshold in reversed(candidate_thresholds):
                    tp = sum(1 for score, outcome in zip(scores, outcomes)
                             if score >= threshold and outcome == 1)
                    fp = sum(1 for score, outcome in zip(scores, outcomes)
                             if score >= threshold and outcome == 0)
                    tn = total_negatives - fp
                    fpr = fp / (fp + tn) if (fp + tn) > 0 else 0
                    tpr = tp / (tp + fn) if (tp + fn) > 0 else 0

                    if threshold >= 0.10:
                        best_threshold = threshold
                        best_tpr = tpr
                        best_fpr = fpr
                        break

            # Confidence based on sample size
            if len(signals) >= 100:
                confidence = 'high'
            elif len(signals) >= 50:
                confidence = 'medium'
            else:
                confidence = 'low'

            # Get current threshold
            current_threshold = self._get_current_detector_threshold(conn, detector_name)

            return {
                'detector_name': detector_name,
                'current_threshold': current_threshold,
                'recommended_threshold': best_threshold,
                'target_fpr': target_fpr,
                'achieved_fpr': best_fpr,
                'achieved_tpr': best_tpr,
                'sample_size': len(signals),
                'tp_count': total_positives,
                'fp_count': total_negatives,
                'confidence': confidence,
                'reason': f'Achieves {best_fpr:.1%} FPR (target {target_fpr:.1%}) with {best_tpr:.1%} TPR',
                'evaluated_at': datetime.now()
            }
        finally:
            conn.close()

    def _get_current_detector_threshold(self, conn: sqlite3.Connection, detector_name: str) -> float:
        """Get current threshold for detector from config or defaults."""
        # Check overrides table
        cursor = conn.execute("""
            SELECT threshold FROM detector_thresholds
            WHERE detector_name = ?
        """, (detector_name,))
        row = cursor.fetchone()

        if row:
            return row['threshold']

        # Fallback to hardcoded defaults (from fraud_detector.py FraudConfig)
        defaults = {
            'success_rate_anomaly': 0.5,  # Z-score threshold is 2.5, normalize to 0-1
            'temporal_manipulation': 0.5,
            'unnatural_confidence_growth': 0.5
        }

        return defaults.get(detector_name, 0.5)

    # =========================================================================
    # CLASSIFICATION THRESHOLD TUNING
    # =========================================================================

    def calculate_optimal_classification_thresholds(
        self,
        target_fpr_suspicious: float = 0.10,
        target_fpr_likely: float = 0.05,
        target_fpr_confirmed: float = 0.01,
        min_samples: int = 50
    ) -> Dict[str, Any]:
        """
        Calculate optimal classification thresholds (suspicious/likely/confirmed).

        See algorithm in section 2.4 of design doc.
        """
        conn = self._get_connection()
        try:
            # Get all reviewed reports
            cursor = conn.execute("""
                SELECT fraud_score, review_outcome
                FROM fraud_reports
                WHERE review_outcome IN ('true_positive', 'false_positive')
                ORDER BY fraud_score ASC
            """)

            reports = cursor.fetchall()

            if len(reports) < min_samples:
                return {
                    'error': 'insufficient_data',
                    'sample_size': len(reports),
                    'min_required': min_samples
                }

            scores = [r['fraud_score'] for r in reports]
            outcomes = [1 if r['review_outcome'] == 'true_positive' else 0
                        for r in reports]

            # Calculate thresholds for each level
            results = {}

            for level, target_fpr in [
                ('suspicious', target_fpr_suspicious),
                ('fraud_likely', target_fpr_likely),
                ('fraud_confirmed', target_fpr_confirmed)
            ]:
                threshold_result = self._find_threshold_for_fpr(
                    scores, outcomes, target_fpr
                )
                results[level] = threshold_result

            # Enforce ordering
            results = self._enforce_threshold_ordering(results)

            # Apply safety bounds
            results = self._apply_safety_bounds(results)

            # Get current thresholds
            current = self._get_current_classification_thresholds(conn)

            return {
                'suspicious': {
                    'current': current['suspicious'],
                    **results['suspicious']
                },
                'fraud_likely': {
                    'current': current['fraud_likely'],
                    **results['fraud_likely']
                },
                'fraud_confirmed': {
                    'current': current['fraud_confirmed'],
                    **results['fraud_confirmed']
                },
                'sample_size': len(reports),
                'evaluated_at': datetime.now()
            }
        finally:
            conn.close()

    def _find_threshold_for_fpr(
        self,
        scores: List[float],
        outcomes: List[int],
        target_fpr: float
    ) -> Dict[str, Any]:
        """Find threshold that achieves target FPR."""
        total_negatives = sum(1 for o in outcomes if o == 0)
        total_positives = sum(1 for o in outcomes if o == 1)

        if total_negatives == 0 or total_positives == 0:
            return {
                'threshold': 0.5,
                'fpr': 0,
                'tpr': 0,
                'warning': 'Insufficient positive or negative samples'
            }

        candidate_thresholds = sorted(set(scores))

        for threshold in candidate_thresholds:
            fp = sum(1 for s, o in zip(scores, outcomes)
                     if s >= threshold and o == 0)
            tp = sum(1 for s, o in zip(scores, outcomes)
                     if s >= threshold and o == 1)

            fpr = fp / total_negatives
            tpr = tp / total_positives

            if fpr <= target_fpr:
                return {
                    'threshold': threshold,
                    'fpr': fpr,
                    'tpr': tpr
                }

        # No threshold meets target, use most conservative
        return {
            'threshold': max(candidate_thresholds) if candidate_thresholds else 0.95,
            'fpr': 0,
            'tpr': 0,
            'warning': 'Could not meet target FPR, using maximum threshold'
        }

    def _enforce_threshold_ordering(self, results: Dict) -> Dict:
        """Ensure suspicious < likely < confirmed."""
        sus = results['suspicious']['threshold']
        likely = results['fraud_likely']['threshold']
        confirmed = results['fraud_confirmed']['threshold']

        # Minimum separation: 0.10
        if likely <= sus:
            likely = sus + 0.10
        if confirmed <= likely:
            confirmed = likely + 0.15

        results['fraud_likely']['threshold'] = likely
        results['fraud_confirmed']['threshold'] = confirmed

        return results

    def _apply_safety_bounds(self, results: Dict) -> Dict:
        """Enforce absolute min/max bounds."""
        bounds = {
            'suspicious': (0.10, 0.40),
            'fraud_likely': (0.30, 0.70),
            'fraud_confirmed': (0.60, 0.95)
        }

        for level, (min_val, max_val) in bounds.items():
            t = results[level]['threshold']
            results[level]['threshold'] = max(min_val, min(max_val, t))

        return results

    def _get_current_classification_thresholds(self, conn: sqlite3.Connection) -> Dict[str, float]:
        """Get current classification thresholds."""
        cursor = conn.execute("SELECT level, threshold FROM classification_thresholds")
        return {row['level']: row['threshold'] for row in cursor.fetchall()}

    # =========================================================================
    # RECOMMENDATION MANAGEMENT
    # =========================================================================

    def create_recommendation(
        self,
        recommendation: Dict[str, Any],
        threshold_type: str
    ) -> int:
        """
        Store threshold recommendation for CEO review.

        Args:
            recommendation: Output from calculate_optimal_*()
            threshold_type: 'detector' or 'classification'

        Returns:
            recommendation_id
        """
        conn = self._get_connection()
        try:
            if threshold_type == 'detector':
                cursor = conn.execute("""
                    INSERT INTO threshold_recommendations
                    (detector_name, threshold_type, current_threshold,
                     recommended_threshold, target_fpr, achieved_fpr, achieved_tpr,
                     sample_size, tp_count, fp_count, confidence, reason)
                    VALUES (?, 'detector', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    recommendation['detector_name'],
                    recommendation['current_threshold'],
                    recommendation['recommended_threshold'],
                    recommendation['target_fpr'],
                    recommendation['achieved_fpr'],
                    recommendation['achieved_tpr'],
                    recommendation['sample_size'],
                    recommendation['tp_count'],
                    recommendation['fp_count'],
                    recommendation['confidence'],
                    recommendation['reason']
                ))
            else:  # classification
                # Store one recommendation per level
                rec_ids = []
                for level in ['suspicious', 'fraud_likely', 'fraud_confirmed']:
                    level_data = recommendation[level]
                    cursor = conn.execute("""
                        INSERT INTO threshold_recommendations
                        (threshold_type, level, current_threshold,
                         recommended_threshold, target_fpr, achieved_fpr, achieved_tpr,
                         sample_size, confidence, reason)
                        VALUES ('classification', ?, ?, ?, ?, ?, ?, ?, 'medium', ?)
                    """, (
                        level,
                        level_data['current'],
                        level_data['threshold'],
                        level_data.get('target_fpr', 0.05),
                        level_data.get('fpr', 0),
                        level_data.get('tpr', 0),
                        recommendation['sample_size'],
                        level_data.get('warning', 'Recommended based on TP/FP analysis')
                    ))
                    rec_ids.append(cursor.lastrowid)
                conn.commit()
                return rec_ids[0]  # Return first ID

            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()

    def get_pending_recommendations(self) -> List[Dict]:
        """Get all recommendations pending CEO review."""
        conn = self._get_connection()
        try:
            cursor = conn.execute("""
                SELECT * FROM threshold_recommendations
                WHERE review_decision IS NULL
                ORDER BY created_at DESC
            """)
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def apply_threshold_update(
        self,
        recommendation_id: int,
        approved_by: str = 'ceo',
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Apply a threshold recommendation.

        IMPORTANT: Only call after CEO approval.
        Records change in threshold_history for rollback.

        Args:
            recommendation_id: ID of approved recommendation
            approved_by: Who approved (default 'ceo')
            reason: Optional reason for applying

        Returns:
            {'success': bool, 'applied': [...]}
        """
        conn = self._get_connection()
        try:
            # Get recommendation
            cursor = conn.execute("""
                SELECT * FROM threshold_recommendations WHERE id = ?
            """, (recommendation_id,))
            rec = cursor.fetchone()

            if not rec:
                return {'success': False, 'error': 'Recommendation not found'}

            if rec['review_decision'] == 'rejected':
                return {'success': False, 'error': 'Recommendation was rejected'}

            # Apply based on type
            if rec['threshold_type'] == 'detector':
                # Update detector threshold
                conn.execute("""
                    INSERT OR REPLACE INTO detector_thresholds
                    (detector_name, threshold, updated_by, reason)
                    VALUES (?, ?, ?, ?)
                """, (
                    rec['detector_name'],
                    rec['recommended_threshold'],
                    approved_by,
                    reason or rec['reason']
                ))

                # Record in history
                conn.execute("""
                    INSERT INTO threshold_history
                    (detector_name, threshold_type, old_threshold, new_threshold,
                     changed_by, reason)
                    VALUES (?, 'detector', ?, ?, ?, ?)
                """, (
                    rec['detector_name'],
                    rec['current_threshold'],
                    rec['recommended_threshold'],
                    approved_by,
                    reason or rec['reason']
                ))

            else:  # classification
                # Update classification threshold
                conn.execute("""
                    UPDATE classification_thresholds
                    SET threshold = ?, updated_by = ?, reason = ?, last_updated = CURRENT_TIMESTAMP
                    WHERE level = ?
                """, (
                    rec['recommended_threshold'],
                    approved_by,
                    reason or rec['reason'],
                    rec['level']
                ))

                # Record in history
                conn.execute("""
                    INSERT INTO threshold_history
                    (threshold_type, level, old_threshold, new_threshold,
                     changed_by, reason)
                    VALUES ('classification', ?, ?, ?, ?, ?)
                """, (
                    rec['level'],
                    rec['current_threshold'],
                    rec['recommended_threshold'],
                    approved_by,
                    reason or rec['reason']
                ))

            # Mark recommendation as approved and applied
            conn.execute("""
                UPDATE threshold_recommendations
                SET review_decision = 'approved',
                    reviewed_at = CURRENT_TIMESTAMP,
                    reviewed_by = ?,
                    applied_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (approved_by, recommendation_id))

            conn.commit()

            return {
                'success': True,
                'applied': {
                    'detector_name': rec['detector_name'],
                    'level': rec['level'],
                    'old_threshold': rec['current_threshold'],
                    'new_threshold': rec['recommended_threshold']
                }
            }
        finally:
            conn.close()

    def rollback_threshold(
        self,
        history_id: int,
        reverted_by: str = 'ceo'
    ) -> Dict[str, Any]:
        """
        Rollback a threshold change.

        Reverts to old_threshold from history record.
        """
        conn = self._get_connection()
        try:
            # Get history record
            cursor = conn.execute("""
                SELECT * FROM threshold_history WHERE id = ?
            """, (history_id,))
            hist = cursor.fetchone()

            if not hist:
                return {'success': False, 'error': 'History record not found'}

            if hist['reverted_at']:
                return {'success': False, 'error': 'Already reverted'}

            # Revert based on type
            if hist['threshold_type'] == 'detector':
                conn.execute("""
                    INSERT OR REPLACE INTO detector_thresholds
                    (detector_name, threshold, updated_by, reason)
                    VALUES (?, ?, ?, ?)
                """, (
                    hist['detector_name'],
                    hist['old_threshold'],
                    reverted_by,
                    f'Rollback of change on {hist["applied_at"]}'
                ))
            else:  # classification
                conn.execute("""
                    UPDATE classification_thresholds
                    SET threshold = ?, updated_by = ?, reason = ?, last_updated = CURRENT_TIMESTAMP
                    WHERE level = ?
                """, (
                    hist['old_threshold'],
                    reverted_by,
                    f'Rollback of change on {hist["applied_at"]}',
                    hist['level']
                ))

            # Mark as reverted
            conn.execute("""
                UPDATE threshold_history
                SET reverted_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (history_id,))

            conn.commit()

            return {
                'success': True,
                'reverted': {
                    'detector_name': hist['detector_name'],
                    'level': hist['level'],
                    'from': hist['new_threshold'],
                    'to': hist['old_threshold']
                }
            }
        finally:
            conn.close()

    # =========================================================================
    # BATCH OPERATIONS
    # =========================================================================

    def run_full_tuning_analysis(
        self,
        target_fpr: float = 0.05,
        min_samples_detector: int = 30,
        min_samples_classification: int = 50
    ) -> Dict[str, Any]:
        """
        Run complete tuning analysis for all detectors and classification.

        Generates recommendations, does NOT apply them.

        Returns:
            {
                'detectors': [...],
                'classification': {...},
                'recommendations_created': [...]
            }
        """
        results = {
            'detectors': [],
            'classification': None,
            'recommendations_created': []
        }

        # Tune each detector
        detector_names = [
            'success_rate_anomaly',
            'temporal_manipulation',
            'unnatural_confidence_growth'
        ]

        for detector in detector_names:
            result = self.calculate_optimal_threshold(
                detector, target_fpr, min_samples_detector
            )
            results['detectors'].append(result)

            # Create recommendation if sufficient data
            if 'error' not in result:
                rec_id = self.create_recommendation(result, 'detector')
                results['recommendations_created'].append(rec_id)

        # Tune classification thresholds
        class_result = self.calculate_optimal_classification_thresholds(
            target_fpr_suspicious=0.10,
            target_fpr_likely=0.05,
            target_fpr_confirmed=0.01,
            min_samples=min_samples_classification
        )

        results['classification'] = class_result

        if 'error' not in class_result:
            rec_id = self.create_recommendation(class_result, 'classification')
            results['recommendations_created'].append(rec_id)

        return results


# CLI interface
if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser(description="Adaptive Threshold Tuning")
    parser.add_argument("command", choices=[
        "analyze-detector",
        "analyze-classification",
        "full-analysis",
        "pending",
        "apply",
        "rollback"
    ])
    parser.add_argument("--detector", help="Detector name")
    parser.add_argument("--target-fpr", type=float, default=0.05)
    parser.add_argument("--rec-id", type=int, help="Recommendation ID")
    parser.add_argument("--history-id", type=int, help="History ID for rollback")

    args = parser.parse_args()

    tuner = ThresholdTuner()

    if args.command == "analyze-detector":
        if not args.detector:
            print("Error: --detector required")
            exit(1)
        result = tuner.calculate_optimal_threshold(args.detector, args.target_fpr)
        print(json.dumps(result, indent=2, default=str))

    elif args.command == "analyze-classification":
        result = tuner.calculate_optimal_classification_thresholds()
        print(json.dumps(result, indent=2, default=str))

    elif args.command == "full-analysis":
        result = tuner.run_full_tuning_analysis(args.target_fpr)
        print(json.dumps(result, indent=2, default=str))

    elif args.command == "pending":
        result = tuner.get_pending_recommendations()
        print(json.dumps(result, indent=2, default=str))

    elif args.command == "apply":
        if not args.rec_id:
            print("Error: --rec-id required")
            exit(1)
        result = tuner.apply_threshold_update(args.rec_id)
        print(json.dumps(result, indent=2, default=str))

    elif args.command == "rollback":
        if not args.history_id:
            print("Error: --history-id required")
            exit(1)
        result = tuner.rollback_threshold(args.history_id)
        print(json.dumps(result, indent=2, default=str))
```

---

## 4. Integration with Fraud Detector

The fraud detector needs to read thresholds from the database instead of hardcoded config.

**Changes to `fraud_detector.py`:**

```python
class FraudDetector:
    def __init__(self, db_path: Path = DB_PATH, config: Optional[FraudConfig] = None):
        self.db_path = db_path
        self.config = config or self._load_config_from_db()

    def _load_config_from_db(self) -> FraudConfig:
        """Load configuration from database (or defaults)."""
        conn = self._get_connection()
        try:
            config = FraudConfig()

            # Load classification thresholds
            cursor = conn.execute("SELECT level, threshold FROM classification_thresholds")
            for row in cursor.fetchall():
                if row['level'] == 'suspicious':
                    config.threshold_suspicious = row['threshold']
                elif row['level'] == 'fraud_likely':
                    config.threshold_fraud_likely = row['threshold']
                elif row['level'] == 'fraud_confirmed':
                    config.threshold_fraud_confirmed = row['threshold']

            # Load detector thresholds
            cursor = conn.execute("SELECT detector_name, threshold FROM detector_thresholds")
            detector_overrides = {row['detector_name']: row['threshold']
                                 for row in cursor.fetchall()}

            # Apply overrides (extend FraudConfig to store these)
            config.detector_thresholds = detector_overrides

            return config
        finally:
            conn.close()
```

---

## 5. CEO Workflow

### 5.1 Generating Recommendations

**Monthly tuning analysis (cron job or manual):**

```bash
# Run full analysis
python ~/.claude/emergent-learning/query/threshold_tuner.py full-analysis --target-fpr 0.05

# Output:
# {
#   "detectors": [
#     {
#       "detector_name": "success_rate_anomaly",
#       "current_threshold": 0.50,
#       "recommended_threshold": 0.42,
#       "achieved_fpr": 0.04,
#       "achieved_tpr": 0.87,
#       "confidence": "high"
#     },
#     ...
#   ],
#   "recommendations_created": [123, 124, 125]
# }
```

### 5.2 Reviewing Recommendations

```bash
# Check pending recommendations
python ~/.claude/emergent-learning/query/threshold_tuner.py pending

# Output shows all pending recommendations with current vs recommended
```

**CEO reviews each recommendation:**
- Check sample size (is it sufficient?)
- Check confidence level (high/medium/low)
- Check achieved FPR/TPR (are they acceptable?)
- Check change magnitude (is it reasonable? Max ±0.10)

### 5.3 Approving Changes

```bash
# Apply recommendation
python ~/.claude/emergent-learning/query/threshold_tuner.py apply --rec-id 123

# Output:
# {
#   "success": true,
#   "applied": {
#     "detector_name": "success_rate_anomaly",
#     "old_threshold": 0.50,
#     "new_threshold": 0.42
#   }
# }
```

### 5.4 Rolling Back

```bash
# If threshold change causes problems, rollback
python ~/.claude/emergent-learning/query/threshold_tuner.py rollback --history-id 45

# Reverts to old threshold
```

---

## 6. Safety Mechanisms

### 6.1 Sample Size Requirements

- **Detector tuning:** Minimum 30 reviewed signals
- **Classification tuning:** Minimum 50 reviewed reports
- **Rationale:** Small samples lead to unstable estimates

### 6.2 Safety Bounds

**Absolute bounds (never exceed):**
- `suspicious`: [0.10, 0.40]
- `fraud_likely`: [0.30, 0.70]
- `fraud_confirmed`: [0.60, 0.95]

**Rationale:**
- Lower bounds prevent over-sensitivity (false positive flood)
- Upper bounds prevent under-sensitivity (miss real fraud)

### 6.3 Gradual Adjustment

**Maximum change per update:** ±0.10

If algorithm suggests moving from 0.50 → 0.25, recommend 0.40 instead.
Next tuning cycle can adjust further if data supports.

**Rationale:** Large sudden changes are risky, gradual is safer.

### 6.4 Threshold Ordering

Must maintain: `suspicious < fraud_likely < fraud_confirmed`

Minimum separation: 0.10 between levels

**Rationale:** Classifications must be distinguishable.

### 6.5 Rollback Capability

All changes recorded in `threshold_history`.
Any change can be reverted with single command.

**Rationale:** If tuning causes unexpected issues, quick recovery.

---

## 7. Performance Considerations

**Tuning is NOT real-time:**
- Run monthly (or on-demand)
- Batch operation, takes ~1-5 seconds
- No impact on live fraud detection

**Database queries are lightweight:**
- Indexed on review_outcome, detector_name
- Typical dataset: <1000 reviewed reports
- Query time: <100ms

---

## 8. Future Enhancements

### 8.1 Per-Domain Thresholds

Current design uses global thresholds.
Could extend to domain-specific:

```sql
CREATE TABLE domain_threshold_overrides (
    domain TEXT,
    level TEXT,
    threshold REAL,
    PRIMARY KEY (domain, level)
);
```

### 8.2 ROC Curve Analysis

Instead of single target FPR, show full ROC curve.
CEO picks point on curve (TPR/FPR tradeoff).

### 8.3 Cost-Sensitive Learning

Assign costs: FP = $10, FN = $100
Optimize thresholds to minimize expected cost.

### 8.4 Temporal Adjustment

Detect seasonal patterns, adjust thresholds quarterly.
Example: Tax season may need different thresholds.

---

## 9. Testing Strategy

### 9.1 Unit Tests

Test each function with synthetic data:
- `calculate_optimal_threshold()` with known TP/FP distribution
- `enforce_threshold_ordering()` with edge cases
- `apply_safety_bounds()` with out-of-bounds inputs

### 9.2 Integration Tests

- Create 100 fake fraud_reports with review_outcome
- Run full analysis
- Verify recommendations are generated
- Apply and verify thresholds updated
- Rollback and verify reverted

### 9.3 Validation Tests

Use actual production data:
- Compare recommended vs current thresholds
- Simulate: if we had used recommended, what would FPR/TPR be?
- Validate against holdout set (last 30 days not used in tuning)

---

## 10. FINDINGS

### [fact] Current System Uses Fixed Thresholds
- `FraudConfig` in `fraud_detector.py` hardcodes all thresholds
- No mechanism to adjust based on observed performance
- Classification thresholds: 0.20, 0.50, 0.80 (arbitrary choices)
- Detector thresholds: 0.5 for temporal/trajectory, 2.5 Z-score for success_rate

### [fact] Database Already Tracks TP/FP
- `fraud_reports.review_outcome` column exists
- Values: 'true_positive', 'false_positive', 'pending', NULL
- `anomaly_signals` table links detectors to reports
- Schema is ready for TP/FP analysis

### [hypothesis] Frequentist Approach Is Sufficient
- Bayesian approach adds complexity without major benefit
- Requires choosing prior (subjective)
- For sample sizes >30, frequentist converges to Bayesian
- **Recommendation:** Implement frequentist, document Bayesian as alternative

### [hypothesis] Target FPR 5% Is Reasonable
- Design doc suggests 5% FPR for fraud_likely
- Industry standard for anomaly detection: 1-10% FPR
- Conservative for high-impact actions (quarantine)
- Less conservative for low-impact (warnings)
- **Recommendation:** 10% for suspicious, 5% for likely, 1% for confirmed

### [blocker] No CEO Review Collected Yet
- System is Phase 2D (just implemented)
- Likely zero or very few reviewed reports
- Cannot tune until N reviews collected
- **Mitigation:** Document required sample sizes, implement but don't expect immediate use

### [question] How Often to Re-Tune?
- Monthly: Adapts quickly, but unstable if little new data
- Quarterly: More stable, but slower adaptation
- On-demand: CEO triggers when FP rate seems high
- **Recommendation:** Start with quarterly, allow on-demand

### [question] Should Detectors Have Independent Thresholds?
- Currently: All detectors use same score threshold (0.5)
- Alternative: Each detector has tuned threshold
- More complex but more accurate
- **Recommendation:** Yes, implement per-detector tuning

### [fact] Safety Bounds Prevent Catastrophic Tuning
- Bounds [0.10, 0.40] for suspicious prevent going to 0.01 (flag everything)
- Bounds [0.60, 0.95] for confirmed prevent going to 1.0 (flag nothing)
- Gradual adjustment (max ±0.10) prevents shock
- **Validation:** Critical safety mechanism, do NOT remove

### [hypothesis] Rollback Will Rarely Be Needed
- If tuning is conservative (gradual, bounded), changes will be small
- Small changes are unlikely to cause major issues
- But rollback is cheap insurance
- **Keep rollback mechanism** even if rarely used

### [fact] Integration Requires FraudConfig Changes
- `FraudConfig` dataclass needs dynamic loading
- Currently initialized once at startup
- Need `_load_config_from_db()` method
- Minimal code change (< 50 lines)

### [question] What If TP/FP Distribution Is Skewed?
- Example: 95% of reviewed reports are true_positive
- Very few false_positives to calibrate on
- Frequentist approach may suggest threshold = 0.0 (flag nothing)
- **Mitigation:** Require minimum counts (10 TP AND 10 FP)

### [hypothesis] Confidence Levels Are Useful Signal
- low: 30-49 samples (use with caution)
- medium: 50-99 samples (reasonable)
- high: 100+ samples (trustworthy)
- CEO can weight confidence in decision
- **Include in recommendation output**

### [fact] No External Dependencies Needed
- Python stdlib only (sqlite3, statistics, dataclasses)
- No scipy, scikit-learn, pandas required
- Simple frequentist approach is implementable in pure Python
- **Advantage:** No dependency bloat

### [blocker] Need to Extend Database Schema
- Tables: threshold_recommendations, threshold_history, detector_thresholds, classification_thresholds
- ~150 lines of SQL
- Migration needed before implementation
- **Action:** Create migration script

### [question] Should Recommendations Expire?
- If recommendation created but not reviewed for 90 days, still valid?
- Data distribution may have changed
- **Recommendation:** Mark as 'stale' after 60 days, require re-analysis
