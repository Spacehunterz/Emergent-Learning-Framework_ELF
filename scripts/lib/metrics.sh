#!/bin/bash
# Metrics collection library for Emergent Learning Framework
#
# Usage:
#   source "$(dirname "${BASH_SOURCE[0]}")/../lib/metrics.sh"
#   metrics_init
#   metrics_record "operation_count" 1 type="failure" domain="coordination"
#   metrics_record "operation_duration_ms" 1234 operation="record_failure"
#   metrics_record "db_size_mb" 45.2
#
# Metrics are stored in the index.db database and can be queried for:
# - Operations count by type
# - Success/failure rates
# - Latency percentiles
# - DB size over time
# - Error rates by category

METRICS_DB="${METRICS_DB:-}"

#
# Initialize metrics subsystem
#
# Args:
#   $1 - Database path (optional, defaults to ~/.claude/emergent-learning/memory/index.db)
#
metrics_init() {
    local db_path="${1:-}"

    if [ -z "$db_path" ]; then
        local home_dir="${HOME:-$USERPROFILE}"
        if [ -n "$home_dir" ]; then
            METRICS_DB="$home_dir/.claude/emergent-learning/memory/index.db"
        else
            METRICS_DB="/tmp/emergent-learning/memory/index.db"
        fi
    else
        METRICS_DB="$db_path"
    fi

    # Verify database exists
    if [ ! -f "$METRICS_DB" ]; then
        echo "ERROR: Metrics database not found: $METRICS_DB" >&2
        return 1
    fi

    # Verify metrics table exists
    if ! sqlite3 "$METRICS_DB" "SELECT name FROM sqlite_master WHERE type='table' AND name='metrics'" 2>/dev/null | grep -q "metrics"; then
        echo "WARN: Metrics table does not exist, creating..." >&2
        _metrics_create_tables
    fi

    return 0
}

#
# Create metrics tables if they don't exist
#
_metrics_create_tables() {
    sqlite3 "$METRICS_DB" <<'SQL'
CREATE TABLE IF NOT EXISTS metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    metric_type TEXT NOT NULL,
    metric_name TEXT NOT NULL,
    metric_value REAL NOT NULL,
    tags TEXT,
    context TEXT
);

CREATE INDEX IF NOT EXISTS idx_metrics_timestamp ON metrics(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_metrics_type ON metrics(metric_type);
CREATE INDEX IF NOT EXISTS idx_metrics_name ON metrics(metric_name);
CREATE INDEX IF NOT EXISTS idx_metrics_type_name ON metrics(metric_type, metric_name, timestamp DESC);
SQL
}

#
# Record a metric
#
# Args:
#   $1 - Metric name (required)
#   $2 - Metric value (required, numeric)
#   ${@:3} - Tags as key=value pairs
#
metrics_record() {
    local metric_name="$1"
    local metric_value="$2"
    shift 2

    if [ -z "$metric_name" ] || [ -z "$metric_value" ]; then
        echo "ERROR: metrics_record requires name and value" >&2
        return 1
    fi

    if [ -z "$METRICS_DB" ]; then
        echo "ERROR: Metrics not initialized. Call metrics_init first." >&2
        return 1
    fi

    # Determine metric type from name
    local metric_type
    case "$metric_name" in
        *_count|*_total)
            metric_type="counter"
            ;;
        *_duration*|*_latency*|*_time*)
            metric_type="timing"
            ;;
        *_size*|*_bytes*|*_mb*|*_gb*)
            metric_type="gauge"
            ;;
        *_rate|*_percent|*_ratio)
            metric_type="rate"
            ;;
        *)
            metric_type="gauge"
            ;;
    esac

    # Build tags string
    local tags=""
    local context=""
    for arg in "$@"; do
        if [[ "$arg" =~ ^([^=]+)=(.*)$ ]]; then
            local key="${BASH_REMATCH[1]}"
            local value="${BASH_REMATCH[2]}"
            if [ -n "$tags" ]; then
                tags+=","
            fi
            tags+="$key:$value"
        fi
    done

    # Escape single quotes for SQL
    metric_name="${metric_name//\'/\'\'}"
    tags="${tags//\'/\'\'}"
    context="${context//\'/\'\'}"
    metric_type="${metric_type//\'/\'\'}"

    # Insert into database with retry
    local max_attempts=3
    local attempt=1
    while [ $attempt -le $max_attempts ]; do
        if sqlite3 "$METRICS_DB" <<SQL 2>/dev/null
