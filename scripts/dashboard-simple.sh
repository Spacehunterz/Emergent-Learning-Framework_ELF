#!/bin/bash
# Simple Health Dashboard for Emergent Learning Framework

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$(dirname "$SCRIPT_DIR")"
MEMORY_DIR="$BASE_DIR/memory"
DB_PATH="$MEMORY_DIR/index.db"
LOGS_DIR="$BASE_DIR/logs"
ALERTS_DIR="$BASE_DIR/alerts"

clear
echo "╔════════════════════════════════════════════════════════════════════════════╗"
echo "║         Emergent Learning Framework - Health Dashboard                    ║"
echo "╚════════════════════════════════════════════════════════════════════════════╝"
echo ""
echo "Updated: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

# System Status
echo "┌────────────────────────────────────────────────────────────────────────────┐"
echo "│ SYSTEM STATUS                                                              │"
echo "└────────────────────────────────────────────────────────────────────────────┘"

# Database
if [ -f "$DB_PATH" ]; then
    db_size_mb=$(($(stat -c%s "$DB_PATH" 2>/dev/null || stat -f%z "$DB_PATH" 2>/dev/null || echo "0") / 1024 / 1024))
    echo "  Database: OK (${db_size_mb} MB)"
else
    echo "  Database: MISSING"
fi

# Disk space
avail_mb=$(df "$BASE_DIR" 2>/dev/null | awk 'NR==2 {print int($4/1024)}')
if [ "$avail_mb" -lt 100 ]; then
    echo "  Disk Space: CRITICAL (${avail_mb} MB available)"
elif [ "$avail_mb" -lt 500 ]; then
    echo "  Disk Space: WARNING (${avail_mb} MB available)"
else
    echo "  Disk Space: OK (${avail_mb} MB available)"
fi

# Logs
log_count=$(ls -1 "$LOGS_DIR"/*.log 2>/dev/null | wc -l)
echo "  Logs: OK ($log_count log files)"

echo ""

# Active Alerts
echo "┌────────────────────────────────────────────────────────────────────────────┐"
echo "│ ACTIVE ALERTS                                                              │"
echo "└────────────────────────────────────────────────────────────────────────────┘"

if [ -f "$ALERTS_DIR/.active_alerts" ]; then
    alert_count=0
    while IFS='|' read -r alert_id severity timestamp message; do
        alert_file="$ALERTS_DIR/${alert_id}.alert"
        if [ -f "$alert_file" ] && grep -q "STATUS: active" "$alert_file" 2>/dev/null; then
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

# Metrics Summary
echo "┌────────────────────────────────────────────────────────────────────────────┐"
echo "│ METRICS (Last 24 hours)                                                    │"
echo "└────────────────────────────────────────────────────────────────────────────┘"

if [ -f "$DB_PATH" ]; then
    # Total operations
    op_count=$(sqlite3 "$DB_PATH" "SELECT COALESCE(SUM(metric_value), 0) FROM metrics WHERE metric_name = 'operation_count' AND timestamp > datetime('now', '-24 hours');" 2>/dev/null || echo "0")

    # Errors
    error_count=$(sqlite3 "$DB_PATH" "SELECT COALESCE(SUM(metric_value), 0) FROM metrics WHERE metric_name = 'operation_count' AND tags LIKE '%status:failure%' AND timestamp > datetime('now', '-24 hours');" 2>/dev/null || echo "0")

    # Success rate
    if [ "$op_count" -gt 0 ]; then
        success_rate=$(awk "BEGIN {print int((($op_count - $error_count) / $op_count) * 100)}")
    else
        success_rate="N/A"
    fi

    echo "  Operations: $op_count total"
    echo "  Errors: $error_count"
    echo "  Success Rate: ${success_rate}%"
else
    echo "  No metrics available"
fi

echo ""

# Recent Activity
echo "┌────────────────────────────────────────────────────────────────────────────┐"
echo "│ RECENT ACTIVITY (Last 10 operations)                                      │"
echo "└────────────────────────────────────────────────────────────────────────────┘"

if [ -f "$DB_PATH" ]; then
    sqlite3 "$DB_PATH" "SELECT datetime(timestamp, 'localtime'), metric_name, tags FROM metrics WHERE metric_name = 'operation_count' ORDER BY timestamp DESC LIMIT 10;" 2>/dev/null | head -10 | while read -r line; do
        echo "  $line"
    done
else
    echo "  No activity recorded"
fi

echo ""
echo "────────────────────────────────────────────────────────────────────────────────"
echo ""
echo "Commands:"
echo "  View logs: tail -f $LOGS_DIR/$(date +%Y%m%d).log"
echo "  List alerts: ls -lh $ALERTS_DIR/"
echo "  Query metrics: sqlite3 $DB_PATH 'SELECT * FROM metrics ORDER BY timestamp DESC LIMIT 20;'"
echo ""
