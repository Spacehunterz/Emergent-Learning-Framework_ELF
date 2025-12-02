#!/bin/bash
# Health Dashboard for Emergent Learning Framework
#
# Displays real-time system health, metrics, and alerts
#
# Usage: ./dashboard.sh [--refresh N] [--json]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$(dirname "$SCRIPT_DIR")"
MEMORY_DIR="$BASE_DIR/memory"
DB_PATH="$MEMORY_DIR/index.db"
LOGS_DIR="$BASE_DIR/logs"
ALERTS_DIR="$BASE_DIR/alerts"

# Source libraries
source "$SCRIPT_DIR/lib/logging.sh"
source "$SCRIPT_DIR/lib/metrics.sh"
source "$SCRIPT_DIR/lib/alerts.sh"

# Initialize
log_init "dashboard"
metrics_init "$DB_PATH"
alerts_init "$BASE_DIR"

# Parse arguments
REFRESH_INTERVAL=0
OUTPUT_FORMAT="text"

while [[ $# -gt 0 ]]; do
    case $1 in
        --refresh)
            REFRESH_INTERVAL="$2"
            shift 2
            ;;
        --json)
            OUTPUT_FORMAT="json"
            shift
            ;;
        --help)
            echo "Usage: $0 [--refresh N] [--json]"
            echo ""
            echo "Options:"
            echo "  --refresh N   Refresh every N seconds (0 = no refresh)"
            echo "  --json        Output in JSON format"
            echo "  --help        Show this help"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

