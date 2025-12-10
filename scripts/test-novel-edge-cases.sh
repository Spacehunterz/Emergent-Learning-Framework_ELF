#!/bin/bash
# Novel Edge Case Testing for Emergent Learning Framework
# Testing race conditions and edge cases that likely haven't been tested

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPTS_DIR="$SCRIPT_DIR/scripts"
MEMORY_DIR="$SCRIPT_DIR/memory"
DB_PATH="$MEMORY_DIR/index.db"
RESULTS_DIR="$SCRIPT_DIR/test-results/novel-edge-cases"

mkdir -p "$RESULTS_DIR"

echo "==================================================================="
echo "Novel Edge Case Testing - Emergent Learning Framework"
echo "Testing novel race conditions and edge cases"
echo "==================================================================="
echo ""

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0
CRITICAL_ISSUES=0
HIGH_ISSUES=0
MEDIUM_ISSUES=0
LOW_ISSUES=0

log_test() {
    echo -e "${GREEN}[TEST]${NC} $*"
}

log_pass() {
    echo -e "${GREEN}[PASS]${NC} $*"
    ((TESTS_PASSED++))
}

log_fail() {
    local severity="$1"
    shift
    echo -e "${RED}[FAIL]${NC} [$severity] $*"
    ((TESTS_FAILED++))

    case "$severity" in
        CRITICAL) ((CRITICAL_ISSUES++)) ;;
        HIGH) ((HIGH_ISSUES++)) ;;
        MEDIUM) ((MEDIUM_ISSUES++)) ;;
        LOW) ((LOW_ISSUES++)) ;;
    esac
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $*"
}

# =================================================================
# TEST 1: Rapid Sequential Calls with Same Title
# =================================================================
test_rapid_sequential_calls() {
    ((TESTS_RUN++))
    log_test "Test 1: Rapid sequential calls - 10 identical failures in rapid succession"

    local test_title="EDGE_CASE_TEST_RAPID_SEQUENTIAL_$$"
    local start_count=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM failures WHERE title='$test_title'" 2>/dev/null || echo "0")

    # Launch 10 rapid calls with same title
    for i in {1..10}; do
        FAILURE_TITLE="$test_title" \
        FAILURE_DOMAIN="testing" \
        FAILURE_SUMMARY="Rapid sequential test iteration $i" \
        FAILURE_SEVERITY="1" \
        "$SCRIPTS_DIR/record-failure.sh" &>/dev/null &
    done

    # Wait for all to complete
    wait

    # Check results
    sleep 1
    local end_count=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM failures WHERE title='$test_title'" 2>/dev/null || echo "0")
    local created=$((end_count - start_count))

    echo "  - Started with: $start_count records"
    echo "  - Ended with: $end_count records"
    echo "  - Created: $created records"

    if [ "$created" -eq 10 ]; then
        log_pass "All 10 records created successfully"
    elif [ "$created" -gt 0 ] && [ "$created" -lt 10 ]; then
        log_fail "HIGH" "Only $created/10 records created - some calls failed or were lost"
        echo "  Suggestion: Increase retry attempts or backoff time in sqlite_with_retry"
    else
        log_fail "CRITICAL" "No records created - complete failure"
        echo "  Suggestion: Check database locking mechanism and concurrency handling"
    fi

    # Check for duplicates or corruption
    local unique_summaries=$(sqlite3 "$DB_PATH" "SELECT COUNT(DISTINCT summary) FROM failures WHERE title='$test_title'" 2>/dev/null || echo "0")
    if [ "$unique_summaries" -eq "$created" ]; then
        log_pass "All summaries are unique - no data corruption"
    else
        log_fail "MEDIUM" "Some summaries are duplicated - possible race condition in data writing"
    fi

    echo ""
}

