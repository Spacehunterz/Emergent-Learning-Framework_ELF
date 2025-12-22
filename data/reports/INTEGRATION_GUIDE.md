# Observability Integration Guide

How to integrate the observability infrastructure into existing Emergent Learning Framework scripts.

## Quick Start

### 1. Add to Any Bash Script

```bash
#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$(dirname "$SCRIPT_DIR")"
DB_PATH="$BASE_DIR/memory/index.db"

# Source observability libraries
source "$SCRIPT_DIR/lib/logging.sh"
source "$SCRIPT_DIR/lib/metrics.sh"

# Initialize (do this once at the start)
log_init "my-script-name"
metrics_init "$DB_PATH"

# Your script logic here
log_info "Script started" param1="value1"

# Track performance
operation_start=$(metrics_operation_start "my_operation")

# Do work...
result=$(some_command)

# Record outcome
if [ $? -eq 0 ]; then
    log_info "Operation succeeded" result="$result"
    metrics_operation_end "my_operation" "$operation_start" "success"
else
    log_error "Operation failed" error_code="$?"
    metrics_operation_end "my_operation" "$operation_start" "failure"
fi
```

### 2. Update `record-failure.sh`

Here's how to integrate observability into the existing `record-failure.sh`:

```bash
#!/bin/bash
# At the top of the script, after SCRIPT_DIR definition

# Source observability libraries
source "$SCRIPT_DIR/lib/logging.sh"
source "$SCRIPT_DIR/lib/metrics.sh"

# Replace old logging with new structured logging
# OLD:
# log() {
#     local level="$1"
#     shift
#     echo "[$(date '+%Y-%m-%d %H:%M:%S')] [$level] [record-failure] $*" >> "$LOG_FILE"
# }

# NEW: Initialize logging
log_init "record-failure"
metrics_init "$DB_PATH"

# Track the entire operation
operation_start=$(metrics_operation_start "record_failure")

# In your script logic, update log calls:
# OLD: log "INFO" "Recording failure: $title"
# NEW: log_info "Recording failure" title="$title" domain="$domain" severity="$severity"

# OLD: log "ERROR" "Database insert failed"
# NEW: log_error "Database insert failed" title="$title"

# At the end of the script, record metrics
if [ -n "$LAST_ID" ]; then
    log_info "Failure recorded successfully" record_id="$LAST_ID" filepath="$filepath"
    metrics_operation_end "record_failure" "$operation_start" "success" domain="$domain" severity="$severity"
else
    log_error "Failed to record failure"
    metrics_operation_end "record_failure" "$operation_start" "failure" domain="$domain"
    exit 1
fi
```

### 3. Update `record-heuristic.sh`

```bash
#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$(dirname "$SCRIPT_DIR")"
DB_PATH="$BASE_DIR/memory/index.db"

# Source observability
source "$SCRIPT_DIR/lib/logging.sh"
source "$SCRIPT_DIR/lib/metrics.sh"

log_init "record-heuristic"
metrics_init "$DB_PATH"

operation_start=$(metrics_operation_start "record_heuristic")

# Your existing logic...
log_info "Recording heuristic" domain="$domain" rule="$rule"

# Timer for database operations
log_timer_start "db_insert"

# Insert heuristic
if sqlite3 "$DB_PATH" "INSERT INTO heuristics..."; then
    log_timer_stop "db_insert" status="success"
    log_info "Heuristic recorded" heuristic_id="$LAST_ID"
    metrics_operation_end "record_heuristic" "$operation_start" "success" domain="$domain"
else
    log_timer_stop "db_insert" status="failure"
    log_error "Failed to record heuristic" domain="$domain"
    metrics_operation_end "record_heuristic" "$operation_start" "failure" domain="$domain"
    exit 1
fi
```

### 4. Update `query.py`

Add metrics tracking to the Python query system:

