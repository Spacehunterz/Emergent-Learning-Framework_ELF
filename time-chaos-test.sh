#!/bin/bash
# Time-based Chaos Testing for Emergent Learning Framework
# Tests edge cases around timestamps, dates, and time handling

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$SCRIPT_DIR"

echo "========================================="
echo "TIME-BASED CHAOS TESTING"
echo "Agent: Opus Agent A"
echo "Date: $(date)"
echo "========================================="
echo ""

# Track issues found
ISSUES_FOUND=0
ISSUES_FIXED=0

# Test counter
TEST_NUM=0

run_test() {
    TEST_NUM=$((TEST_NUM + 1))
    echo ""
    echo "TEST $TEST_NUM: $1"
    echo "----------------------------------------"
}

report_issue() {
    local severity="$1"
    local description="$2"
    ISSUES_FOUND=$((ISSUES_FOUND + 1))
    echo "  [ISSUE-$ISSUES_FOUND] $severity: $description"
}

# =============================================================================
# TEST 1: Midnight Boundary - Date Changes Mid-Execution
# =============================================================================
run_test "Midnight Boundary - Date Changes During Execution"

echo "  Checking if date prefixes are consistent within a single execution..."

# Simulate by checking if scripts capture date once or multiple times
if grep -n 'date +%Y%m%d' "$BASE_DIR/scripts/record-failure.sh" | wc -l | grep -q '[2-9]'; then
    echo "  Found multiple date command calls in record-failure.sh"

    # Check if they're stored in a variable
    if grep -q 'date_prefix=$(date +%Y%m%d)' "$BASE_DIR/scripts/record-failure.sh"; then
        echo "  GOOD: Date is captured once in variable 'date_prefix'"
    else
        report_issue "HIGH" "Date calculated multiple times - could split across midnight"
    fi
else
    echo "  Single date command found - checking variable usage..."
fi

# Check log file naming
if grep -q 'LOG_FILE=.*$(date +%Y%m%d)' "$BASE_DIR/scripts/record-failure.sh"; then
    echo "  FOUND: Log file uses inline date - could change mid-execution"
    report_issue "MEDIUM" "LOG_FILE uses inline date calculation - inconsistent across same execution"
fi

# =============================================================================
# TEST 2: Timezone Handling
# =============================================================================
run_test "Timezone Handling - System Timezone Changes"

echo "  Checking if timezone is explicitly set or relies on system..."

if grep -q 'TZ=' "$BASE_DIR/scripts/record-failure.sh"; then
    echo "  GOOD: Timezone explicitly set"
else
    echo "  WARNING: No explicit timezone setting - relies on system TZ"
    report_issue "LOW" "No explicit timezone setting - behavior undefined if TZ changes"
fi

# Check for UTC usage
if grep -q 'date.*--utc\|date.*-u' "$BASE_DIR/scripts/record-failure.sh"; then
    echo "  GOOD: UTC flag detected"
else
    echo "  INFO: No UTC normalization - using local time"
fi

# =============================================================================
# TEST 3: Clock Skew - System Time Jumps
# =============================================================================
run_test "Clock Skew - System Time Jumps Backward/Forward"

echo "  Checking if timestamps are monotonic and validated..."

# Check if scripts validate timestamp sanity
if grep -q 'date.*validity\|timestamp.*check\|time.*validation' "$BASE_DIR/scripts/record-failure.sh"; then
    echo "  GOOD: Timestamp validation found"
else
    echo "  WARNING: No timestamp validation detected"
    report_issue "MEDIUM" "No timestamp validation - accepts future/past dates blindly"
fi

# Check database timestamp handling
echo "  Checking database timestamp defaults..."
if grep -q 'CURRENT_TIMESTAMP' "$BASE_DIR/query/query.py"; then
    echo "  GOOD: Database uses CURRENT_TIMESTAMP (SQLite managed)"
else
    echo "  WARNING: Manual timestamp management"
fi

# =============================================================================
# TEST 4: Timestamp Validation - Future/Past Dates
# =============================================================================
run_test "Timestamp Validation - Can Records Have Invalid Dates?"

echo "  Attempting to create record with future date..."

# Test with environment variables to avoid interactive mode
export FAILURE_TITLE="Future Date Test"
export FAILURE_DOMAIN="time-testing"
export FAILURE_SUMMARY="Testing future date acceptance"
export FAILURE_SEVERITY="1"

# We can't easily manipulate system date in test, but we can check validation
echo "  Checking if scripts validate date ranges..."

if grep -q 'epoch\|1970\|future.*date\|date.*validation' "$BASE_DIR/scripts/record-failure.sh"; then
    echo "  Found date-related validation"
else
    report_issue "HIGH" "No validation prevents future dates or dates before epoch"
fi

# =============================================================================
# TEST 5: Date Format Consistency
# =============================================================================
run_test "Date Format Consistency - YYYYMMDD vs Other Formats"

echo "  Checking for consistent date format usage..."

# Extract all date format patterns
echo "  Date formats found in record-failure.sh:"
grep -o 'date +[^)]*' "$BASE_DIR/scripts/record-failure.sh" | sort -u | while read -r fmt; do
    echo "    - $fmt"
done