INSERT INTO metrics (metric_type, metric_name, metric_value, tags, context)
VALUES ('$metric_type', '$metric_name', $metric_value, '$tags', '$context');
SQL
        then
            return 0
        fi

        sleep 0.$((RANDOM % 3 + 1))
        ((attempt++))
    done

    echo "ERROR: Failed to record metric after $max_attempts attempts" >&2
    return 1
}

#
# Record operation start (for duration tracking)
#
# Args:
#   $1 - Operation name
#
# Returns:
#   Timestamp to be passed to metrics_operation_end
#
metrics_operation_start() {
    local operation_name="$1"

    # Return current timestamp in milliseconds
    date +%s%3N 2>/dev/null || date +%s
}

#
# Record operation end and duration
#
# Args:
#   $1 - Operation name
#   $2 - Start timestamp (from metrics_operation_start)
#   $3 - Status (success/failure)
#   ${@:4} - Additional tags
#
metrics_operation_end() {
    local operation_name="$1"
    local start_time="$2"
    local status="$3"
    shift 3

    local end_time
    end_time="$(date +%s%3N 2>/dev/null || date +%s)"

    local duration=$((end_time - start_time))

    # Record duration
    metrics_record "${operation_name}_duration_ms" "$duration" status="$status" "$@"

    # Record operation count
    metrics_record "operation_count" 1 operation="$operation_name" status="$status" "$@"
}

#
# Query metrics
#
# Args:
#   $1 - Query type (recent|summary|timeseries)
#   $2 - Metric name (optional filter)
#   $3 - Limit (optional, default 100)
#
metrics_query() {
    local query_type="$1"
    local metric_name="${2:-}"
    local limit="${3:-100}"

    if [ -z "$METRICS_DB" ]; then
        echo "ERROR: Metrics not initialized. Call metrics_init first." >&2
        return 1
    fi

    case "$query_type" in
        recent)
            # Recent metrics
            if [ -n "$metric_name" ]; then
                sqlite3 "$METRICS_DB" <<SQL
SELECT datetime(timestamp, 'localtime') as time, metric_name, metric_value, tags
FROM metrics
WHERE metric_name = '$metric_name'
ORDER BY timestamp DESC
LIMIT $limit;
SQL
            else
                sqlite3 "$METRICS_DB" <<SQL
SELECT datetime(timestamp, 'localtime') as time, metric_name, metric_value, tags
FROM metrics
ORDER BY timestamp DESC
LIMIT $limit;
SQL
            fi
            ;;

        summary)
            # Summary statistics
            if [ -n "$metric_name" ]; then
                sqlite3 "$METRICS_DB" <<SQL
SELECT
    metric_name,
    COUNT(*) as count,
    ROUND(AVG(metric_value), 2) as avg,
    ROUND(MIN(metric_value), 2) as min,
    ROUND(MAX(metric_value), 2) as max,
    ROUND(SUM(metric_value), 2) as sum
FROM metrics
WHERE metric_name = '$metric_name'
GROUP BY metric_name;
SQL
            else
                sqlite3 "$METRICS_DB" <<SQL
SELECT
    metric_name,
    COUNT(*) as count,
    ROUND(AVG(metric_value), 2) as avg,
    ROUND(MIN(metric_value), 2) as min,
    ROUND(MAX(metric_value), 2) as max,
    ROUND(SUM(metric_value), 2) as sum
