# Emergent Learning Framework - Observability Guide

Complete observability infrastructure for monitoring, debugging, and analyzing the Emergent Learning Framework.

## Overview

The observability system provides:

1. **Structured Logging** - Consistent, queryable logs with correlation IDs
2. **Metrics Collection** - Performance, operations, and health metrics
3. **Health Checks** - Automated system health monitoring
4. **Dashboard** - Unified view of system status and trends

## Components

### 1. Structured Logging Library

**Location**: `scripts/lib/logging.sh`

#### Features
- Multiple log levels: DEBUG, INFO, WARN, ERROR, FATAL
- Multiple output formats: text (colored for terminal) and JSON
- Correlation IDs for request tracing
- Performance timing
- Context fields (script, operation, record_id)
- Automatic log rotation (keeps 30 days)

#### Usage

```bash
# Source the library
source "$(dirname "${BASH_SOURCE[0]}")/../lib/logging.sh"

# Initialize logging
log_init "my-script"

# Basic logging
log_info "Operation started" operation="create" record_id="123"
log_warn "Low disk space" available_mb="500"
log_error "Database error" error_code="SQLITE_BUSY"
log_debug "Variable value" var="$value"
log_fatal "Critical failure - exiting"

# Performance timing
log_timer_start "database_operation"
# ... do work ...
log_timer_stop "database_operation" operation="insert" status="success"

# Metrics (for integration with metrics system)
log_metric "operations_processed" 42 type="failure" domain="coordination"

# Correlation IDs (for distributed tracing)
correlation_id=$(log_get_correlation_id)
log_set_correlation_id "custom-id-12345"
```

#### Configuration

Environment variables:
- `LOG_LEVEL` - Minimum level to output (DEBUG|INFO|WARN|ERROR|FATAL), default: INFO
- `LOG_FORMAT` - Output format (text|json), default: text
- `LOG_DIR` - Directory for log files, default: ~/.claude/emergent-learning/logs

```bash
# JSON output with DEBUG level
LOG_LEVEL=DEBUG LOG_FORMAT=json ./my-script.sh

# Custom log directory
LOG_DIR=/var/log/emergent ./my-script.sh
```

#### Log Files

- Location: `~/.claude/emergent-learning/logs/`
- Format: `YYYYMMDD.log` (one file per day)
- Rotation: Automatic, keeps last 30 days
- Structure (text):
  ```
  [2025-12-01 14:23:45] [INFO] [my-script] [corr:12ab34cd-5678] operation=create record_id=123 Operation started
  ```
- Structure (JSON):
  ```json
  {"timestamp":"2025-12-01T14:23:45Z","level":"INFO","message":"Operation started","script":"my-script","correlation_id":"12ab34cd-5678","operation":"create","record_id":"123"}
  ```

### 2. Metrics Collection Library

**Location**: `scripts/lib/metrics.sh`

#### Features
- Counter metrics (operation counts, totals)
- Timing metrics (durations, latencies)
- Gauge metrics (sizes, rates)
- Tag-based filtering
- Automatic metric type detection
- Time-series queries
- Success rate calculations

#### Usage

```bash
# Source the library
source "$(dirname "${BASH_SOURCE[0]}")/../lib/metrics.sh"

# Initialize metrics
metrics_init  # Uses default DB path
# OR
metrics_init "/path/to/index.db"

# Record metrics
metrics_record "operation_count" 1 type="failure" domain="coordination"
metrics_record "db_size_mb" 45.2
metrics_record "operation_duration_ms" 1234 operation="record_failure" status="success"

# Track operation duration automatically
start_time=$(metrics_operation_start "my_operation")
# ... do work ...
metrics_operation_end "my_operation" "$start_time" "success" domain="testing"

# Query metrics
metrics_query recent                    # Recent metrics (last 100)
metrics_query recent operation_count 50 # Last 50 operation counts
metrics_query summary                   # Summary statistics
metrics_query timeseries               # Hourly time series

# Calculate success rate
metrics_success_rate "record_failure" 24  # Last 24 hours

# Database growth
metrics_db_growth  # Last 30 days

# Cleanup old metrics
metrics_cleanup 90  # Keep last 90 days
```

