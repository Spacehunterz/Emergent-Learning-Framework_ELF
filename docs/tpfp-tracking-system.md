# TP/FP Tracking System

**Phase:** 3 - Swarm Agent 1 Deliverable
**Date:** 2025-12-13
**Status:** Implemented and Tested

---

## Overview

The TP/FP (True Positive / False Positive) tracking system enables human reviewers to make decisions on fraud detection alerts and calculates detector accuracy metrics based on those decisions. This creates a continuous improvement loop where detectors can be tuned based on real-world outcomes.

## Architecture

### Database Schema

**Migration:** `memory/migrations/007_tpfp_tracking.sql`

#### New Tables

1. **`fraud_outcome_history`**
   - Audit trail for all outcome changes
   - Tracks who changed what and when
   - Enables rollback and analysis of decision patterns

2. **`detector_performance`** (materialized metrics)
   - Pre-computed accuracy metrics per detector
   - Time-windowed (all_time, last_30d, last_7d, last_24h)
   - Fast dashboard queries

3. **`domain_fraud_performance`** (materialized metrics)
   - Fraud detection accuracy by domain
   - Helps identify domains with high FP rates

#### Enhanced Tables

**`fraud_reports`** (existing, from migration 006):
- Already has `review_outcome` column ('true_positive', 'false_positive', 'dismissed', 'pending')
- Already has `reviewed_at` and `reviewed_by` columns
- No schema changes needed - fully compatible

#### Analytical Views

1. **`detector_accuracy_realtime`**
   - Real-time accuracy metrics per detector
   - Shows precision (TP / (TP + FP))
   - Tracks total reports, TP, FP, pending

2. **`detector_accuracy_30d`**
   - Same as realtime but filtered to last 30 days
   - Useful for tracking recent performance

3. **`domain_fraud_accuracy`**
   - Accuracy metrics grouped by domain
   - Identifies domains with systematic FP issues

4. **`classification_accuracy`**
   - Checks if fraud_score thresholds align with human decisions
   - Shows accuracy per classification level (clean, suspicious, fraud_likely, etc.)

5. **`pending_review_queue`**
   - Prioritized list of reports awaiting review
   - Priority = (fraud_score * 0.7) + (signal_count * 0.03)
   - Shows detectors and severities

6. **`detector_confusion_matrix`**
   - TP/FP distribution per detector and severity level
   - Helps understand which detectors are most reliable

#### Triggers

**`trg_fraud_outcome_change`**
- Fires on UPDATE of `fraud_reports.review_outcome`
- Automatically records changes to `fraud_outcome_history`
- Captures who made the change and when

---

## Python API

**Module:** `query/fraud_outcomes.py`

### Core Classes

#### `FraudOutcomeTracker`

Main class for recording outcomes and calculating accuracy.

**Example Usage:**

```python
from fraud_outcomes import FraudOutcomeTracker

tracker = FraudOutcomeTracker()

# Record a decision
tracker.record_outcome(
    report_id=123,
    outcome='true_positive',  # or 'false_positive', 'dismissed', 'pending'
    decided_by='ceo@example.com',
    notes='Confirmed after investigation'
)

# Get detector accuracy
accuracies = tracker.get_detector_accuracy(days=30)
for acc in accuracies:
    print(f"{acc.detector_name}: {acc.precision:.1%} precision")

# Get pending reports for review
pending = tracker.get_pending_reports(limit=10)
for report in pending:
    print(f"Report {report['report_id']}: {report['classification']}")
    print(f"  Score: {report['fraud_score']:.2f}")
    print(f"  Detectors: {report['detectors']}")

# Generate performance report
report = tracker.generate_performance_report(days=30)
print(f"Overall precision: {report['summary']['overall_precision']:.1%}")
```

### Key Methods

#### Recording Outcomes

**`record_outcome(report_id, outcome, decided_by, notes=None, confidence=None)`**

Records a human decision on a fraud report.

- **Args:**
  - `report_id` (int): ID of the fraud_reports record
  - `outcome` (OutcomeType): 'true_positive', 'false_positive', 'dismissed', 'pending'
  - `decided_by` (str): Who made the decision (email, agent ID, or 'user')
  - `notes` (str, optional): Explanation for the decision
  - `confidence` (float, optional): Reviewer confidence (0.0-1.0)

- **Returns:** `bool` - True if recorded successfully

**`batch_record_outcomes(outcomes)`**

Records multiple outcomes at once.

- **Args:** List of `(report_id, outcome, decided_by, notes)` tuples
- **Returns:** `{'success': int, 'failed': int}`

#### Accuracy Queries

**`get_detector_accuracy(detector_name=None, days=None)`**

Get accuracy metrics for one or all detectors.

- **Args:**
  - `detector_name` (str, optional): Specific detector (None = all)
  - `days` (int, optional): Time window (None = all time)

- **Returns:** `List[DetectorAccuracy]`

**`get_domain_accuracy(domain=None, days=None)`**

Get fraud detection accuracy by domain.

- **Args:**
  - `domain` (str, optional): Specific domain (None = all)
  - `days` (int, optional): Time window

