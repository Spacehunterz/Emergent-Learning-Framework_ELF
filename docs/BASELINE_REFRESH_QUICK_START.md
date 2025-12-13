# Baseline Refresh System - Quick Start Guide

## What is This?

The baseline refresh system automatically recalculates domain baselines used in fraud detection. This ensures your fraud detection stays accurate as your heuristics evolve.

**Why it matters:** Baselines define "normal" behavior. Outdated baselines = inaccurate fraud detection.

---

## 1-Minute Setup

### Step 1: Configure Schedule
```bash
cd ~/.claude/emergent-learning
python scripts/baseline-refresh-scheduler.py --setup-schedule --interval-days 30
```

### Step 2: Setup Windows Task Scheduler
```bash
python scripts/baseline-refresh-scheduler.py --setup-task-scheduler
```
Follow the printed instructions to create a Windows scheduled task.

### Step 3: Test It
```bash
python scripts/baseline-refresh-scheduler.py --run-once
```

**Done!** Baselines will now refresh automatically every 30 days.

---

## Common Commands

### Check What Needs Refresh
```bash
python query/fraud_detector.py needs-refresh
```

### Refresh All Baselines Now
```bash
python query/fraud_detector.py refresh-all
```

### Check for Drift Alerts
```bash
python query/fraud_detector.py drift-alerts
```

### View Baseline History
```bash
python query/fraud_detector.py baseline-history --limit 10
```

### Acknowledge Drift Alert
```bash
python scripts/baseline-refresh-scheduler.py --ack-alert 5 --ack-user you --ack-notes "Reason"
```

---

## Understanding Drift Alerts

When baselines change significantly (>20%), you get an alert.

**Severity Levels:**
- **Medium (20-35%):** Monitor - possibly normal evolution
- **High (35-50%):** Review recent fraud reports
- **Critical (50%+):** Investigate immediately

**What to do:**
1. Check `drift-alerts` to see which domains drifted
2. Review baseline history to see trend
3. Investigate recent heuristic changes in that domain
4. Check for fraud reports in that domain
5. Acknowledge alert once reviewed

---

## Typical Workflows

### Weekly Monitoring (5 minutes)
```bash
# Check for drift alerts
python query/fraud_detector.py drift-alerts

# If alerts exist, review history
python query/fraud_detector.py baseline-history --domain problematic-domain

# Acknowledge after review
python scripts/baseline-refresh-scheduler.py --ack-alert ID --ack-user you --ack-notes "Reviewed - normal"
```

### Manual Refresh (when needed)
```bash
# After bulk heuristic changes
python query/fraud_detector.py refresh-all

# Check what changed
python query/fraud_detector.py baseline-history --limit 5
```

### Investigating Fraud
```bash
# When fraud detected in domain "api-calls"
python query/fraud_detector.py baseline-history --domain api-calls

# Look for baseline spikes around fraud detection date
# Check if fraud manipulated the baseline
```

---

## Troubleshooting

### "Insufficient sample size" errors
**Cause:** Domain has < 3 heuristics with < 10 applications each
**Fix:** Normal - wait for more data to accumulate

### Scheduler not running
**Windows Task Scheduler:**
1. Open `taskschd.msc`
2. Find "ELF Baseline Refresh" task
3. Right-click -> Run to test
4. Check "Last Run Result" column

**Daemon mode:**
```bash
# Check if running
tasklist | findstr python

# Stop daemon
# Kill the process via Task Manager

# Restart
python scripts/baseline-refresh-scheduler.py --daemon
```

### Too many drift alerts
**Cause:** Threshold too sensitive (20% default)
**Fix:** Adjust threshold in `fraud_detector.py` line 273
```python
is_significant_drift = abs(drift_percentage) > 30.0  # Raised to 30%
```

---

## Advanced Usage

### Domain-Specific Schedules
```bash
# Refresh "api-calls" domain every 7 days
python scripts/baseline-refresh-scheduler.py --setup-schedule --interval-days 7 --domain api-calls
```

### View All Schedules
```bash
sqlite3 ~/.claude/emergent-learning/memory/index.db \
  "SELECT domain, interval_days, next_refresh FROM baseline_refresh_schedule;"
```

### Check Drift Trends
```bash
# Domains with most drift in last 30 days
sqlite3 ~/.claude/emergent-learning/memory/index.db \
  "SELECT * FROM domains_with_drift ORDER BY max_drift DESC LIMIT 10;"
```

---

## Integration with Dashboard

The baseline refresh system stores data that can be visualized:

1. **Baseline Evolution Chart:** Time-series of baselines per domain
2. **Drift Heatmap:** Which domains are most volatile
3. **Alert Status:** Unacknowledged drift alerts widget

*Dashboard integration coming in future phase.*

---

## Files & Locations

- **Migration:** `memory/migrations/007_baseline_history.sql`
- **Scheduler:** `scripts/baseline-refresh-scheduler.py`
- **CLI:** `query/fraud_detector.py` (commands: refresh-all, drift-alerts, etc.)
- **Tests:** `tests/test_baseline_refresh.py`
- **Logs:** `logs/baseline-refresh.log` (created on first run)

---

## Need Help?

**Check logs:**
```bash
cat ~/.claude/emergent-learning/logs/baseline-refresh.log
```

**Run tests:**
```bash
python tests/test_baseline_refresh.py
```

**Full documentation:**
See `reports/phase3/AGENT_3_BASELINE_REFRESH_REPORT.md`

---

**Remember:** Baselines are the foundation of fraud detection. Keep them fresh!