#### Metric Types

Automatically determined by metric name:
- `*_count`, `*_total` → counter
- `*_duration*`, `*_latency*`, `*_time*` → timing
- `*_size*`, `*_bytes*`, `*_mb*`, `*_gb*` → gauge
- `*_rate`, `*_percent`, `*_ratio` → rate

#### Database Schema

```sql
CREATE TABLE metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    metric_type TEXT NOT NULL,        -- counter, timing, gauge, rate
    metric_name TEXT NOT NULL,
    metric_value REAL NOT NULL,
    tags TEXT,                         -- key:value,key:value
    context TEXT
);
```

### 3. Health Check Script

**Location**: `scripts/health-check.sh`

#### Features
- Database connectivity and integrity checks
- Disk space monitoring
- Git repository status
- Stale lock detection
- Error rate analysis from logs
- Exit codes for automation (0=healthy, 1=degraded, 2=critical)

#### Usage

```bash
# Basic health check
./scripts/health-check.sh

# Verbose output
./scripts/health-check.sh --verbose

# JSON output (for monitoring systems)
./scripts/health-check.sh --json

# Example cron job (run every hour)
0 * * * * /path/to/emergent-learning/scripts/health-check.sh --json >> /var/log/health.log 2>&1
```

#### Output

Text format:
```
=== Emergent Learning Framework - Health Check ===

Status: HEALTHY
Timestamp: 2025-12-01 14:30:00

Check Results:
  db_connectivity:     ✓ pass
  db_integrity:        ✓ pass
  disk_space:          ✓ pass
  git_status:          ✓ pass
  stale_locks:         ✓ pass
  error_rate:          ✓ pass

Details:
  • Database connectivity: OK
  • Database size: 0MB
  • Disk space available: 50000MB
  • Git: Clean working directory
  • Stale locks: None found
  • Error count (today): 0
```

JSON format:
```json
{
  "status": "healthy",
  "timestamp": "2025-12-01T14:30:00Z",
  "checks": {
    "db_connectivity": "pass",
    "db_integrity": "pass",
    "disk_space": "pass",
    "git_status": "pass",
    "stale_locks": "pass",
    "error_rate": "pass"
  },
  "errors": [],
  "warnings": [],
  "details": [
    "Database connectivity: OK",
    "Database size: 0MB",
    "Disk space available: 50000MB",
    "Git: Clean working directory",
    "Stale locks: None found",
    "Error count (today): 0"
  ]
}
```

#### Exit Codes

- `0` - Healthy: All checks passed
- `1` - Degraded: Warnings present, but functional
- `2` - Critical: Service unavailable or critical issues

#### Thresholds

Configurable in the script:
- `DISK_WARN_THRESHOLD_MB=1000` - Warn if less than 1GB free
- `DISK_CRITICAL_THRESHOLD_MB=100` - Critical if less than 100MB free
- `MAX_STALE_LOCK_AGE_MINUTES=30` - Locks older than 30 minutes are stale

### 4. Dashboard Query

**Location**: `query/dashboard.py`

#### Features
- System health summary
- Recent operations
- Error trends
- Storage usage
- Performance metrics (latency percentiles)
- JSON and text output

#### Usage

```bash
# View dashboard
python query/dashboard.py

# Detailed view
python query/dashboard.py --detailed

# JSON output
python query/dashboard.py --json

# Save to file
python query/dashboard.py --json --detailed > dashboard.json

# Custom base path
python query/dashboard.py --base-path /path/to/emergent-learning
```

#### Output