- **Returns:** `List[DomainAccuracy]`

#### Analysis & Reporting

**`get_pending_reports(limit=50)`**

Get fraud reports awaiting review, prioritized by severity.

- **Returns:** List of pending reports with metadata

**`get_classification_accuracy()`**

Check if fraud_score thresholds align with human decisions.

- **Returns:** Classification accuracy view

**`get_detector_confusion_matrix()`**

Get confusion matrix showing TP/FP distribution per detector.

- **Returns:** List of confusion matrix entries

**`identify_underperforming_detectors(min_reports=10, max_precision=0.5)`**

Find detectors with low precision (high FP rate).

- **Args:**
  - `min_reports` (int): Minimum reports to evaluate
  - `max_precision` (float): Precision threshold

- **Returns:** List of underperforming detectors

**`generate_performance_report(days=30)`**

Generate comprehensive performance report.

- **Returns:** Dictionary with overall metrics, detector stats, domain stats

---

## Integration with FraudDetector

The existing `FraudDetector` class now includes convenience methods:

```python
from fraud_detector import FraudDetector

detector = FraudDetector()

# Record outcome
detector.record_outcome(123, 'false_positive', 'ceo', 'Normal behavior')

# Get accuracy
accuracies = detector.get_detector_accuracy(days=30)
```

---

## CLI Usage

### fraud_outcomes.py CLI

```bash
# Record an outcome
python fraud_outcomes.py record \
    --report-id 123 \
    --outcome true_positive \
    --decided-by ceo \
    --notes "Confirmed fraud"

# Get pending reports
python fraud_outcomes.py pending --json

# Get detector accuracy
python fraud_outcomes.py accuracy --days 30 --json

# Get domain accuracy
python fraud_outcomes.py domains --domain git-workflow --json

# Generate performance report
python fraud_outcomes.py report --days 30 --json

# Identify underperforming detectors
python fraud_outcomes.py underperforming --json
```

---

## Testing

**Test Suite:** `tests/test_fraud_outcomes.py`

Comprehensive tests covering:
- Recording outcomes (single and batch)
- Detector accuracy calculations
- Domain accuracy calculations
- Pending reports queue
- Classification accuracy
- Confusion matrix
- Underperforming detector identification
- Performance report generation

**Run tests:**

```bash
python tests/test_fraud_outcomes.py
```

**Test Results (2025-12-13):**

```
✓ All tests passed!
✓ Test: Record Outcome (3/3 assertions)
✓ Test: Detector Accuracy (3 detectors analyzed)
✓ Test: Domain Accuracy (3 domains analyzed)
✓ Test: Pending Reports (0 pending - all reviewed)
✓ Test: Classification Accuracy (4 classification levels)
✓ Test: Confusion Matrix (5 detector/severity combinations)
✓ Test: Underperforming Detectors (2 identified)
✓ Test: Performance Report (generated successfully)
```

---

## Usage Workflow

### 1. Fraud Detection Creates Reports

```python
from fraud_detector import FraudDetector

detector = FraudDetector()
report = detector.create_fraud_report(heuristic_id=42)

print(f"Fraud score: {report.fraud_score:.2f}")
print(f"Classification: {report.classification}")
```

### 2. CEO Reviews Pending Reports

```python
from fraud_outcomes import FraudOutcomeTracker

tracker = FraudOutcomeTracker()

# Get prioritized queue
pending = tracker.get_pending_reports(limit=10)

for report in pending:
    print(f"\nReport #{report['report_id']}")
    print(f"  Domain: {report['domain']}")
    print(f"  Heuristic: {report['rule']}")
    print(f"  Fraud Score: {report['fraud_score']:.2f}")
    print(f"  Detectors: {report['detectors']}")
    print(f"  Priority: {report['priority_score']:.2f}")
```

### 3. Record Decisions

```python
# Confirm fraud
tracker.record_outcome(
    report_id=42,
    outcome='true_positive',
    decided_by='ceo@example.com',
    notes='Confirmed pump-and-dump pattern'
)

# False alarm
tracker.record_outcome(
    report_id=43,
    outcome='false_positive',
    decided_by='ceo@example.com',
    notes='High success rate is legitimate for this domain'
)

# Unclear
tracker.record_outcome(
    report_id=44,
    outcome='dismissed',
    decided_by='ceo@example.com',
    notes='Need more data to decide'
)
```

### 4. Analyze Detector Performance

```python
# Weekly review
report = tracker.generate_performance_report(days=7)

print(f"Overall Precision: {report['summary']['overall_precision']:.1%}")
print(f"Total Reports: {report['summary']['total_reports']}")
print(f"TP: {report['summary']['total_tp']}, FP: {report['summary']['total_fp']}")

# Check detectors
for detector in report['detectors']:
    print(f"\n{detector['name']}: {detector['precision']:.1%}")
    print(f"  TP: {detector['tp']}, FP: {detector['fp']}")

# Identify problems
if report['underperforming']:
    print("\n⚠️ Underperforming Detectors:")
    for d in report['underperforming']:
        print(f"  - {d['detector_name']}: {d['precision']:.1%} precision")
```

