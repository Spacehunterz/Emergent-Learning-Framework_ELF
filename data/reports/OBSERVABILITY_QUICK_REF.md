# Observability Quick Reference

## Logging

```bash
source "$SCRIPT_DIR/lib/logging.sh"
log_init "script-name"

# Log messages
log_debug "Debug message" key="value"
log_info "Info message" key="value"
log_warn "Warning message" key="value"
log_error "Error message" key="value"
log_fatal "Fatal message" key="value"

# Timers
log_timer_start "operation_name"
log_timer_stop "operation_name" status="success"

# Correlation IDs
correlation_id=$(log_get_correlation_id)
log_set_correlation_id "custom-id"

# Configuration
LOG_LEVEL=DEBUG LOG_FORMAT=json ./script.sh
```

## Metrics

```bash
source "$SCRIPT_DIR/lib/metrics.sh"
metrics_init

# Record metrics
metrics_record "metric_name" 123.4 tag1="value1" tag2="value2"

# Track operations
start=$(metrics_operation_start "op_name")
# ... work ...
metrics_operation_end "op_name" "$start" "success" domain="test"

# Query metrics
metrics_query recent [metric_name] [limit]
metrics_query summary [metric_name]
metrics_query timeseries [metric_name]
metrics_success_rate "operation" [hours]
metrics_db_growth
metrics_cleanup [days]
```

## Health Check

```bash
# Run health check
./scripts/health-check.sh                # Text output
./scripts/health-check.sh --verbose      # Detailed
./scripts/health-check.sh --json         # JSON output

# Exit codes
# 0 = Healthy
# 1 = Degraded
# 2 = Critical

# Cron example
0 * * * * /path/to/health-check.sh --json >> /var/log/health.log 2>&1
```

## Dashboard

```bash
# View dashboard
python query/dashboard.py                # Basic view
python query/dashboard.py --detailed     # Detailed view
python query/dashboard.py --json         # JSON output

# Save snapshot
python query/dashboard.py --json --detailed > dashboard.json
```

## Metrics CLI

```bash
# Recent metrics
./scripts/query-metrics.sh recent operation_count 50

# Summary statistics
./scripts/query-metrics.sh summary db_size_mb

# Time series
./scripts/query-metrics.sh timeseries operation_duration_ms

# Success rate
./scripts/query-metrics.sh success-rate record_failure 24

# Database growth
./scripts/query-metrics.sh db-growth

# Cleanup
./scripts/query-metrics.sh cleanup 90
```

## Integration Template

```bash
#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$(dirname "$SCRIPT_DIR")"
DB_PATH="$BASE_DIR/memory/index.db"

# Source libraries
source "$SCRIPT_DIR/lib/logging.sh"
source "$SCRIPT_DIR/lib/metrics.sh"

# Initialize
log_init "my-script"
metrics_init "$DB_PATH"

# Track operation
operation_start=$(metrics_operation_start "my_operation")

# Your logic here
log_info "Starting operation" param="value"

if perform_work; then
    log_info "Operation succeeded"
    metrics_operation_end "my_operation" "$operation_start" "success"
else
    log_error "Operation failed"
    metrics_operation_end "my_operation" "$operation_start" "failure"
    exit 1
fi
```

## Troubleshooting

```bash
# View today's logs
tail -f ~/.claude/emergent-learning/logs/$(date +%Y%m%d).log

# Search for errors
grep ERROR ~/.claude/emergent-learning/logs/$(date +%Y%m%d).log

# Query failed operations
sqlite3 ~/.claude/emergent-learning/memory/index.db \
  "SELECT * FROM metrics WHERE tags LIKE '%status:failure%' ORDER BY timestamp DESC LIMIT 20;"

# Check database integrity
sqlite3 ~/.claude/emergent-learning/memory/index.db "PRAGMA integrity_check;"

# Find stale locks
find ~/.claude/emergent-learning/.git -name "*.dir" -type d -mmin +30
```

## File Locations

```
~/.claude/emergent-learning/
├── scripts/lib/logging.sh      # Logging library
├── scripts/lib/metrics.sh      # Metrics library
├── scripts/health-check.sh     # Health monitoring
├── scripts/query-metrics.sh    # Metrics CLI
├── query/dashboard.py          # Dashboard
├── logs/YYYYMMDD.log          # Log files
└── memory/index.db            # Database (metrics + system_health tables)
```

## Documentation

- `OBSERVABILITY.md` - Complete guide
- `INTEGRATION_GUIDE.md` - Integration patterns
- `OBSERVABILITY_IMPLEMENTATION_REPORT.md` - Implementation details
- `OBSERVABILITY_QUICK_REF.md` - This file
