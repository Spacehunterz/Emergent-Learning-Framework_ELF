#!/bin/bash
# Query metrics from the command line
#
# Usage:
#   ./query-metrics.sh recent [metric_name] [limit]
#   ./query-metrics.sh summary [metric_name]
#   ./query-metrics.sh timeseries [metric_name]

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$(dirname "$SCRIPT_DIR")"

# Source metrics library
source "$SCRIPT_DIR/lib/metrics.sh"

# Initialize
metrics_init

# Parse command
QUERY_TYPE="${1:-recent}"
METRIC_NAME="${2:-}"
LIMIT="${3:-20}"

# Execute query
case "$QUERY_TYPE" in
    recent)
        echo "=== Recent Metrics ==="
        if [ -n "$METRIC_NAME" ]; then
            echo "Metric: $METRIC_NAME (last $LIMIT)"
        else
            echo "All metrics (last $LIMIT)"
        fi
        echo ""
        metrics_query recent "$METRIC_NAME" "$LIMIT"
        ;;

    summary)
        echo "=== Metrics Summary ==="
        if [ -n "$METRIC_NAME" ]; then
            echo "Metric: $METRIC_NAME"
        else
            echo "All metrics"
        fi
        echo ""
        metrics_query summary "$METRIC_NAME"
        ;;

    timeseries)
        echo "=== Metrics Time Series (hourly) ==="
        if [ -n "$METRIC_NAME" ]; then
            echo "Metric: $METRIC_NAME"
        else
            echo "All metrics"
        fi
        echo ""
        metrics_query timeseries "$METRIC_NAME"
        ;;

    success-rate)
        if [ -z "$METRIC_NAME" ]; then
            echo "ERROR: success-rate requires operation name"
            echo "Usage: $0 success-rate <operation_name> [hours]"
            exit 1
        fi
        hours="${3:-24}"
        echo "=== Success Rate ==="
        echo "Operation: $METRIC_NAME"
        echo "Time window: Last $hours hours"
        echo ""
        metrics_success_rate "$METRIC_NAME" "$hours"
        ;;

    db-growth)
        echo "=== Database Growth ==="
        echo "Last 30 days"
        echo ""
        metrics_db_growth
        ;;

    cleanup)
        days="${2:-90}"
        echo "=== Cleanup Old Metrics ==="
        echo "Keeping last $days days"
        echo ""
        metrics_cleanup "$days"
        ;;

    *)
        echo "Usage: $0 <query_type> [metric_name] [limit/hours/days]"
        echo ""
        echo "Query types:"
        echo "  recent [metric_name] [limit]        - Show recent metrics"
        echo "  summary [metric_name]                - Show summary statistics"
        echo "  timeseries [metric_name]             - Show hourly time series"
        echo "  success-rate <operation> [hours]     - Calculate success rate"
        echo "  db-growth                            - Show database growth"
        echo "  cleanup [days]                       - Remove old metrics"
        echo ""
        echo "Examples:"
        echo "  $0 recent operation_count 50"
        echo "  $0 summary db_size_mb"
        echo "  $0 timeseries operation_duration_ms"
        echo "  $0 success-rate record_failure 24"
        echo "  $0 db-growth"
        echo "  $0 cleanup 90"
        exit 1
        ;;
esac