### 5. Tune Detector Thresholds

Based on accuracy metrics, adjust `FraudConfig` in `fraud_detector.py`:

```python
# If success_rate_anomaly has high FP rate, tighten threshold
config = FraudConfig(
    success_rate_z_threshold=3.0,  # Raised from 2.5
    temporal_score_threshold=0.5,
    trajectory_score_threshold=0.5
)

detector = FraudDetector(config=config)
```

---

## Metrics & KPIs

### Precision (Primary Metric)

**Formula:** `TP / (TP + FP)`

- **Target:** ≥ 95% (per CEO decision, 5% FPR tolerance)
- **Warning:** < 90%
- **Critical:** < 80%

### Detection Metrics

- **True Positive Rate:** Confirmed frauds / Total reports
- **False Positive Rate:** False alarms / Total reports
- **Pending Rate:** Unreviewed / Total reports

### Detector-Specific Metrics

- **Precision by Detector:** Which detectors are most accurate?
- **Precision by Severity:** Are 'high' severity signals more reliable?
- **Precision by Domain:** Which domains have higher FP rates?

### Threshold Alignment

- **Classification Accuracy:** Do our fraud_score thresholds match human decisions?
  - `fraud_confirmed` (>0.80) should be confirmed ~90%+ of the time
  - `suspicious` (>0.20) should be confirmed ~30-50% of the time

---

## FINDINGS

### [fact] Existing schema already supports outcomes
The `fraud_reports` table from migration 006 already has `review_outcome`, `reviewed_at`, and `reviewed_by` columns. No schema changes needed to the core table.

### [fact] Views enable efficient analytics
Creating materialized views like `detector_accuracy_realtime` enables fast dashboard queries without expensive JOINs on every request.

### [fact] Triggers automate audit trail
The `trg_fraud_outcome_change` trigger automatically records all outcome changes to `fraud_outcome_history`, ensuring complete audit trail without requiring manual logging.

### [fact] Priority scoring enables triage
The pending_review_queue view uses a weighted priority score (70% fraud score + 30% signal count) to help reviewers focus on the most important cases first.

### [hypothesis] Detector tuning will reduce FP rate
By tracking which detectors produce false positives, we can adjust thresholds (e.g., raising `success_rate_z_threshold` from 2.5 to 3.0) to improve precision while maintaining detection capability.

### [hypothesis] Domain-specific thresholds may be needed
If certain domains consistently show high FP rates, we may need domain-specific configurations rather than global thresholds.

### [fact] Test suite validates all core functionality
All 8 test scenarios pass successfully, confirming:
- Outcome recording (single and batch)
- Accuracy calculations (detector and domain level)
- Queue prioritization
- Classification alignment
- Confusion matrix generation
- Performance reporting

### [question] How should we handle "dismissed" outcomes?
Currently, "dismissed" outcomes (unclear/need-more-data) are not counted in precision calculations. Should they:
1. Be excluded (current behavior)
2. Count as FP (conservative)
3. Count fractionally (0.5 weight)
4. Trigger re-analysis after X days

### [question] When should we refresh domain baselines?
After recording outcomes, we may need to refresh domain baselines if FP patterns indicate baseline drift. Should this be:
1. Manual (CEO triggered)
2. Automatic after N outcomes per domain
3. Scheduled (weekly refresh)

---

## Next Steps

### Immediate (Phase 3)
1. ✅ Migration 007 schema implemented
2. ✅ Python API implemented
3. ✅ Integration with FraudDetector
4. ✅ Test suite passing
5. **Pending:** Apply migration to production database
6. **Pending:** Dashboard UI for outcome recording

### Future Enhancements
1. **Auto-tuning:** Automatically adjust detector thresholds based on accuracy
2. **Batch review UI:** Review multiple reports at once
3. **Reviewer consensus:** Multi-reviewer voting for unclear cases
4. **Outcome predictions:** ML model to predict likely outcomes based on signal patterns
5. **Detector deprecation:** Automatically disable detectors below precision threshold

---

## Related Files

- **Migration:** `memory/migrations/007_tpfp_tracking.sql`
- **Python API:** `query/fraud_outcomes.py`
- **Fraud Detector:** `query/fraud_detector.py`
- **Test Suite:** `tests/test_fraud_outcomes.py`
- **Previous Migration:** `memory/migrations/006_fraud_detection.sql`

---

## Constraints & Assumptions

### Constraints (from task brief)
✅ Must integrate with existing schema from 006_fraud_detection.sql
✅ Follow existing code patterns in fraud_detector.py
✅ Provide views for TP/FP rates by detector, domain, time period
✅ Implement Python functions for outcome recording and accuracy calculation

### Assumptions
- Human reviewers are available to review reports (CEO or delegated)
- Review decisions are final (no appeals process modeled)
- Precision is the primary metric (not recall, since we don't track missed frauds)
- 30-day window is default for "recent" performance (configurable)

---

**Implementation complete. Ready for Phase 3 integration.**