FROM metrics
GROUP BY metric_name
ORDER BY count DESC
LIMIT $limit;
SQL
            fi
            ;;

        timeseries)
            # Time series (hourly aggregation)
            if [ -n "$metric_name" ]; then
                sqlite3 "$METRICS_DB" <<SQL
SELECT
    strftime('%Y-%m-%d %H:00', timestamp) as hour,
    metric_name,
    ROUND(AVG(metric_value), 2) as avg_value,
    COUNT(*) as sample_count
FROM metrics
WHERE metric_name = '$metric_name'
GROUP BY hour, metric_name
ORDER BY hour DESC
LIMIT $limit;
SQL
            else
                sqlite3 "$METRICS_DB" <<SQL
SELECT
    strftime('%Y-%m-%d %H:00', timestamp) as hour,
    metric_name,
    ROUND(AVG(metric_value), 2) as avg_value,
    COUNT(*) as sample_count
FROM metrics
GROUP BY hour, metric_name
ORDER BY hour DESC
LIMIT $limit;
SQL
            fi
            ;;

        *)
            echo "ERROR: Unknown query type: $query_type" >&2
            echo "Valid types: recent, summary, timeseries" >&2
            return 1
            ;;
    esac
}

#
# Calculate success rate for an operation
#
# Args:
#   $1 - Operation name
#   $2 - Time window in hours (default 24)
#
metrics_success_rate() {
    local operation="$1"
    local hours="${2:-24}"

    if [ -z "$METRICS_DB" ]; then
        echo "ERROR: Metrics not initialized. Call metrics_init first." >&2
        return 1
    fi

    sqlite3 "$METRICS_DB" <<SQL
SELECT
    ROUND(
        CAST(SUM(CASE WHEN tags LIKE '%status:success%' THEN metric_value ELSE 0 END) AS REAL) /
        CAST(SUM(metric_value) AS REAL) * 100,
        2
    ) as success_rate_percent,
    SUM(CASE WHEN tags LIKE '%status:success%' THEN metric_value ELSE 0 END) as successes,
    SUM(CASE WHEN tags LIKE '%status:failure%' THEN metric_value ELSE 0 END) as failures,
    SUM(metric_value) as total_operations
FROM metrics
WHERE metric_name = 'operation_count'
  AND tags LIKE '%operation:$operation%'
  AND timestamp > datetime('now', '-$hours hours');
SQL
}

#
# Get database size over time
#
metrics_db_growth() {
    if [ -z "$METRICS_DB" ]; then
        echo "ERROR: Metrics not initialized. Call metrics_init first." >&2
        return 1
    fi

    sqlite3 "$METRICS_DB" <<SQL
SELECT
    date(timestamp) as date,
    ROUND(AVG(metric_value), 2) as avg_size_mb,
    ROUND(MAX(metric_value), 2) as max_size_mb
FROM metrics
WHERE metric_name LIKE '%db_size%'
GROUP BY date
ORDER BY date DESC
LIMIT 30;
SQL
}

#
# Clean old metrics (keep last N days)
#
# Args:
#   $1 - Days to keep (default 90)
#
metrics_cleanup() {
    local days="${1:-90}"

    if [ -z "$METRICS_DB" ]; then
        echo "ERROR: Metrics not initialized. Call metrics_init first." >&2
        return 1
    fi

    local deleted_count
    deleted_count=$(sqlite3 "$METRICS_DB" <<SQL
DELETE FROM metrics
WHERE timestamp < datetime('now', '-$days days');
SELECT changes();
SQL
)

    echo "Cleaned up $deleted_count old metrics (older than $days days)"

    # Vacuum to reclaim space
    sqlite3 "$METRICS_DB" "VACUUM;"
}

# Export functions
export -f metrics_record metrics_operation_start metrics_operation_end
export -f metrics_query metrics_success_rate metrics_db_growth metrics_cleanup
