# Observability Quick Start Guide

**Status**: 10/10 Observability Achieved ✅

## Instant Commands

### View System Health
```bash
cd ~/.claude/emergent-learning
./scripts/dashboard-simple.sh
```

### View Live Logs
```bash
tail -f ~/.claude/emergent-learning/logs/$(date +%Y%m%d).log
```

### Search Logs by Correlation ID
```bash
# After an operation, search for all related logs
grep "correlation_id=\"YOUR-CORRELATION-ID\"" ~/.claude/emergent-learning/logs/*.log
```

### Query Metrics
```bash
# Recent metrics
cd ~/.claude/emergent-learning
sqlite3 memory/index.db "SELECT datetime(timestamp, 'localtime'), metric_name, metric_value FROM metrics ORDER BY timestamp DESC LIMIT 20;"
```

### Check Active Alerts
```bash
ls -lh ~/.claude/emergent-learning/alerts/*.alert
```

### Run Health Checks
```bash
cd ~/.claude/emergent-learning/scripts
source lib/alerts.sh
alerts_init "$HOME/.claude/emergent-learning"
alert_health_check
```

### Rotate Logs
```bash
~/.claude/emergent-learning/scripts/rotate-logs.sh
```

---

## For Script Developers

### Add Observability to Your Script

```bash
#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$(dirname "$SCRIPT_DIR")"
DB_PATH="$BASE_DIR/memory/index.db"

# 1. Source libraries
source "$SCRIPT_DIR/lib/logging.sh"
source "$SCRIPT_DIR/lib/metrics.sh"
source "$SCRIPT_DIR/lib/alerts.sh"

# 2. Initialize
log_init "my-script-name"
metrics_init "$DB_PATH"
alerts_init "$BASE_DIR"

# 3. Get correlation ID
CORRELATION_ID=$(log_get_correlation_id)

# 4. Log your operations
log_info "Starting operation" correlation_id="$CORRELATION_ID"

# 5. Track performance
log_timer_start "my_operation"
op_start=$(metrics_operation_start "my_operation")

# ... your code here ...

# 6. Complete tracking
log_timer_stop "my_operation" status="success" correlation_id="$CORRELATION_ID"
metrics_operation_end "my_operation" "$op_start" "success"

# 7. Trigger alerts if needed
if [ $error_count -gt 10 ]; then
    alert_trigger "critical" "Too many errors: $error_count" correlation_id="$CORRELATION_ID"
fi

log_info "Operation complete" correlation_id="$CORRELATION_ID"
```

---

## Common Tasks

### Track an Operation
```bash
# Start timer
log_timer_start "database_query"

# Do your work
result=$(sqlite3 database.db "SELECT * FROM table")

# Stop timer and log
log_timer_stop "database_query" status="success" rows="$(echo "$result" | wc -l)"
```

### Record a Metric
```bash
# Simple counter
metrics_record "api_calls_count" 1 endpoint="/users"

# Gauge (current value)
metrics_record "active_connections" 42 type="gauge"

# Duration
metrics_record "request_latency_ms" 156.7 endpoint="/api/data"
```

### Trigger an Alert
```bash
# Info alert
alert_trigger "info" "Backup completed successfully" size_mb="150"

# Warning
alert_trigger "warning" "High memory usage" usage_percent="85"

# Critical (auto-escalates to CEO inbox)
alert_trigger "critical" "Database connection failed" retries="3"
```

### Search Logs
```bash
# By level
grep "\[ERROR\]" logs/*.log

# By script
grep "\[my-script\]" logs/*.log

# By correlation ID
grep "correlation_id=\"abc123\"" logs/*.log

# By context
grep "user=alice" logs/*.log
```

---

## Log Levels

- **DEBUG**: Detailed information for diagnosing problems
- **INFO**: General informational messages
- **WARN**: Warning messages for potentially harmful situations
- **ERROR**: Error events that might still allow continued execution
- **FATAL**: Severe errors that will cause termination

---

## Correlation ID

Every script execution gets a unique correlation ID (e.g., `000192bb-14e4`) that appears in:
- All log entries
- All metrics (in tags)
- All alerts

Use it to trace the entire execution flow of an operation.

---

## Metrics Types

Automatically determined by metric name:

- `*_count`, `*_total` → **counter**
- `*_duration*`, `*_latency*`, `*_time*` → **timing**
- `*_size*`, `*_bytes*`, `*_mb*` → **gauge**
- `*_rate`, `*_percent`, `*_ratio` → **rate**

---

## Files & Directories

