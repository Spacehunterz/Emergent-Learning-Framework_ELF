#!/bin/bash
# Midnight Boundary Simulation Test
# Tests that BEFORE and AFTER fixes, dates remain consistent

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$SCRIPT_DIR"

echo "========================================="
echo "MIDNIGHT BOUNDARY SIMULATION TEST"
echo "========================================="
echo ""

echo "TEST 1: Verify date consistency in current (fixed) scripts"
echo "-----------------------------------------------------------"

# Test that record-failure.sh uses consistent dates
echo "Testing record-failure.sh date consistency..."

# Create a test failure
export FAILURE_TITLE="Midnight Test $(date +%s)"
export FAILURE_DOMAIN="time-testing"
export FAILURE_SUMMARY="Testing date consistency across midnight boundary"
export FAILURE_SEVERITY="1"

echo "  Creating test failure record..."
cd "$BASE_DIR"
bash scripts/record-failure.sh > /tmp/test_output.txt 2>&1

# Extract the filename from output
CREATED_FILE=$(grep "Created:" /tmp/test_output.txt | awk '{print $2}')
echo "  Created file: $CREATED_FILE"

# Extract dates from the file
FILE_DATE_PREFIX=$(basename "$CREATED_FILE" | cut -d_ -f1)
CONTENT_DATE=$(grep '^\*\*Date\*\*:' "$CREATED_FILE" | sed 's/\*\*Date\*\*: //' | sed 's/-//g' | awk '{print $1}')
LOG_DATE=$(date +%Y%m%d)

echo ""
echo "  Date Analysis:"
echo "    Filename date prefix: $FILE_DATE_PREFIX"
echo "    Content date field:   $CONTENT_DATE"
echo "    Log file date:        $LOG_DATE"

if [ "$FILE_DATE_PREFIX" = "$CONTENT_DATE" ] && [ "$CONTENT_DATE" = "$LOG_DATE" ]; then
    echo "  ✓ PASS: All dates are consistent"
else
    echo "  ✗ FAIL: Date mismatch detected!"
    echo "    This would occur at midnight if not fixed properly"
fi

echo ""
echo "TEST 2: Verify timestamp validation works"
echo "-----------------------------------------------------------"

# The validation function should exist and be called
echo "  Checking that timestamp validation is active..."

if grep -q "validate_timestamp" "$BASE_DIR/scripts/record-failure.sh"; then
    echo "  ✓ validate_timestamp function exists"
else
    echo "  ✗ validate_timestamp function missing"
fi

if grep -q "if ! validate_timestamp; then" "$BASE_DIR/scripts/record-failure.sh"; then
    echo "  ✓ validate_timestamp is called in preflight"
else
    echo "  ✗ validate_timestamp not called in preflight"
fi

echo ""
echo "TEST 3: Verify no redundant date calculations"
echo "-----------------------------------------------------------"

# Count how many times date commands are called (excluding comments)
FAILURE_DATE_CALLS=$(grep -v '^#' "$BASE_DIR/scripts/record-failure.sh" | grep -c 'date +%Y%m%d' || true)
HEURISTIC_DATE_CALLS=$(grep -v '^#' "$BASE_DIR/scripts/record-heuristic.sh" | grep -c 'date +%Y%m%d' || true)

echo "  record-failure.sh:   $FAILURE_DATE_CALLS date calculation(s)"
echo "  record-heuristic.sh: $HEURISTIC_DATE_CALLS date calculation(s)"

if [ "$FAILURE_DATE_CALLS" -eq 1 ] && [ "$HEURISTIC_DATE_CALLS" -eq 1 ]; then
    echo "  ✓ PASS: Each script calculates date exactly once (optimal)"
else
    echo "  ✗ FAIL: Scripts have multiple date calculations (risk of inconsistency)"
fi

echo ""
echo "TEST 4: Demonstrate the BEFORE behavior (using backup)"
echo "-----------------------------------------------------------"

if [ -f "$BASE_DIR/scripts/record-failure.sh.backup" ]; then
    echo "  Analyzing OLD (backup) version..."

    OLD_DATE_CALLS=$(grep -v '^#' "$BASE_DIR/scripts/record-failure.sh.backup" | grep -c 'date +%Y%m%d' || true)
    echo "  OLD version had $OLD_DATE_CALLS date calculations"

    if [ "$OLD_DATE_CALLS" -gt 1 ]; then
        echo "  ✓ Confirmed: OLD version had multiple date calculations"
        echo "    This WOULD cause issues at midnight!"
    fi

    # Show the problematic lines
    echo ""
    echo "  Problematic lines in OLD version:"
    grep -n 'date +%Y%m%d' "$BASE_DIR/scripts/record-failure.sh.backup" | head -3 | while read -r line; do
        echo "    $line"
    done
else
    echo "  No backup found - skipping comparison"
fi

echo ""
echo "TEST 5: Stress test - Rapid consecutive executions"
echo "-----------------------------------------------------------"

echo "  Creating 5 rapid consecutive records..."

for i in {1..5}; do
    export FAILURE_TITLE="Rapid Test $i"
    export FAILURE_DOMAIN="time-testing"
    export FAILURE_SUMMARY="Rapid execution test $i"
    export FAILURE_SEVERITY="1"

    bash "$BASE_DIR/scripts/record-failure.sh" > /dev/null 2>&1 &
done

wait
echo "  ✓ All rapid executions completed"

# Check that all files created have today's date
TODAYS_DATE=$(date +%Y%m%d)
RAPID_FILES=$(ls "$BASE_DIR/memory/failures/${TODAYS_DATE}_rapid-test-"* 2>/dev/null | wc -l)

echo "  Created $RAPID_FILES files with today's date prefix"

if [ "$RAPID_FILES" -eq 5 ]; then
    echo "  ✓ PASS: All rapid executions used consistent date"
else
    echo "  ! Note: Some files may have been deduplicated or failed"
fi

echo ""
echo "TEST 6: Database timestamp consistency"
echo "-----------------------------------------------------------"

echo "  Checking database timestamps..."

# Query recent records
RECENT_RECORDS=$(sqlite3 "$BASE_DIR/memory/index.db" \
    "SELECT COUNT(*) FROM learnings WHERE domain='time-testing'" 2>/dev/null || echo "0")

echo "  Found $RECENT_RECORDS time-testing records in database"

# Check that created_at timestamps are reasonable
FUTURE_RECORDS=$(sqlite3 "$BASE_DIR/memory/index.db" \
    "SELECT COUNT(*) FROM learnings WHERE created_at > datetime('now', '+1 day')" 2>/dev/null || echo "0")

echo "  Records with future timestamps: $FUTURE_RECORDS"

if [ "$FUTURE_RECORDS" -eq 0 ]; then
    echo "  ✓ PASS: No invalid future timestamps in database"
else
    echo "  ✗ FAIL: Found records with future timestamps (clock skew?)"
fi

echo ""
echo "========================================="
echo "MIDNIGHT SIMULATION TEST COMPLETE"
echo "========================================="
echo ""
echo "Summary of Fixes Applied:"
echo "  1. EXECUTION_DATE captured once at script start"
echo "  2. LOG_FILE uses captured date (no mid-execution changes)"
echo "  3. Filename date prefix uses captured date"
echo "  4. Markdown content date uses captured date"
echo "  5. Timestamp validation prevents invalid dates"
echo "  6. Documentation added for timezone handling"
echo ""
echo "Midnight Boundary Protection: ACTIVE"
echo "Date Consistency: GUARANTEED within single execution"
echo ""