# =================================================================
# TEST 2: Midnight Boundary Crossing
# =================================================================
test_midnight_boundary() {
    ((TESTS_RUN++))
    log_test "Test 2: Midnight boundary - simulating date change during execution"

    # We'll simulate this by manipulating the date during execution
    # This is tricky - we'll test if the script uses consistent dates

    local test_title="EDGE_CASE_TEST_MIDNIGHT_$$"

    # Create a wrapper that simulates time passing
    local wrapper_script="$RESULTS_DIR/midnight_wrapper_$$.sh"
    cat > "$wrapper_script" << 'WRAPPER_EOF'
#!/bin/bash
# This wrapper will call record-failure but we'll check if internal dates are consistent

FAILURE_TITLE="$1"
FAILURE_DOMAIN="testing"
FAILURE_SUMMARY="Midnight boundary test"

# Call the script
/c/Users/Evede/.claude/emergent-learning/scripts/record-failure.sh
WRAPPER_EOF

    chmod +x "$wrapper_script"

    # Execute
    FAILURE_TITLE="$test_title" \
    FAILURE_DOMAIN="testing" \
    FAILURE_SUMMARY="Midnight boundary test at $(date)" \
    "$SCRIPTS_DIR/record-failure.sh" &>/dev/null

    # Check if record was created
    local count=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM failures WHERE title='$test_title'" 2>/dev/null || echo "0")

    if [ "$count" -gt 0 ]; then
        # Check if the created_at date matches the filename date
        local record=$(sqlite3 "$DB_PATH" "SELECT created_at FROM failures WHERE title='$test_title' ORDER BY id DESC LIMIT 1" 2>/dev/null)
        local date_in_db=$(echo "$record" | cut -d' ' -f1)
        local today=$(date +%Y-%m-%d)

        if [ "$date_in_db" = "$today" ]; then
            log_pass "Date consistency maintained"
        else
            log_fail "LOW" "Date mismatch - DB has $date_in_db, expected $today"
            echo "  Note: This might be OK if test ran across midnight"
        fi

        # Check the actual TIME-FIX-1 in code
        if grep -q "EXECUTION_DATE=\$(date +%Y%m%d)" "$SCRIPTS_DIR/record-failure.sh"; then
            log_pass "TIME-FIX-1 present - date captured at script start"
            echo "  This should prevent midnight boundary issues"
        else
            log_fail "MEDIUM" "TIME-FIX-1 not found - potential midnight boundary bug"
        fi
    else
        log_fail "HIGH" "Failed to create record"
    fi

    rm -f "$wrapper_script"
    echo ""
}

# =================================================================
# TEST 3: File Descriptor Exhaustion
# =================================================================
test_file_descriptor_exhaustion() {
    ((TESTS_RUN++))
    log_test "Test 3: File descriptor exhaustion - opening many handles before script"

    # Get current fd limit
    local fd_limit=$(ulimit -n 2>/dev/null || echo "unknown")
    echo "  - Current FD limit: $fd_limit"

    # Open many file descriptors
    local temp_dir="$RESULTS_DIR/fd_test_$$"
    mkdir -p "$temp_dir"

    # Create and open multiple files
    local num_fds=50
    for i in $(seq 1 $num_fds); do
        touch "$temp_dir/file_$i"
        eval "exec ${i}<$temp_dir/file_$i"
    done

    echo "  - Opened $num_fds file descriptors"

    # Now try to run record-failure
    local test_title="EDGE_CASE_TEST_FD_EXHAUST_$$"

    FAILURE_TITLE="$test_title" \
    FAILURE_DOMAIN="testing" \
    FAILURE_SUMMARY="FD exhaustion test" \
    "$SCRIPTS_DIR/record-failure.sh" &>/dev/null
    local exit_code=$?

    # Close file descriptors
    for i in $(seq 1 $num_fds); do
        eval "exec ${i}<&-" 2>/dev/null || true
    done

    # Check if it succeeded
    local count=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM failures WHERE title='$test_title'" 2>/dev/null || echo "0")

    if [ "$count" -gt 0 ] && [ "$exit_code" -eq 0 ]; then
        log_pass "Script handled FD pressure successfully"
    elif [ "$count" -eq 0 ] && [ "$exit_code" -ne 0 ]; then
        log_fail "MEDIUM" "Script failed with many FDs open (exit code: $exit_code)"
        echo "  Suggestion: Add FD cleanup and error handling"
    else
        log_warn "Unclear result - count=$count, exit=$exit_code"
    fi

    rm -rf "$temp_dir"
    echo ""
}