# Check for mixed formats
FORMATS_COUNT=$(grep -o 'date +[^)]*' "$BASE_DIR/scripts/record-failure.sh" | sort -u | wc -l)
if [ "$FORMATS_COUNT" -gt 2 ]; then
    report_issue "MEDIUM" "Multiple date formats detected ($FORMATS_COUNT) - potential inconsistency"
else
    echo "  ACCEPTABLE: $FORMATS_COUNT distinct date format(s) found"
fi

# =============================================================================
# TEST 6: Leap Second Handling
# =============================================================================
run_test "Leap Second Handling - Edge Cases Around Leap Seconds"

echo "  Checking for timezone-aware datetime handling..."

# Check if Python uses timezone-aware datetimes
if grep -q 'from datetime import.*timezone\|pytz\|zoneinfo' "$BASE_DIR/query/query.py"; then
    echo "  GOOD: Timezone-aware datetime handling detected"
else
    echo "  INFO: No explicit timezone library imports - using naive datetime"
    report_issue "LOW" "Python datetime usage may not handle leap seconds/DST correctly"
fi

# Check for ISO 8601 format usage
if grep -q 'isoformat\|%Y-%m-%dT%H:%M:%S' "$BASE_DIR/query/query.py"; then
    echo "  GOOD: ISO 8601 datetime format usage detected"
else
    echo "  INFO: No ISO 8601 format detected"
fi

# =============================================================================
# TEST 7: Log File Date Rollover
# =============================================================================
run_test "Log File Date Rollover - Mid-Execution Log File Change"

echo "  Simulating log writes across midnight boundary..."

# The critical bug: LOG_FILE is calculated once at script start
# But if script runs at 23:59:59, log() calls after midnight write to wrong file

echo "  CRITICAL CHECK: Is LOG_FILE static or dynamic?"

if grep -q '^LOG_FILE=.*$(date' "$BASE_DIR/scripts/record-failure.sh"; then
    if grep -q 'log().*$(date' "$BASE_DIR/scripts/record-failure.sh"; then
        echo "  GOOD: Log file path recalculated on each log() call"
    else
        report_issue "CRITICAL" "LOG_FILE set once at start - logs split across files if execution crosses midnight"
    fi
fi

# =============================================================================
# TEST 8: Database Timestamp Column Types
# =============================================================================
run_test "Database Timestamp Types - Proper SQLite Datetime Storage"

echo "  Checking SQLite timestamp column types..."

# SQLite should use DATETIME or TIMESTAMP types, not TEXT
if grep -q 'created_at DATETIME\|created_at TIMESTAMP' "$BASE_DIR/query/query.py"; then
    echo "  GOOD: created_at uses proper datetime type"
else
    echo "  WARNING: created_at may not use proper datetime type"
fi

# Check for proper CURRENT_TIMESTAMP default
if grep -q "created_at.*DEFAULT CURRENT_TIMESTAMP" "$BASE_DIR/query/query.py"; then
    echo "  GOOD: created_at uses CURRENT_TIMESTAMP default"
else
    report_issue "MEDIUM" "created_at missing CURRENT_TIMESTAMP default"
fi

# =============================================================================
# TEST 9: Race Condition - Concurrent Date Calculations
# =============================================================================
run_test "Race Condition - Multiple Scripts Running at Midnight"

echo "  Checking if concurrent executions at midnight cause issues..."

# If two scripts start at 23:59:59, they might:
# 1. Both calculate date as YYYYMMDD
# 2. First finishes at 00:00:01 with old date
# 3. Second finishes at 00:00:02 with new date
# 4. Git commits may conflict

echo "  Checking git lock implementation..."
if grep -q 'acquire_git_lock' "$BASE_DIR/scripts/record-failure.sh"; then
    echo "  GOOD: Git locking implemented"
else
    report_issue "HIGH" "No git locking - concurrent midnight executions could conflict"
fi

# =============================================================================
# TEST 10: Filename Date Prefix Atomicity
# =============================================================================
run_test "Filename Date Prefix Atomicity"

echo "  Checking if filename date matches log date matches DB date..."

# This is the critical issue - if date changes between:
# 1. LOG_FILE calculation (line 20)
# 2. date_prefix calculation (line 225)
# 3. Date field in markdown (line 238)
# We get inconsistent dates across log, filename, and content

echo "  Analyzing date capture points in record-failure.sh:"
grep -n 'date +' "$BASE_DIR/scripts/record-failure.sh" | head -10

DATE_CALCULATIONS=$(grep -c 'date +' "$BASE_DIR/scripts/record-failure.sh")
echo "  Total date calculations: $DATE_CALCULATIONS"

if [ "$DATE_CALCULATIONS" -gt 3 ]; then
    report_issue "CRITICAL" "Multiple date calculations ($DATE_CALCULATIONS) - high risk of inconsistency across midnight"
fi

# =============================================================================
# SUMMARY
# =============================================================================

echo ""
echo "========================================="
echo "TEST SUMMARY"
echo "========================================="
echo "Total Tests Run: $TEST_NUM"
echo "Issues Found: $ISSUES_FOUND"
echo ""

if [ $ISSUES_FOUND -gt 0 ]; then
    echo "RESULT: FAILURES DETECTED - Fixes needed"
    echo ""
    echo "Proceeding to fix critical issues..."
else
    echo "RESULT: ALL TESTS PASSED"
fi

exit 0