```python
#!/usr/bin/env python3
import sqlite3
import time
from pathlib import Path

class QuerySystem:
    def __init__(self, base_path=None):
        # Existing init code...
        self.metrics_enabled = True

    def _record_metric(self, metric_name, value, **tags):
        """Record a metric to the database."""
        if not self.metrics_enabled:
            return

        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()

            # Determine metric type
            if '_duration' in metric_name or '_latency' in metric_name:
                metric_type = 'timing'
            elif '_count' in metric_name:
                metric_type = 'counter'
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
        except Exception:
            # Don't fail query if metrics recording fails
            pass

    def query_by_domain(self, domain, limit=10):
        """Query with metrics tracking."""
        start_time = time.time()

        try:
            # Existing query logic...
            result = self._existing_query_logic(domain, limit)

            # Record success metrics
            duration_ms = (time.time() - start_time) * 1000
            self._record_metric(
                "query_duration_ms",
                duration_ms,
                query_type="by_domain",
                status="success",
                domain=domain
            )
            self._record_metric("query_count", 1, query_type="by_domain", status="success")

            return result

        except Exception as e:
            # Record failure metrics
            duration_ms = (time.time() - start_time) * 1000
            self._record_metric(
                "query_duration_ms",
                duration_ms,
                query_type="by_domain",
                status="failure",
                domain=domain
            )
            self._record_metric("query_count", 1, query_type="by_domain", status="failure")
            raise
```

## Integration Patterns

### Pattern 1: Simple Operation Tracking

For scripts that perform a single main operation:

```bash
#!/bin/bash
source "$SCRIPT_DIR/lib/logging.sh"
source "$SCRIPT_DIR/lib/metrics.sh"

log_init "my-script"
metrics_init

operation_start=$(metrics_operation_start "main_operation")

# Do work
if perform_work; then
    metrics_operation_end "main_operation" "$operation_start" "success"
else
    metrics_operation_end "main_operation" "$operation_start" "failure"
    exit 1
fi
```

### Pattern 2: Multi-Step Operation Tracking

For scripts with multiple distinct steps:

```bash
#!/bin/bash
source "$SCRIPT_DIR/lib/logging.sh"
source "$SCRIPT_DIR/lib/metrics.sh"

log_init "multi-step-script"
metrics_init

# Track overall operation
overall_start=$(metrics_operation_start "overall")

# Step 1: Validate input
log_info "Validating input"
step1_start=$(metrics_operation_start "validate")
if validate_input; then
    metrics_operation_end "validate" "$step1_start" "success"
else
    metrics_operation_end "validate" "$step1_start" "failure"
    metrics_operation_end "overall" "$overall_start" "failure"
    exit 1
fi

# Step 2: Process data
log_info "Processing data"
step2_start=$(metrics_operation_start "process")
if process_data; then
    metrics_operation_end "process" "$step2_start" "success"
else
    metrics_operation_end "process" "$step2_start" "failure"
    metrics_operation_end "overall" "$overall_start" "failure"
    exit 1
fi

# Step 3: Save results
log_info "Saving results"
step3_start=$(metrics_operation_start "save")
if save_results; then
    metrics_operation_end "save" "$step3_start" "success"
    metrics_operation_end "overall" "$overall_start" "success"
else
    metrics_operation_end "save" "$step3_start" "failure"
    metrics_operation_end "overall" "$overall_start" "failure"
    exit 1
fi
```

### Pattern 3: Error Handling with Logging

```bash
#!/bin/bash
source "$SCRIPT_DIR/lib/logging.sh"
source "$SCRIPT_DIR/lib/metrics.sh"

log_init "error-aware-script"
metrics_init

# Set up error trap
trap 'log_error "Script failed at line $LINENO" exit_code=$?; metrics_record "script_error" 1 line=$LINENO' ERR

operation_start=$(metrics_operation_start "risky_operation")

# Risky operation
if ! risky_command; then
    log_error "Risky command failed" command="risky_command"
    metrics_operation_end "risky_operation" "$operation_start" "failure" reason="command_failed"
    exit 1
fi

log_info "Operation completed successfully"
metrics_operation_end "risky_operation" "$operation_start" "success"
```

### Pattern 4: Database Operations with Retry

```bash
#!/bin/bash
source "$SCRIPT_DIR/lib/logging.sh"
source "$SCRIPT_DIR/lib/metrics.sh"

log_init "db-script"
metrics_init

db_operation_with_metrics() {
    local operation_name="$1"
    local sql_query="$2"

    local attempt=1
    local max_attempts=5

    operation_start=$(metrics_operation_start "$operation_name")

    while [ $attempt -le $max_attempts ]; do
        log_debug "Attempting database operation" operation="$operation_name" attempt="$attempt"

        if sqlite3 "$DB_PATH" "$sql_query" 2>/dev/null; then
            log_info "Database operation succeeded" operation="$operation_name" attempts="$attempt"
            metrics_operation_end "$operation_name" "$operation_start" "success" attempts="$attempt"
            return 0
        fi

        log_warn "Database operation failed, retrying" operation="$operation_name" attempt="$attempt"
        sleep 0.$((RANDOM % 5 + 1))
        ((attempt++))
    done

    log_error "Database operation failed after retries" operation="$operation_name" max_attempts="$max_attempts"
    metrics_operation_end "$operation_name" "$operation_start" "failure" attempts="$max_attempts"
    return 1
}

# Usage
db_operation_with_metrics "insert_learning" "INSERT INTO learnings..."
```