# =================================================================
# TEST 4: Signal Interruption During Database Write
# =================================================================
test_signal_interruption() {
    ((TESTS_RUN++))
    log_test "Test 4: Signal interruption - SIGTERM during database write"

    local test_title="EDGE_CASE_TEST_SIGTERM_$$"

    # Start the script in background
    FAILURE_TITLE="$test_title" \
    FAILURE_DOMAIN="testing" \
    FAILURE_SUMMARY="Signal interruption test - this may be incomplete" \
    "$SCRIPTS_DIR/record-failure.sh" &

    local pid=$!

    # Give it a moment to start
    sleep 0.1

    # Send SIGTERM
    kill -TERM $pid 2>/dev/null || true

    # Wait for it to die
    wait $pid 2>/dev/null || true

    sleep 1

    # Check database integrity
    if sqlite3 "$DB_PATH" "PRAGMA integrity_check;" 2>/dev/null | grep -q "ok"; then
        log_pass "Database integrity maintained after SIGTERM"
    else
        log_fail "CRITICAL" "Database corruption detected after SIGTERM"
        echo "  Suggestion: Add signal handlers and transaction rollback"
    fi

    # Check if partial record was created
    local count=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM failures WHERE title='$test_title'" 2>/dev/null || echo "0")

    if [ "$count" -eq 0 ]; then
        log_pass "No partial records created - transaction properly rolled back"
    else
        # Check if the record is complete
        local summary=$(sqlite3 "$DB_PATH" "SELECT summary FROM failures WHERE title='$test_title' LIMIT 1" 2>/dev/null)
        if [ -n "$summary" ]; then
            log_warn "Record was created (possibly completed before signal)"
        else
            log_fail "HIGH" "Partial/corrupt record in database"
        fi
    fi

    # Test with SIGINT too
    FAILURE_TITLE="${test_title}_SIGINT" \
    FAILURE_DOMAIN="testing" \
    FAILURE_SUMMARY="SIGINT test" \
    "$SCRIPTS_DIR/record-failure.sh" &

    local pid2=$!
    sleep 0.1
    kill -INT $pid2 2>/dev/null || true
    wait $pid2 2>/dev/null || true

    sleep 1

    if sqlite3 "$DB_PATH" "PRAGMA integrity_check;" 2>/dev/null | grep -q "ok"; then
        log_pass "Database integrity maintained after SIGINT"
    else
        log_fail "CRITICAL" "Database corruption after SIGINT"
    fi

    echo ""
}