```
~/.claude/emergent-learning/
├── logs/                          # Log files (date-based)
│   ├── 20251201.log              # Today's logs
│   └── *.log.gz                  # Compressed old logs
├── alerts/                        # Alert files
│   ├── .active_alerts            # Active alerts index
│   └── alert_*.alert             # Individual alerts
├── ceo-inbox/                     # CEO escalations
│   └── alert_*.md                # Critical alerts
├── memory/
│   └── index.db                  # Metrics database
└── scripts/
    ├── lib/
    │   ├── logging.sh            # Logging library
    │   ├── metrics.sh            # Metrics library
    │   └── alerts.sh             # Alerts library
    ├── dashboard-simple.sh        # Health dashboard
    ├── rotate-logs.sh            # Log rotation
    ├── demo-observability.sh     # Live demo
    └── verify-observability.sh   # Verification test
```

---

## Database Schema

```sql
-- Metrics table
CREATE TABLE metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    metric_type TEXT NOT NULL,       -- counter, timing, gauge, rate
    metric_name TEXT NOT NULL,
    metric_value REAL NOT NULL,
    tags TEXT,                       -- Comma-separated key:value pairs
    context TEXT
);

-- Indexes for fast queries
CREATE INDEX idx_metrics_timestamp ON metrics(timestamp DESC);
CREATE INDEX idx_metrics_type ON metrics(metric_type);
CREATE INDEX idx_metrics_name ON metrics(metric_name);
```

---

## Queries

### Recent Operations
```sql
SELECT datetime(timestamp, 'localtime'), metric_name, tags
FROM metrics
WHERE metric_name = 'operation_count'
ORDER BY timestamp DESC
LIMIT 10;
```

### Error Rate (Last 24h)
```sql
SELECT
    ROUND(
        CAST(SUM(CASE WHEN tags LIKE '%status:failure%' THEN metric_value ELSE 0 END) AS REAL) /
        CAST(SUM(metric_value) AS REAL) * 100,
        2
    ) as error_rate_percent
FROM metrics
WHERE metric_name = 'operation_count'
  AND timestamp > datetime('now', '-24 hours');
```

### Average Latency by Operation
```sql
SELECT
    REPLACE(metric_name, '_duration_ms', '') as operation,
    ROUND(AVG(metric_value), 2) as avg_latency_ms,
    COUNT(*) as samples
FROM metrics
WHERE metric_name LIKE '%duration_ms'
  AND timestamp > datetime('now', '-24 hours')
GROUP BY operation
ORDER BY avg_latency_ms DESC;
```

---

## Troubleshooting

### No Logs Appearing
```bash
# Check if logging is initialized
source ~/.claude/emergent-learning/scripts/lib/logging.sh
log_init "test-script"
log_info "Test message"

# Check log file
tail ~/.claude/emergent-learning/logs/$(date +%Y%m%d).log
```

### Metrics Not Recording
```bash
# Check database exists
ls -lh ~/.claude/emergent-learning/memory/index.db

# Check table exists
sqlite3 ~/.claude/emergent-learning/memory/index.db "SELECT name FROM sqlite_master WHERE type='table';"

# Initialize if needed
source ~/.claude/emergent-learning/scripts/lib/metrics.sh
metrics_init ~/.claude/emergent-learning/memory/index.db
```

### Alerts Not Working
```bash
# Check alerts directory
ls -lh ~/.claude/emergent-learning/alerts/

# Create if missing
mkdir -p ~/.claude/emergent-learning/alerts
mkdir -p ~/.claude/emergent-learning/ceo-inbox

# Test alert
source ~/.claude/emergent-learning/scripts/lib/alerts.sh
alerts_init ~/.claude/emergent-learning
alert_trigger "info" "Test alert"
```

---

## Demo

Run the full observability demo:

```bash
~/.claude/emergent-learning/scripts/demo-observability.sh
```

This demonstrates:
1. Structured logging
2. Performance timing
3. Metrics collection
4. Alert triggering
5. End-to-end correlation
6. Health checks

---

## Verification

Verify 10/10 observability:

```bash
~/.claude/emergent-learning/scripts/verify-observability.sh
```

Expected output:
```
RESULTS:
  Passed: 32 / 32
  Failed: 0 / 32
  Score:  10 / 10

🎉 PERFECT SCORE: 10/10 OBSERVABILITY ACHIEVED!
```

---

## Learn More

See full documentation:
- `OBSERVABILITY_10_OF_10_REPORT.md` - Complete implementation report
- `scripts/lib/logging.sh` - Logging library source
- `scripts/lib/metrics.sh` - Metrics library source
- `scripts/lib/alerts.sh` - Alerts library source

---

**Questions?** Check the full report or examine the example scripts in `scripts/`.