```
================================================================================
EMERGENT LEARNING FRAMEWORK - DASHBOARD
================================================================================
Generated: 2025-12-01T14:30:00

SYSTEM HEALTH
--------------------------------------------------------------------------------
Status: ✓ HEALTHY
Last Check: 2025-12-01 14:25:00
Database Integrity: pass
Database Size: 0.12 MB
Disk Free: 50000 MB
Stale Locks: 0

24h Health Trend:
  healthy: 24 checks

STORAGE USAGE
--------------------------------------------------------------------------------
Database Size: 0.12 MB (126,976 bytes)
Disk Space Free: 50000 MB

Record Counts:
  learnings           :     15
  heuristics          :      8
  experiments         :      2
  metrics             :    156
  system_health       :     24
  ceo_reviews         :      0

OPERATIONS (Last 24 hours)
--------------------------------------------------------------------------------
Total Operations: 42
Unique Types: 3

By Operation Type:
Type                    Total  Success   Failed     Rate
--------------------------------------------------------------------------------
record_failure             12       11        1     91.7%
record_heuristic            8        8        0    100.0%
query                      22       22        0    100.0%

ERROR TRENDS (Last 7 days)
--------------------------------------------------------------------------------
Error Count by Day:
  2025-12-01: 1 errors
  2025-11-30: 3 errors

Recent Failures:
  [!!!] 2025-12-01 10:15: Database lock timeout (coordination)
  [!!] 2025-11-30 15:45: Git merge conflict (coordination)
```

## Integration Examples

### Integrating into Existing Scripts

Update `record-failure.sh` to use observability:

```bash
#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$(dirname "$SCRIPT_DIR")"

# Source observability libraries
source "$SCRIPT_DIR/lib/logging.sh"
source "$SCRIPT_DIR/lib/metrics.sh"

# Initialize
log_init "record-failure"
metrics_init

# Start operation tracking
operation_start=$(metrics_operation_start "record_failure")

# Your existing code here
log_info "Recording failure" title="$title" domain="$domain"

# ... existing logic ...

if [ $? -eq 0 ]; then
    log_info "Failure recorded successfully" record_id="$LAST_ID"
    metrics_operation_end "record_failure" "$operation_start" "success" domain="$domain"
else
    log_error "Failed to record failure" error="$error_message"
    metrics_operation_end "record_failure" "$operation_start" "failure" domain="$domain"
fi
```

### Python Integration

```python
#!/usr/bin/env python3
import sqlite3
from pathlib import Path

# Record metrics from Python
def record_metric(db_path, metric_name, value, **tags):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Determine metric type
    if '_count' in metric_name or '_total' in metric_name:
        metric_type = 'counter'
    elif '_duration' in metric_name or '_latency' in metric_name:
        metric_type = 'timing'
    elif '_size' in metric_name or '_bytes' in metric_name:
        metric_type = 'gauge'
    else:
        metric_type = 'gauge'

    # Build tags string
    tags_str = ','.join(f"{k}:{v}" for k, v in tags.items())

    cursor.execute("""
        INSERT INTO metrics (metric_type, metric_name, metric_value, tags)
        VALUES (?, ?, ?, ?)
    """, (metric_type, metric_name, value, tags_str))

    conn.commit()
    conn.close()

# Usage
db_path = Path.home() / ".claude" / "emergent-learning" / "memory" / "index.db"
record_metric(db_path, "query_duration_ms", 123.4, operation="build_context", status="success")
```

## Monitoring and Alerting

### Cron Jobs

Add to crontab:

```cron
# Health check every hour
0 * * * * /path/to/emergent-learning/scripts/health-check.sh --json >> /var/log/emergent-health.log 2>&1

# Daily metrics cleanup (keep 90 days)
0 2 * * * /path/to/emergent-learning/scripts/cleanup-metrics.sh

# Daily dashboard snapshot
0 6 * * * /path/to/emergent-learning/query/dashboard.py --json > /var/log/emergent-dashboard-$(date +\%Y\%m\%d).json
```

### Alerting Script

Create `scripts/alert-on-health.sh`:

```bash
#!/bin/bash
# Alert if health check fails

/path/to/scripts/health-check.sh --json > /tmp/health.json
exit_code=$?

if [ $exit_code -eq 2 ]; then
    # Critical - send alert
    mail -s "CRITICAL: Emergent Learning Framework" admin@example.com < /tmp/health.json
elif [ $exit_code -eq 1 ]; then
    # Degraded - send warning
    mail -s "WARNING: Emergent Learning Framework" admin@example.com < /tmp/health.json
fi
```

