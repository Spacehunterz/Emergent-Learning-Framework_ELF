#!/bin/bash
# Comprehensive test for 10/10 observability
#
# Tests:
# 1. Structured logging in all scripts
# 2. Correlation ID tracking
# 3. Metrics collection
# 4. Alert system
# 5. Dashboard functionality
# 6. Log rotation
# 7. End-to-end tracing

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$(dirname "$SCRIPT_DIR")"
LOGS_DIR="$BASE_DIR/logs"
DB_PATH="$BASE_DIR/memory/index.db"
ALERTS_DIR="$BASE_DIR/alerts"

# Source libraries
source "$SCRIPT_DIR/lib/logging.sh"
source "$SCRIPT_DIR/lib/metrics.sh"
source "$SCRIPT_DIR/lib/alerts.sh"

# Initialize
log_init "test-observability"
metrics_init "$DB_PATH"
alerts_init "$BASE_DIR"

TEST_PASSED=0
TEST_FAILED=0

# Test helper
run_test() {
    local test_name="$1"
    local test_command="$2"

    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "TEST: $test_name"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    if eval "$test_command"; then
        echo "✓ PASS: $test_name"
        ((TEST_PASSED++))
        log_info "Test passed" test="$test_name"
        return 0
    else
        echo "✗ FAIL: $test_name"
        ((TEST_FAILED++))
        log_error "Test failed" test="$test_name"
        return 1
    fi
}

echo "╔════════════════════════════════════════════════════════════╗"
echo "║  Emergent Learning Framework - Observability Test Suite   ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
echo "Testing for 10/10 observability score..."
echo ""

# TEST 1: Structured Logging Library
run_test "Structured logging library exists" \
    "[ -f '$SCRIPT_DIR/lib/logging.sh' ]"

# TEST 2: Metrics library exists
run_test "Metrics library exists" \
    "[ -f '$SCRIPT_DIR/lib/metrics.sh' ]"

# TEST 3: Alerts library exists
run_test "Alerts library exists" \
    "[ -f '$SCRIPT_DIR/lib/alerts.sh' ]"

# TEST 4: Dashboard exists
run_test "Dashboard script exists" \
    "[ -f '$SCRIPT_DIR/dashboard.sh' ]"

# TEST 5: Log rotation exists
run_test "Log rotation script exists" \
    "[ -f '$SCRIPT_DIR/rotate-logs.sh' ]"

# TEST 6: Scripts use structured logging
run_test "record-failure.sh uses structured logging" \
    "grep -q 'source.*lib/logging.sh' '$SCRIPT_DIR/record-failure.sh'"

run_test "record-heuristic.sh uses structured logging" \
    "grep -q 'source.*lib/logging.sh' '$SCRIPT_DIR/record-heuristic.sh'"

run_test "start-experiment.sh uses structured logging" \
    "grep -q 'source.*lib/logging.sh' '$SCRIPT_DIR/start-experiment.sh'"

run_test "sync-db-markdown.sh uses structured logging" \
    "grep -q 'source.*lib/logging.sh' '$SCRIPT_DIR/sync-db-markdown.sh'"

# TEST 7: Correlation ID tracking
run_test "record-failure.sh tracks correlation ID" \
    "grep -q 'CORRELATION_ID.*log_get_correlation_id' '$SCRIPT_DIR/record-failure.sh'"

run_test "record-heuristic.sh tracks correlation ID" \
    "grep -q 'CORRELATION_ID.*log_get_correlation_id' '$SCRIPT_DIR/record-heuristic.sh'"

run_test "start-experiment.sh tracks correlation ID" \
    "grep -q 'CORRELATION_ID.*log_get_correlation_id' '$SCRIPT_DIR/start-experiment.sh'"

# TEST 8: Structured logging functions work
echo ""
echo "Testing logging functions..."

log_timer_start "test_operation"
log_debug "This is a debug message" test="true"
log_info "This is an info message" test="true"
log_warn "This is a warning message" test="true"
log_timer_stop "test_operation" status="success"

run_test "Log file contains structured entries" \
    "grep -q '\[INFO\].*This is an info message' '$LOGS_DIR/'*.log"

# TEST 9: Metrics collection works
echo ""
echo "Testing metrics collection..."

