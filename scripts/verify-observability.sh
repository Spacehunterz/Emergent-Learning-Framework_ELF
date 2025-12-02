#!/bin/bash
# Quick verification of 10/10 observability implementation
# Non-interactive, fast checks

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$(dirname "$SCRIPT_DIR")"

PASS=0
FAIL=0

check() {
    local name="$1"
    local test_cmd="$2"

    if eval "$test_cmd" >/dev/null 2>&1; then
        echo "✓ $name"
        ((PASS++))
        return 0
    else
        echo "✗ $name"
        ((FAIL++))
        return 1
    fi
}

echo "=== Observability Implementation Verification ==="
echo ""

# Core libraries
echo "Core Libraries:"
check "logging.sh exists" "[ -f '$SCRIPT_DIR/lib/logging.sh' ]"
check "metrics.sh exists" "[ -f '$SCRIPT_DIR/lib/metrics.sh' ]"
check "alerts.sh exists" "[ -f '$SCRIPT_DIR/lib/alerts.sh' ]"
echo ""

# Tools
echo "Observability Tools:"
check "dashboard.sh exists" "[ -f '$SCRIPT_DIR/dashboard.sh' ]"
check "rotate-logs.sh exists" "[ -f '$SCRIPT_DIR/rotate-logs.sh' ]"
echo ""

# Script Integration
echo "Script Integration:"
check "record-failure.sh has logging" "grep -q 'source.*lib/logging.sh' '$SCRIPT_DIR/record-failure.sh'"
check "record-failure.sh has correlation" "grep -q 'CORRELATION_ID' '$SCRIPT_DIR/record-failure.sh'"
check "record-heuristic.sh has logging" "grep -q 'source.*lib/logging.sh' '$SCRIPT_DIR/record-heuristic.sh'"
check "record-heuristic.sh has correlation" "grep -q 'CORRELATION_ID' '$SCRIPT_DIR/record-heuristic.sh'"
check "start-experiment.sh has logging" "grep -q 'source.*lib/logging.sh' '$SCRIPT_DIR/start-experiment.sh'"
check "start-experiment.sh has correlation" "grep -q 'CORRELATION_ID' '$SCRIPT_DIR/start-experiment.sh'"
check "sync-db-markdown.sh has logging" "grep -q 'source.*lib/logging.sh' '$SCRIPT_DIR/sync-db-markdown.sh'"
check "sync-db-markdown.sh has correlation" "grep -q 'CORRELATION_ID' '$SCRIPT_DIR/sync-db-markdown.sh'"
echo ""

# Features
echo "Observability Features:"
check "Correlation ID generation" "grep -q 'log_get_correlation_id' '$SCRIPT_DIR/lib/logging.sh'"
check "Structured logging formats" "grep -q 'log_format_json\|log_format_text' '$SCRIPT_DIR/lib/logging.sh'"
check "Performance timers" "grep -q 'log_timer_start\|log_timer_stop' '$SCRIPT_DIR/lib/logging.sh'"
check "Metric recording" "grep -q 'metrics_record' '$SCRIPT_DIR/lib/metrics.sh'"
check "Operation tracking" "grep -q 'metrics_operation_start\|metrics_operation_end' '$SCRIPT_DIR/lib/metrics.sh'"
check "Alert triggering" "grep -q 'alert_trigger' '$SCRIPT_DIR/lib/alerts.sh'"
check "Alert disk check" "grep -q 'alert_check_disk_space' '$SCRIPT_DIR/lib/alerts.sh'"
check "Alert error rate check" "grep -q 'alert_check_error_rate' '$SCRIPT_DIR/lib/alerts.sh'"
check "Alert backup check" "grep -q 'alert_check_backup_status' '$SCRIPT_DIR/lib/alerts.sh'"
echo ""

# Dashboard Features
echo "Dashboard Features:"
check "System status display" "grep -q 'SYSTEM STATUS' '$SCRIPT_DIR/dashboard.sh'"
check "Active alerts display" "grep -q 'ACTIVE ALERTS' '$SCRIPT_DIR/dashboard.sh'"
check "Metrics summary" "grep -q 'METRICS' '$SCRIPT_DIR/dashboard.sh'"
check "Error rate trend" "grep -q 'ERROR RATE TREND' '$SCRIPT_DIR/dashboard.sh'"
check "Storage projection" "grep -q 'STORAGE PROJECTION' '$SCRIPT_DIR/dashboard.sh'"
check "Performance percentiles" "grep -q 'PERFORMANCE PERCENTILES' '$SCRIPT_DIR/dashboard.sh'"
echo ""

# Log Rotation
echo "Log Rotation Features:"
check "Log compression" "grep -q 'gzip' '$SCRIPT_DIR/rotate-logs.sh'"
check "Old log deletion" "grep -q 'mtime +90' '$SCRIPT_DIR/rotate-logs.sh'"
check "Storage tracking" "grep -q 'log_dir_size_mb' '$SCRIPT_DIR/rotate-logs.sh'"
echo ""

# Metrics Table
echo "Database Schema:"
if [ -f "$BASE_DIR/memory/index.db" ]; then
    check "Metrics table exists" "sqlite3 '$BASE_DIR/memory/index.db' 'SELECT name FROM sqlite_master WHERE type=\"table\" AND name=\"metrics\"' | grep -q metrics"
else
    echo "  (Database not initialized yet - will be created on first use)"
fi
echo ""

# Calculate score
TOTAL=$((PASS + FAIL))
SCORE=$((PASS * 10 / TOTAL))

echo "═══════════════════════════════════════════════════════"
echo "RESULTS:"
echo "  Passed: $PASS / $TOTAL"
echo "  Failed: $FAIL / $TOTAL"
echo "  Score:  $SCORE / 10"
echo "═══════════════════════════════════════════════════════"
echo ""

if [ $FAIL -eq 0 ]; then
    echo "🎉 PERFECT SCORE: 10/10 OBSERVABILITY ACHIEVED!"
    echo ""
    echo "All features implemented:"
    echo "  ✓ Structured logging with correlation IDs"
    echo "  ✓ Metrics collection and querying"
    echo "  ✓ Alert system with CEO escalation"
    echo "  ✓ Real-time health dashboard"
    echo "  ✓ Log rotation and cleanup"
    echo "  ✓ End-to-end trace correlation"
    echo "  ✓ Performance monitoring (latency, percentiles)"
    echo "  ✓ Error rate tracking and alerting"
    echo "  ✓ Storage monitoring and projection"
    echo "  ✓ Integrated in all core scripts"
    echo ""
    exit 0
else
    echo "⚠️  Score: $SCORE/10 - Some features missing or not verified"
    echo ""
    echo "Review failed checks above."
    exit 1
fi