### Pattern 5: Performance-Critical Section

```bash
#!/bin/bash
source "$SCRIPT_DIR/lib/logging.sh"
source "$SCRIPT_DIR/lib/metrics.sh"

log_init "performance-script"
metrics_init

# Track overall performance
log_timer_start "total_execution"

# Critical section 1
log_timer_start "parse_input"
parse_input_data
log_timer_stop "parse_input" status="success"

# Critical section 2
log_timer_start "database_query"
query_database
log_timer_stop "database_query" status="success" rows="$result_count"

# Critical section 3
log_timer_start "generate_output"
generate_output
log_timer_stop "generate_output" status="success" output_size="$output_bytes"

log_timer_stop "total_execution" status="success"
```

## Migration Checklist

When updating an existing script:

- [ ] Add library imports at the top
- [ ] Initialize logging and metrics after directory setup
- [ ] Replace custom log functions with structured logging
- [ ] Add operation tracking for main operations
- [ ] Add performance timers for critical sections
- [ ] Update error handling to use log_error
- [ ] Record success/failure metrics
- [ ] Add context fields to log messages (domain, record_id, etc.)
- [ ] Test the script to ensure metrics are recorded
- [ ] Update documentation

## Testing Integration

After integrating observability:

```bash
# 1. Run your script
./my-updated-script.sh

# 2. Check logs were created
ls -l ~/.claude/emergent-learning/logs/$(date +%Y%m%d).log
tail -20 ~/.claude/emergent-learning/logs/$(date +%Y%m%d).log

# 3. Verify metrics were recorded
sqlite3 ~/.claude/emergent-learning/memory/index.db \
  "SELECT * FROM metrics ORDER BY timestamp DESC LIMIT 10;"

# 4. Check dashboard
python ~/.claude/emergent-learning/query/dashboard.py

# 5. View specific metrics
~/.claude/emergent-learning/scripts/query-metrics.sh recent operation_count 20
~/.claude/emergent-learning/scripts/query-metrics.sh summary
```

## Common Pitfalls

### 1. Not Initializing Libraries

**Wrong:**
```bash
source "$SCRIPT_DIR/lib/logging.sh"
log_info "Starting"  # Will fail - not initialized
```

**Right:**
```bash
source "$SCRIPT_DIR/lib/logging.sh"
log_init "my-script"
log_info "Starting"  # Works
```

### 2. Missing Context Fields

**Wrong:**
```bash
log_info "Operation completed"
```

**Right:**
```bash
log_info "Operation completed" operation="create" record_id="$id" domain="$domain"
```

### 3. Not Recording Failures

**Wrong:**
```bash
if ! do_something; then
    exit 1  # No metrics recorded
fi
```

**Right:**
```bash
operation_start=$(metrics_operation_start "my_op")
if ! do_something; then
    metrics_operation_end "my_op" "$operation_start" "failure"
    exit 1
fi
metrics_operation_end "my_op" "$operation_start" "success"
```

### 4. Forgetting to Stop Timers

**Wrong:**
```bash
log_timer_start "operation"
do_something
# Timer never stopped - leaks memory
```

**Right:**
```bash
log_timer_start "operation"
do_something
log_timer_stop "operation" status="success"
```

## Performance Impact

Typical overhead per operation:

| Operation | Overhead | Notes |
|-----------|----------|-------|
| log_info | ~1ms | Writes to file and stderr |
| log_debug (filtered) | ~0.1ms | Skipped if below LOG_LEVEL |
| metrics_record | ~2-5ms | Includes SQLite write |
| metrics_operation_start | ~0.5ms | Just timestamp capture |
| metrics_operation_end | ~2-5ms | Includes SQLite write |
| log_timer_start | ~0.2ms | Hash table insert |
| log_timer_stop | ~1-2ms | Hash table lookup + log |

**Total overhead for typical script:** 10-30ms

This is negligible for most operations, but for high-frequency operations (>1000/sec), consider:
- Using LOG_LEVEL=WARN in production
- Batching metrics collection
- Using async metrics recording

## See Also

- `OBSERVABILITY.md` - Complete observability documentation
- `scripts/lib/logging.sh` - Logging library source
- `scripts/lib/metrics.sh` - Metrics library source
- `scripts/example-with-observability.sh` - Working example