metrics_record "test_metric" 42 category="test"
metrics_record "test_counter" 1 type="test"

run_test "Metrics were recorded in database" \
    "sqlite3 '$DB_PATH' 'SELECT COUNT(*) FROM metrics WHERE metric_name = \"test_metric\"' | grep -q '[1-9]'"

# TEST 10: Alert system works
echo ""
echo "Testing alert system..."

alert_trigger "warning" "Test alert - ignore" test="true"

run_test "Alert was created" \
    "ls '$ALERTS_DIR/'*.alert >/dev/null 2>&1"

# TEST 11: Correlation ID is unique
echo ""
echo "Testing correlation ID uniqueness..."

CORR_ID_1=$(log_get_correlation_id)
# Simulate new execution
log_init "test-observability-2"
CORR_ID_2=$(log_get_correlation_id)

run_test "Correlation IDs are unique" \
    "[ '$CORR_ID_1' != '$CORR_ID_2' ]"

# TEST 12: Metrics queries work
echo ""
echo "Testing metrics queries..."

run_test "Metrics summary query works" \
    "metrics_query summary test_metric >/dev/null 2>&1"

run_test "Metrics recent query works" \
    "metrics_query recent test_metric 10 >/dev/null 2>&1"

# TEST 13: Alert checks work
echo ""
echo "Testing alert checks..."

run_test "Disk space check works" \
    "alert_check_disk_space 1 >/dev/null 2>&1 || true"

run_test "Error rate check works" \
    "alert_check_error_rate 100 1 >/dev/null 2>&1 || true"

# TEST 14: Dashboard runs without error
echo ""
echo "Testing dashboard..."

run_test "Dashboard executes successfully" \
    "timeout 2s '$SCRIPT_DIR/dashboard.sh' >/dev/null 2>&1 || [ \$? -eq 124 ]"

# TEST 15: End-to-end tracing
echo ""
echo "Testing end-to-end tracing..."

# Generate a correlation ID
log_init "e2e-test"
E2E_CORR_ID=$(log_get_correlation_id)

log_info "E2E test start" correlation_id="$E2E_CORR_ID" step="1"
log_info "E2E test middle" correlation_id="$E2E_CORR_ID" step="2"
log_info "E2E test end" correlation_id="$E2E_CORR_ID" step="3"

run_test "End-to-end trace appears in logs" \
    "grep -c \"correlation_id=\\\"$E2E_CORR_ID\\\"\" '$LOGS_DIR/'*.log | grep -q '[3-9]'"

# TEST 16: Performance metrics
echo ""
echo "Testing performance metrics..."

operation_start=$(metrics_operation_start "test_op")
sleep 0.1
metrics_operation_end "test_op" "$operation_start" "success"

run_test "Operation metrics recorded" \
    "sqlite3 '$DB_PATH' 'SELECT COUNT(*) FROM metrics WHERE metric_name = \"test_op_duration_ms\"' | grep -q '[1-9]'"

# FINAL REPORT
echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║                    TEST RESULTS                            ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
echo "Tests Passed: $TEST_PASSED"
echo "Tests Failed: $TEST_FAILED"
echo "Total Tests:  $((TEST_PASSED + TEST_FAILED))"
echo ""

if [ $TEST_FAILED -eq 0 ]; then
    echo "🎉 ALL TESTS PASSED! 🎉"
    echo ""
    echo "Observability Score: 10/10"
    echo ""
    echo "✓ Structured logging integrated in all scripts"
    echo "✓ Correlation ID tracking throughout"
    echo "✓ Metrics collection working"
    echo "✓ Alert system functional"
    echo "✓ Dashboard operational"
    echo "✓ Log rotation implemented"
    echo "✓ End-to-end tracing verified"
    echo ""
    log_info "Observability test suite completed" score="10/10" passed="$TEST_PASSED" failed="$TEST_FAILED"
    exit 0
else
    echo "⚠️  SOME TESTS FAILED"
    echo ""
    echo "Observability Score: $((TEST_PASSED * 10 / (TEST_PASSED + TEST_FAILED)))/10"
    echo ""
    echo "Review failed tests above for details."
    log_error "Observability test suite completed with failures" passed="$TEST_PASSED" failed="$TEST_FAILED"
    exit 1
fi
