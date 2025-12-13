# Adaptive Threshold Tuning - CEO Guide

## Overview

The adaptive threshold tuning system automatically analyzes fraud detection performance and recommends threshold adjustments based on actual true positive (TP) and false positive (FP) data.

**Key principles:**
- NEVER auto-applies changes
- Generates recommendations for your review
- Requires minimum sample size before tuning
- Applies safety bounds to prevent extreme adjustments
- Maintains full history for rollback

---

## Quick Start

### 1. Apply Database Migration

First time only:

```bash
cd ~/.claude/emergent-learning
sqlite3 memory/index.db < scripts/migrate-threshold-tuning.sql
```

This creates the threshold tuning tables.

### 2. Run Full Analysis

```bash
python query/threshold_tuner.py full-analysis
```

This analyzes all detectors and classification thresholds, generates recommendations.

**Output:**
```json
{
  "detectors": [
    {
      "detector_name": "success_rate_anomaly",
      "current_threshold": 0.50,
      "recommended_threshold": 0.42,
      "achieved_fpr": 0.04,
      "achieved_tpr": 0.87,
      "confidence": "high",
      "sample_size": 85
    }
  ],
  "recommendations_created": [123, 124, 125]
}
```

### 3. Review Pending Recommendations

```bash
python query/threshold_tuner.py pending
```

Shows all recommendations awaiting your decision.

### 4. Approve a Recommendation

```bash
python query/threshold_tuner.py apply --rec-id 123
```

Applies the threshold change and records it in history.

### 5. Rollback if Needed

```bash
python query/threshold_tuner.py rollback --history-id 45
```

Reverts a threshold change to its previous value.

---

## When to Run Tuning

**Recommended schedule:** Quarterly (every 3 months)

**Or on-demand when:**
- False positive rate seems high (lots of innocent heuristics flagged)
- False negative rate seems high (known fraud not detected)
- After significant system changes
- After accumulating 50+ new reviewed fraud reports

**DO NOT run if:**
- Fewer than 30 reviewed reports for detectors
- Fewer than 50 reviewed reports for classification
- System reports "insufficient_data" error

---

## Understanding Recommendations

### Confidence Levels

- **high** (100+ samples): Very reliable, safe to apply
- **medium** (50-99 samples): Reasonably reliable, review carefully
- **low** (30-49 samples): Use with caution, may be unstable

### Target FPR (False Positive Rate)

- **suspicious**: 10% FPR (allows more warnings, less invasive)
- **fraud_likely**: 5% FPR (balance between catching fraud and avoiding false alarms)
- **fraud_confirmed**: 1% FPR (very conservative, only flag when highly confident)

### Achieved FPR/TPR

- **achieved_fpr**: Actual false positive rate at recommended threshold
- **achieved_tpr**: Actual true positive rate (recall - what % of fraud is caught)

**Example:**
```
achieved_fpr: 0.04 (4%)
achieved_tpr: 0.87 (87%)
```

Means: 4% of clean heuristics are flagged (acceptable), 87% of fraudulent heuristics are caught (good).

### Change Magnitude

System limits changes to ±0.10 per update (gradual adjustment).

**Example:**
- Current: 0.50
- Algorithm suggests: 0.25
- Recommended: 0.40 (limited to -0.10)

If you apply 0.40 and it works well, next tuning cycle can suggest 0.30, etc.

---

## Decision Framework

### When to APPROVE

✅ Confidence is medium or high
✅ Sample size ≥ 50
✅ Achieved FPR ≤ target FPR
✅ Achieved TPR is acceptable (≥ 70%)
✅ Change magnitude is reasonable (≤ 0.15)

### When to REJECT

❌ Confidence is low AND change is large
❌ Sample size < 50
❌ Achieved FPR > target FPR
❌ Change magnitude seems extreme (> 0.20)
❌ You don't understand the recommendation

### When to REQUEST MORE DATA

⏸️ Sample size is borderline (30-50)
⏸️ Confidence is low but direction seems right
⏸️ Data looks imbalanced (95% TP or 95% FP)

---

## Common Scenarios

### Scenario 1: Too Many False Positives

**Symptom:** Clean heuristics keep getting flagged as suspicious

**Action:**
1. Run full analysis
2. Look for recommendations that INCREASE thresholds
3. Approve if confidence is medium/high
4. Monitor for 30 days
5. Re-tune if needed

### Scenario 2: Missing Known Fraud

**Symptom:** You manually reviewed a heuristic and it's clearly fraud, but system didn't flag it

**Action:**
1. Check the fraud_score for that heuristic
2. Run full analysis to see if thresholds should be LOWERED
3. Approve recommendations that increase TPR
4. Monitor detection rate

### Scenario 3: Insufficient Data

**Symptom:** Analysis returns "insufficient_data" errors

**Action:**
1. Review more fraud reports (get to 50+ total)
2. Wait for more fraud detections naturally
3. Consider lowering min_samples (risky)

### Scenario 4: One Detector is Broken

**Symptom:** `success_rate_anomaly` has low confidence but others are high

**Action:**
1. Analyze just that detector: `python query/threshold_tuner.py analyze-detector --detector success_rate_anomaly`
2. Check sample size and data balance
3. If insufficient data, reject recommendation
4. If data looks good but you're unsure, ask for expert review

---

## Advanced Usage

### Analyze Single Detector

```bash
python query/threshold_tuner.py analyze-detector \
  --detector success_rate_anomaly \
  --target-fpr 0.05
```

### Analyze Classification Thresholds Only

```bash
python query/threshold_tuner.py analyze-classification
```

### Custom Target FPR

```bash
python query/threshold_tuner.py full-analysis --target-fpr 0.02
```