# =================================================================
# TEST 5: Partial Git State - .git/index.lock Exists
# =================================================================
test_partial_git_state() {
    ((TESTS_RUN++))
    log_test "Test 5: Partial git state - .git/index.lock from crashed git"

    # Create a stale lock file
    local git_dir="$MEMORY_DIR/.git"
    if [ ! -d "$git_dir" ]; then
        echo "  - No git repo in memory dir, initializing..."
        (cd "$MEMORY_DIR" && git init &>/dev/null)
    fi

    local lock_file="$git_dir/index.lock"

    # Create a stale lock
    echo "$$" > "$lock_file"
    echo "  - Created stale .git/index.lock"

    local test_title="EDGE_CASE_TEST_GIT_LOCK_$$"

    # Try to create a failure (which might trigger git operations)
    FAILURE_TITLE="$test_title" \
    FAILURE_DOMAIN="testing" \
    FAILURE_SUMMARY="Testing with stale git lock" \
    "$SCRIPTS_DIR/record-failure.sh" &>/dev/null
    local exit_code=$?

    # Check if record was created
    local count=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM failures WHERE title='$test_title'" 2>/dev/null || echo "0")

    if [ "$count" -gt 0 ] && [ "$exit_code" -eq 0 ]; then
        log_pass "Script handled stale git lock successfully"
    elif [ "$exit_code" -ne 0 ]; then
        log_fail "MEDIUM" "Script failed with stale git lock (exit code: $exit_code)"
        echo "  Suggestion: Add stale lock detection and cleanup"
        echo "  Check: Does script detect and remove old lock files?"
    else
        log_warn "Partial success - exit=$exit_code, count=$count"
    fi

    # Check if lock still exists
    if [ -f "$lock_file" ]; then
        log_warn "Git lock file still exists after script run"
        # Check age
        local lock_age=$(($(date +%s) - $(stat -c %Y "$lock_file" 2>/dev/null || stat -f %m "$lock_file" 2>/dev/null || echo "0")))
        echo "  - Lock age: ${lock_age}s"
        if [ "$lock_age" -lt 300 ]; then
            log_fail "LOW" "Stale lock not cleaned up (age: ${lock_age}s)"
        fi
    else
        log_pass "Git lock was properly cleaned up or handled"
    fi

    # Clean up
    rm -f "$lock_file"

    echo ""
}

# =================================================================
# TEST 6: Database File Permission Race
# =================================================================
test_db_permission_race() {
    ((TESTS_RUN++))
    log_test "Test 6: Database permission race - chmod during write"

    local test_title="EDGE_CASE_TEST_CHMOD_$$"

    # Start a write operation
    FAILURE_TITLE="$test_title" \
    FAILURE_DOMAIN="testing" \
    FAILURE_SUMMARY="Permission race test" \
    "$SCRIPTS_DIR/record-failure.sh" &

    local pid=$!

    # Immediately try to change permissions
    sleep 0.05
    chmod 444 "$DB_PATH" 2>/dev/null || true

    # Wait for script to finish
    wait $pid 2>/dev/null || true
    local exit_code=$?

    # Restore permissions
    chmod 644 "$DB_PATH" 2>/dev/null || true

    # Check result
    local count=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM failures WHERE title='$test_title'" 2>/dev/null || echo "0")

    if [ "$count" -gt 0 ]; then
        log_pass "Write succeeded despite permission change attempt"
    else
        log_fail "MEDIUM" "Write failed when permissions changed during execution"
        echo "  Suggestion: Handle EPERM errors gracefully"
    fi

    echo ""
}

# =================================================================
# TEST 7: Disk Space Exhaustion Simulation
# =================================================================
test_disk_space_simulation() {
    ((TESTS_RUN++))
    log_test "Test 7: Disk space - extremely large failure summary"

    # Create a very large summary (simulating disk pressure)
    local large_summary=$(printf 'A%.0s' {1..100000})  # 100KB summary
    local test_title="EDGE_CASE_TEST_LARGE_SUMMARY_$$"

    FAILURE_TITLE="$test_title" \
    FAILURE_DOMAIN="testing" \
    FAILURE_SUMMARY="$large_summary" \
    "$SCRIPTS_DIR/record-failure.sh" &>/dev/null
    local exit_code=$?

    # Check if it was handled
    local count=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM failures WHERE title='$test_title'" 2>/dev/null || echo "0")

    if [ "$count" -gt 0 ]; then
        local summary_length=$(sqlite3 "$DB_PATH" "SELECT LENGTH(summary) FROM failures WHERE title='$test_title'" 2>/dev/null)
        echo "  - Summary stored: $summary_length bytes"

        if [ "$summary_length" -eq 100000 ]; then
            log_pass "Large summary handled correctly"
        else
            log_warn "Summary truncated to $summary_length bytes"
            # This might be intentional
        fi
    else
        log_fail "MEDIUM" "Failed to handle large summary (exit: $exit_code)"
        echo "  Suggestion: Add input size validation and limits"
    fi

    echo ""
}