### Monitoring Dashboard Integration

Export metrics to Prometheus/Grafana:

```bash
# Export metrics in Prometheus format
python query/export-prometheus.py > /var/lib/node_exporter/emergent.prom
```

## Troubleshooting

### High Error Rates

```bash
# Check recent errors
grep ERROR ~/.claude/emergent-learning/logs/$(date +%Y%m%d).log

# Analyze error patterns
sqlite3 ~/.claude/emergent-learning/memory/index.db <<SQL
SELECT
    date(timestamp) as date,
    SUM(metric_value) as error_count
FROM metrics
WHERE metric_name = 'error_count'
GROUP BY date
ORDER BY date DESC
LIMIT 7;
SQL
```

### Performance Issues

```bash
# View operation latencies
python query/dashboard.py --detailed | grep -A 20 "PERFORMANCE METRICS"

# Query slow operations
sqlite3 ~/.claude/emergent-learning/memory/index.db <<SQL
SELECT
    REPLACE(metric_name, '_duration_ms', '') as operation,
    AVG(metric_value) as avg_ms,
    MAX(metric_value) as max_ms
FROM metrics
WHERE metric_name LIKE '%_duration_ms'
  AND timestamp > datetime('now', '-24 hours')
GROUP BY metric_name
HAVING avg_ms > 1000  -- Slower than 1 second
ORDER BY avg_ms DESC;
SQL
```

### Database Issues

```bash
# Check database integrity
sqlite3 ~/.claude/emergent-learning/memory/index.db "PRAGMA integrity_check;"

# Check database size
ls -lh ~/.claude/emergent-learning/memory/index.db

# Analyze table sizes
sqlite3 ~/.claude/emergent-learning/memory/index.db <<SQL
SELECT
    name,
    COUNT(*) as count
FROM sqlite_master
WHERE type='table'
GROUP BY name;
SQL
```

### Stale Locks

```bash
# Find stale locks
find ~/.claude/emergent-learning/.git -name "*.dir" -type d -mmin +30

# Remove stale locks (use with caution!)
find ~/.claude/emergent-learning/.git -name "*.dir" -type d -mmin +30 -exec rmdir {} \;
```

## Best Practices

1. **Always initialize logging and metrics** at the start of scripts
2. **Use correlation IDs** for operations that span multiple scripts
3. **Record both success and failure metrics** to calculate rates
4. **Use appropriate log levels** - reserve ERROR for actual errors
5. **Include context** in log messages (operation, record_id, domain, etc.)
6. **Time critical operations** to detect performance regressions
7. **Run health checks regularly** (e.g., hourly via cron)
8. **Monitor dashboard trends** to catch issues early
9. **Clean up old metrics** periodically to control database size
10. **Use JSON output** for automated monitoring and alerting

## Performance Considerations

- **Logging**: Minimal overhead (~1ms per log entry)
- **Metrics**: ~2-5ms per metric record (includes DB write)
- **Health checks**: ~100-500ms (depends on checks enabled)
- **Dashboard**: ~500ms-2s (depends on data volume and detail level)

## File Locations

```
~/.claude/emergent-learning/
├── scripts/
│   ├── lib/
│   │   ├── logging.sh          # Structured logging library
│   │   └── metrics.sh          # Metrics collection library
│   ├── health-check.sh         # Health monitoring script
│   └── example-with-observability.sh
├── query/
│   └── dashboard.py            # Dashboard query tool
├── logs/
│   ├── 20251201.log           # Daily log files
│   └── 20251130.log
├── memory/
│   └── index.db               # Contains metrics and system_health tables
└── OBSERVABILITY.md           # This file
```

## See Also

- `FRAMEWORK.md` - Overall framework architecture
- `CLAUDE.md` - Configuration and usage instructions
- `query/QUICK_REFERENCE.txt` - Query system quick reference