#
# Display dashboard in text format
#
display_text_dashboard() {
    clear
    echo "╔════════════════════════════════════════════════════════════════════════════╗"
    echo "║                 Emergent Learning Framework - Health Dashboard             ║"
    echo "╚════════════════════════════════════════════════════════════════════════════╝"
    echo ""
    echo "Updated: $(date '+%Y-%m-%d %H:%M:%S')"
    echo ""

    # System Status
    echo "┌─────────────────────────────────────────────────────────────────────────────┐"
    echo "│ SYSTEM STATUS                                                               │"
    echo "└─────────────────────────────────────────────────────────────────────────────┘"

    # Check database
    if [ -f "$DB_PATH" ]; then
        local db_size_bytes=$(stat -c%s "$DB_PATH" 2>/dev/null || stat -f%z "$DB_PATH" 2>/dev/null || echo "0")
        local db_size_mb=$((db_size_bytes / 1024 / 1024))
        echo "  Database: OK (${db_size_mb} MB)"
    else
        echo "  Database: MISSING"
    fi

    # Check disk space
    local avail_mb=0
    if df --version 2>&1 | grep -q GNU; then
        avail_mb=$(df -BM "$BASE_DIR" 2>/dev/null | awk 'NR==2 {gsub(/M/,"",$4); print $4}')
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        avail_mb=$(df -m "$BASE_DIR" 2>/dev/null | awk 'NR==2 {print $4}')
    else
        avail_mb=$(df "$BASE_DIR" 2>/dev/null | awk 'NR==2 {print int($4/1024)}')
    fi

    if [ "$avail_mb" -lt 100 ]; then
        echo "  Disk Space: CRITICAL (${avail_mb} MB available)"
    elif [ "$avail_mb" -lt 500 ]; then
        echo "  Disk Space: WARNING (${avail_mb} MB available)"
    else
        echo "  Disk Space: OK (${avail_mb} MB available)"
    fi

    # Check logs
    if [ -d "$LOGS_DIR" ]; then
        local log_count=$(ls -1 "$LOGS_DIR"/*.log 2>/dev/null | wc -l)
        echo "  Logs: OK ($log_count log files)"
    else
        echo "  Logs: No logs directory"
    fi

    echo ""

    # Active Alerts
    echo "┌─────────────────────────────────────────────────────────────────────────────┐"
    echo "│ ACTIVE ALERTS                                                               │"
    echo "└─────────────────────────────────────────────────────────────────────────────┘"

    if [ -f "$ALERTS_DIR/.active_alerts" ]; then
        local alert_count=0
        while IFS='|' read -r alert_id severity timestamp message; do
            local alert_file="$ALERTS_DIR/${alert_id}.alert"
            if [ -f "$alert_file" ] && grep -q "STATUS: active" "$alert_file"; then
                printf "  [%s] %s\n" "$severity" "$message"
                ((alert_count++))
            fi
        done < "$ALERTS_DIR/.active_alerts"

        if [ $alert_count -eq 0 ]; then
            echo "  No active alerts"
        fi
    else
        echo "  No active alerts"
    fi

    echo ""

    # Metrics Summary (Last 24h)
    echo "┌─────────────────────────────────────────────────────────────────────────────┐"
    echo "│ METRICS (Last 24 hours)                                                     │"
    echo "└─────────────────────────────────────────────────────────────────────────────┘"

    if [ -f "$DB_PATH" ] && sqlite3 "$DB_PATH" "SELECT name FROM sqlite_master WHERE type='table' AND name='metrics'" 2>/dev/null | grep -q "metrics"; then
        # Operation counts
        local op_count=$(sqlite3 "$DB_PATH" <<SQL 2>/dev/null || echo "0"
SELECT SUM(metric_value)
FROM metrics
WHERE metric_name = 'operation_count'
  AND timestamp > datetime('now', '-24 hours');
SQL
)
        op_count=${op_count:-0}

        # Success rate
        local success_rate=$(sqlite3 "$DB_PATH" <<SQL 2>/dev/null || echo "0"
SELECT ROUND(
    CAST(SUM(CASE WHEN tags LIKE '%status:success%' THEN metric_value ELSE 0 END) AS REAL) /
    CAST(SUM(metric_value) AS REAL) * 100,
    2
)
FROM metrics
WHERE metric_name = 'operation_count'
  AND timestamp > datetime('now', '-24 hours');
SQL
)
        success_rate=${success_rate:-0}

        # Error count
        local error_count=$(sqlite3 "$DB_PATH" <<SQL 2>/dev/null || echo "0"
SELECT SUM(metric_value)
FROM metrics
WHERE metric_name = 'operation_count'
  AND tags LIKE '%status:failure%'
  AND timestamp > datetime('now', '-24 hours');
SQL
)
        error_count=${error_count:-0}

        echo "  Operations: $op_count total"
        echo "  Success Rate: ${success_rate}%"
        echo "  Errors: $error_count"

        # Average latency
        local avg_latency=$(sqlite3 "$DB_PATH" <<SQL 2>/dev/null || echo "0"
SELECT ROUND(AVG(metric_value), 2)
FROM metrics
WHERE metric_name LIKE '%duration_ms'
  AND timestamp > datetime('now', '-24 hours');
SQL
)
        avg_latency=${avg_latency:-0}
        echo "  Avg Latency: ${avg_latency}ms"

    else
        echo "  No metrics available"
    fi

    echo ""

    # Error Rate Trend (7 days)
    echo "┌─────────────────────────────────────────────────────────────────────────────┐"
    echo "│ ERROR RATE TREND (7 days)                                                   │"
    echo "└─────────────────────────────────────────────────────────────────────────────┘"

    if [ -f "$DB_PATH" ] && sqlite3 "$DB_PATH" "SELECT name FROM sqlite_master WHERE type='table' AND name='metrics'" 2>/dev/null | grep -q "metrics"; then
        sqlite3 "$DB_PATH" <<'SQL' 2>/dev/null | head -7
SELECT
    date(timestamp) as day,
    ROUND(
        CAST(SUM(CASE WHEN tags LIKE '%status:failure%' THEN metric_value ELSE 0 END) AS REAL) /
        CAST(SUM(metric_value) AS REAL) * 100,
        2
    ) || '%' as error_rate,
    SUM(metric_value) as total_ops
FROM metrics
WHERE metric_name = 'operation_count'
  AND timestamp > datetime('now', '-7 days')
GROUP BY day
ORDER BY day DESC;
SQL
    else
        echo "  No metrics available"
    fi
        echo "  No metrics available"
    fi

    echo ""

    # Storage Growth
    echo "┌─────────────────────────────────────────────────────────────────────────────┐"
    echo "│ STORAGE PROJECTION (30 days)                                                │"
    echo "└─────────────────────────────────────────────────────────────────────────────┘"

    if [ -f "$DB_PATH" ]; then
        local current_size_mb=$(($(stat -c%s "$DB_PATH" 2>/dev/null || stat -f%z "$DB_PATH" 2>/dev/null || echo "0") / 1024 / 1024))

        # Get growth rate from last 7 days if metrics available
        local growth_per_day=0
        if sqlite3 "$DB_PATH" "SELECT name FROM sqlite_master WHERE type='table' AND name='metrics'" 2>/dev/null | grep -q "metrics"; then
            local oldest_size=$(sqlite3 "$DB_PATH" <<SQL 2>/dev/null || echo "$current_size_mb"
SELECT metric_value
FROM metrics
WHERE metric_name LIKE '%db_size%'
  AND timestamp > datetime('now', '-7 days')
ORDER BY timestamp ASC
LIMIT 1;
SQL
)
            oldest_size=${oldest_size:-$current_size_mb}
            growth_per_day=$(awk "BEGIN {print ($current_size_mb - $oldest_size) / 7}")
        fi

        local projected_30d=$(awk "BEGIN {print $current_size_mb + ($growth_per_day * 30)}")

        echo "  Current Size: ${current_size_mb} MB"
        echo "  Growth Rate: ${growth_per_day} MB/day"
        echo "  30-day Projection: ${projected_30d} MB"
    else
        echo "  No database available"
    fi

    echo ""

    # Performance Percentiles (24h)
    echo "┌─────────────────────────────────────────────────────────────────────────────┐"
    echo "│ PERFORMANCE PERCENTILES (24 hours)                                          │"
    echo "└─────────────────────────────────────────────────────────────────────────────┘"

    if [ -f "$DB_PATH" ] && sqlite3 "$DB_PATH" "SELECT name FROM sqlite_master WHERE type='table' AND name='metrics'" 2>/dev/null | grep -q "metrics"; then
        # Get latency percentiles (approximation using quartiles)
        local p50=$(sqlite3 "$DB_PATH" <<SQL 2>/dev/null || echo "0"
SELECT ROUND(AVG(metric_value), 2)
FROM (
    SELECT metric_value
    FROM metrics
    WHERE metric_name LIKE '%duration_ms'
      AND timestamp > datetime('now', '-24 hours')
    ORDER BY metric_value
    LIMIT 2 OFFSET (
        SELECT COUNT(*)/2
        FROM metrics
        WHERE metric_name LIKE '%duration_ms'
          AND timestamp > datetime('now', '-24 hours')
    )
);
SQL
)

        local p95=$(sqlite3 "$DB_PATH" <<SQL 2>/dev/null || echo "0"
SELECT ROUND(metric_value, 2)
FROM metrics
WHERE metric_name LIKE '%duration_ms'
  AND timestamp > datetime('now', '-24 hours')
ORDER BY metric_value DESC
LIMIT 1 OFFSET (
    SELECT COUNT(*)/20
    FROM metrics
    WHERE metric_name LIKE '%duration_ms'
      AND timestamp > datetime('now', '-24 hours')
);
SQL
)

        local p99=$(sqlite3 "$DB_PATH" <<SQL 2>/dev/null || echo "0"
SELECT ROUND(metric_value, 2)
FROM metrics
WHERE metric_name LIKE '%duration_ms'
  AND timestamp > datetime('now', '-24 hours')
ORDER BY metric_value DESC
LIMIT 1 OFFSET (
    SELECT COUNT(*)/100
    FROM metrics
    WHERE metric_name LIKE '%duration_ms'
      AND timestamp > datetime('now', '-24 hours')
);
SQL
)

        echo "  p50 (median): ${p50}ms"
        echo "  p95: ${p95}ms"
        echo "  p99: ${p99}ms"
    else
        echo "  No metrics available"
    fi

    echo ""
    echo "────────────────────────────────────────────────────────────────────────────────"

    if [ "$REFRESH_INTERVAL" -gt 0 ]; then
        echo "Refreshing in ${REFRESH_INTERVAL}s... (Ctrl+C to stop)"
    fi
}

#
# Display dashboard in JSON format
#
display_json_dashboard() {
    # TODO: Implement JSON output for programmatic access
    echo "{\"status\": \"json output not yet implemented\"}"
}

#
# Main loop
#
main() {
    if [ "$OUTPUT_FORMAT" = "json" ]; then
        display_json_dashboard
    else
        while true; do
            display_text_dashboard

            if [ "$REFRESH_INTERVAL" -le 0 ]; then
                break
            fi

            sleep "$REFRESH_INTERVAL"
        done
    fi
}

main