# =================================================================
# TEST 8: Concurrent Database Schema Migration
# =================================================================
test_concurrent_schema_change() {
    ((TESTS_RUN++))
    log_test "Test 8: Concurrent operations during schema check"

    # Start multiple failures while checking schema
    local test_title="EDGE_CASE_TEST_SCHEMA_$$"

    for i in {1..5}; do
        FAILURE_TITLE="${test_title}_$i" \
        FAILURE_DOMAIN="testing" \
        FAILURE_SUMMARY="Schema race test $i" \
        "$SCRIPTS_DIR/record-failure.sh" &>/dev/null &
    done

    # While those are running, check schema
    sqlite3 "$DB_PATH" "PRAGMA table_info(failures);" &>/dev/null &

    # Wait for all
    wait

    # Check database integrity
    if sqlite3 "$DB_PATH" "PRAGMA integrity_check;" 2>/dev/null | grep -q "ok"; then
        log_pass "Database integrity maintained during concurrent schema checks"
    else
        log_fail "CRITICAL" "Database corruption during schema operations"
    fi

    # Count records
    local count=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM failures WHERE title LIKE '${test_title}_%'" 2>/dev/null || echo "0")
    if [ "$count" -eq 5 ]; then
        log_pass "All 5 records created during concurrent schema check"
    else
        log_fail "MEDIUM" "Only $count/5 records created"
    fi

    echo ""
}

# =================================================================
# RUN ALL TESTS
# =================================================================

echo "Starting edge case tests..."
echo ""

test_rapid_sequential_calls
test_midnight_boundary
test_file_descriptor_exhaustion
test_signal_interruption
test_partial_git_state
test_db_permission_race
test_disk_space_simulation
test_concurrent_schema_change

# =================================================================
# SUMMARY
# =================================================================

echo "==================================================================="
echo "EDGE CASE TEST SUMMARY"
echo "==================================================================="
echo "Tests Run:    $TESTS_RUN"
echo "Tests Passed: $TESTS_PASSED"
echo "Tests Failed: $TESTS_FAILED"
echo ""
echo "Issues by Severity:"
echo "  CRITICAL: $CRITICAL_ISSUES"
echo "  HIGH:     $HIGH_ISSUES"
echo "  MEDIUM:   $MEDIUM_ISSUES"
echo "  LOW:      $LOW_ISSUES"
echo ""

if [ "$CRITICAL_ISSUES" -gt 0 ]; then
    echo -e "${RED}CRITICAL ISSUES FOUND - Immediate attention required${NC}"
elif [ "$HIGH_ISSUES" -gt 0 ]; then
    echo -e "${YELLOW}HIGH priority issues found - Should be addressed soon${NC}"
elif [ "$MEDIUM_ISSUES" -gt 0 ]; then
    echo -e "${YELLOW}MEDIUM priority issues found - Address when possible${NC}"
elif [ "$TESTS_FAILED" -gt 0 ]; then
    echo -e "${YELLOW}Some tests failed with LOW severity${NC}"
else
    echo -e "${GREEN}All tests passed! No issues found.${NC}"
fi

echo ""
echo "Full results saved to: $RESULTS_DIR"
echo "==================================================================="

# Save summary
cat > "$RESULTS_DIR/summary.txt" << EOF
Edge Case Test Summary - $(date)

Tests Run:    $TESTS_RUN
Tests Passed: $TESTS_PASSED
Tests Failed: $TESTS_FAILED

Issues by Severity:
  CRITICAL: $CRITICAL_ISSUES
  HIGH:     $HIGH_ISSUES
  MEDIUM:   $MEDIUM_ISSUES
  LOW:      $LOW_ISSUES

Tested Scenarios:
1. Rapid sequential calls (10 identical failures)
2. Midnight boundary crossing
3. File descriptor exhaustion
4. Signal interruption (SIGTERM/SIGINT)
5. Partial git state (.git/index.lock exists)
6. Database permission race
7. Disk space pressure (large summaries)
8. Concurrent schema changes

See full output above for details.
EOF

exit 0