Stricter FPR (2% instead of 5%), fewer false positives but may miss some fraud.

### View Threshold History

```bash
sqlite3 ~/.claude/emergent-learning/memory/index.db \
  "SELECT * FROM threshold_change_log ORDER BY applied_at DESC LIMIT 10"
```

Shows last 10 threshold changes with deltas and who made them.

### Check Active Thresholds

```bash
sqlite3 ~/.claude/emergent-learning/memory/index.db \
  "SELECT * FROM active_thresholds"
```

Shows current thresholds for all detectors and classification levels.

---

## Safety Mechanisms

### 1. Safety Bounds

**Classification:**
- `suspicious`: [0.10, 0.40]
- `fraud_likely`: [0.30, 0.70]
- `fraud_confirmed`: [0.60, 0.95]

System will NEVER recommend thresholds outside these ranges.

### 2. Gradual Adjustment

Maximum change per update: ±0.10

Prevents shock to system from large sudden changes.

### 3. Threshold Ordering

Always maintains: `suspicious < fraud_likely < fraud_confirmed`

Minimum separation: 0.10 between levels.

### 4. Minimum Sample Size

- Detector tuning: 30 reviewed signals
- Classification tuning: 50 reviewed reports
- Imbalanced data check: At least 10 TP AND 10 FP

### 5. Rollback

Every change is recorded in `threshold_history` with:
- Old value
- New value
- Who changed it
- When
- Why

Can rollback any change with single command.

---

## Troubleshooting

### "insufficient_data" Error

**Cause:** Not enough reviewed fraud reports

**Fix:**
1. Review more fraud reports in the dashboard
2. Mark them as true_positive or false_positive
3. Re-run analysis when you have 50+ reviews

### "imbalanced_data" Error

**Cause:** Data is 95%+ all true positives or all false positives

**Fix:**
1. Review a more diverse set of reports
2. Ensure you're marking both TP and FP (not just confirming fraud)
3. Need at least 10 of each class

### Recommended Threshold Seems Wrong

**Possible causes:**
1. Sample is not representative (e.g., only reviewed easy cases)
2. Confidence is low (small sample)
3. Algorithm bug (file issue)

**Fix:**
1. Check sample_size and confidence
2. If low, reject and collect more data
3. If high but still seems wrong, investigate data quality

### Applied Threshold Made Things Worse

**Fix:**
1. Find history_id: `SELECT id FROM threshold_history ORDER BY applied_at DESC LIMIT 1`
2. Rollback: `python query/threshold_tuner.py rollback --history-id <id>`
3. Investigate why recommendation was bad
4. File as learning for future tuning

---

## Best Practices

1. **Review regularly:** Quarterly tuning keeps system adapted
2. **Trust the data:** If confidence is high, algorithm is usually right
3. **Start conservative:** When unsure, reject and collect more data
4. **Monitor after changes:** Check FP rate for 30 days after applying
5. **Document decisions:** Use the reason field when applying/rejecting
6. **Keep history:** Don't delete threshold_history records (needed for rollback)

---

## Integration with Fraud Detection

Once you apply threshold updates, the fraud detection system automatically loads them:

**File:** `query/fraud_detector.py`

```python
# On initialization, FraudDetector loads thresholds from database
detector = FraudDetector()  # Automatically loads latest thresholds
```

No need to restart services or reload config - changes are live immediately.

---

## FAQ

**Q: How often should I tune thresholds?**
A: Quarterly is recommended. More frequent if you're accumulating data quickly.

**Q: Can I tune thresholds manually without using this tool?**
A: Yes, you can insert directly into `classification_thresholds` or `detector_thresholds` tables. But this tool provides validation and safety bounds.

**Q: What if I want to use different target FPRs?**
A: Use `--target-fpr` flag. Example: `--target-fpr 0.02` for stricter (2% FPR).

**Q: How do I know if tuning improved performance?**
A: Track metrics before and after:
- Count of false positives per month
- Count of true positives caught
- CEO escalation rate (should stay manageable)

**Q: Can I tune per-domain thresholds?**
A: Not yet implemented. Current design uses global thresholds. Future enhancement.

**Q: What if I want to revert to original Phase 2D defaults?**
A: Delete rows from `classification_thresholds` and re-run migration, OR manually set to 0.20, 0.50, 0.80.

**Q: Is there a way to preview the impact before applying?**
A: Not yet. Recommendation shows achieved_fpr/tpr which estimates impact, but real-world may differ. Apply, monitor, rollback if needed.

---

## Example Workflow

**Month 1-3:** Phase 2D launches
- Fraud detection runs with default thresholds (0.20, 0.50, 0.80)
- CEO reviews fraud reports, marks as TP/FP
- Accumulate 50+ reviews

**Month 4:** First tuning
```bash
python query/threshold_tuner.py full-analysis
python query/threshold_tuner.py pending
# Review recommendations
python query/threshold_tuner.py apply --rec-id 101
python query/threshold_tuner.py apply --rec-id 102
```

**Month 4-6:** Monitor
- Track FP rate
- If acceptable, continue
- If too high, rollback and re-tune

**Month 7:** Second tuning
```bash
python query/threshold_tuner.py full-analysis
# Now with 100+ reviews, confidence should be 'high'
python query/threshold_tuner.py apply --rec-id 110
```

**Ongoing:** Quarterly tuning + on-demand when FP rate spikes

---

## Support

If you encounter issues:
1. Check `threshold_recommendations.reason` field for explanation
2. Review sample_size and confidence
3. Check threshold_history for recent changes
4. File issue with full output of failed command

**Remember:** This system is conservative by design. When in doubt, reject and collect more data.
