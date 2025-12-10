#!/bin/bash
# Simplified Novel Edge Case Testing
# Direct, focused tests without complex wrappers

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPTS_DIR="$SCRIPT_DIR/scripts"
MEMORY_DIR="$SCRIPT_DIR/memory"
DB_PATH="$MEMORY_DIR/index.db"

echo "==================================================================="
echo "NOVEL EDGE CASE TESTING - Emergent Learning Framework"
echo "==================================================================="
echo ""

# Test counter
TEST_NUM=0

# =================================================================
# TEST 1: Rapid Sequential Calls
# =================================================================
((TEST_NUM++))
echo "[$TEST_NUM] Testing: Rapid sequential calls (10 identical failures)"
echo "-------------------------------------------------------------------"

TEST_TITLE="EDGE_TEST_RAPID_$$"
BEFORE=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM failures WHERE title LIKE 'EDGE_TEST_RAPID_%'" 2>/dev/null || echo "0")

echo "Starting 10 parallel record-failure calls..."
for i in {1..10}; do
    (
        export FAILURE_TITLE="$TEST_TITLE"
        export FAILURE_DOMAIN="testing"
        export FAILURE_SUMMARY="Rapid test iteration $i"
        "$SCRIPTS_DIR/record-failure.sh" 2>/dev/null
    ) &
done

echo "Waiting for all processes to complete..."
wait

sleep 2

AFTER=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM failures WHERE title LIKE 'EDGE_TEST_RAPID_%'" 2>/dev/null || echo "0")
CREATED=$((AFTER - BEFORE))

echo "Before: $BEFORE | After: $AFTER | Created: $CREATED"

if [ "$CREATED" -eq 10 ]; then
    echo "✓ PASS: All 10 records created"
    echo "SEVERITY: N/A"
elif [ "$CREATED" -gt 0 ]; then
    echo "✗ FAIL: Only $CREATED/10 records created"
    echo "SEVERITY: HIGH"
    echo "SUGGESTION: Increase retry attempts in sqlite_with_retry()"
else
    echo "✗ FAIL: No records created"
    echo "SEVERITY: CRITICAL"
    echo "SUGGESTION: Check database locking mechanism"
fi
echo ""

# =================================================================
# TEST 2: Midnight Boundary
# =================================================================
((TEST_NUM++))
echo "[$TEST_NUM] Testing: Midnight boundary - date consistency"
echo "-------------------------------------------------------------------"

# Check if TIME-FIX-1 is present
if grep -q "EXECUTION_DATE=\$(date +%Y%m%d)" "$SCRIPTS_DIR/record-failure.sh"; then
    echo "✓ PASS: TIME-FIX-1 detected in code"
    echo "  - Date is captured once at script start"
    echo "  - This prevents midnight boundary issues"
    echo "SEVERITY: N/A"
else
    echo "✗ FAIL: TIME-FIX-1 not found"
    echo "SEVERITY: MEDIUM"
    echo "SUGGESTION: Add EXECUTION_DATE capture at script start"
fi

# Test actual record creation
TEST_TITLE="EDGE_TEST_MIDNIGHT_$$"
export FAILURE_TITLE="$TEST_TITLE"
export FAILURE_DOMAIN="testing"
export FAILURE_SUMMARY="Midnight boundary test"
"$SCRIPTS_DIR/record-failure.sh" 2>/dev/null

sleep 1

# Verify date consistency
RECORD_DATE=$(sqlite3 "$DB_PATH" "SELECT created_at FROM failures WHERE title='$TEST_TITLE' ORDER BY id DESC LIMIT 1" 2>/dev/null | cut -d' ' -f1)
TODAY=$(date +%Y-%m-%d)

if [ "$RECORD_DATE" = "$TODAY" ]; then
    echo "✓ PASS: Record date matches today ($TODAY)"
    echo "SEVERITY: N/A"
else
    echo "✗ FAIL: Date mismatch - DB: $RECORD_DATE, Expected: $TODAY"
    echo "SEVERITY: LOW (could be midnight boundary)"
fi
echo ""

# =================================================================
# TEST 3: File Descriptor Exhaustion
# =================================================================
((TEST_NUM++))
echo "[$TEST_NUM] Testing: File descriptor exhaustion"
echo "-------------------------------------------------------------------"

FD_LIMIT=$(ulimit -n 2>/dev/null || echo "unknown")
echo "Current FD limit: $FD_LIMIT"

# Open 50 file descriptors
TEMP_DIR="$SCRIPT_DIR/test-results/fd_test_$$"
mkdir -p "$TEMP_DIR"

for i in $(seq 3 52); do
    touch "$TEMP_DIR/file_$i"
    eval "exec ${i}>$TEMP_DIR/file_$i" 2>/dev/null || true
done

echo "Opened ~50 file descriptors"

# Try to run record-failure
TEST_TITLE="EDGE_TEST_FD_$$"
export FAILURE_TITLE="$TEST_TITLE"
export FAILURE_DOMAIN="testing"
export FAILURE_SUMMARY="FD exhaustion test"
"$SCRIPTS_DIR/record-failure.sh" 2>/dev/null
EXIT_CODE=$?

# Close FDs
for i in $(seq 3 52); do
    eval "exec ${i}>&-" 2>/dev/null || true
done

sleep 1

COUNT=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM failures WHERE title='$TEST_TITLE'" 2>/dev/null || echo "0")

if [ "$COUNT" -gt 0 ] && [ "$EXIT_CODE" -eq 0 ]; then
    echo "✓ PASS: Script handled FD pressure successfully"
    echo "SEVERITY: N/A"
else
    echo "✗ FAIL: Script failed with many FDs open (exit: $EXIT_CODE, count: $COUNT)"
    echo "SEVERITY: MEDIUM"
    echo "SUGGESTION: Add FD cleanup and error handling"
fi

rm -rf "$TEMP_DIR"
echo ""

# =================================================================
# TEST 4: Signal Interruption (SIGTERM)
# =================================================================
((TEST_NUM++))
echo "[$TEST_NUM] Testing: Signal interruption (SIGTERM during write)"
echo "-------------------------------------------------------------------"

TEST_TITLE="EDGE_TEST_SIGTERM_$$"

# Start in background
(
    export FAILURE_TITLE="$TEST_TITLE"
    export FAILURE_DOMAIN="testing"
    export FAILURE_SUMMARY="Signal interruption test"
    "$SCRIPTS_DIR/record-failure.sh" 2>/dev/null
) &
PID=$!

sleep 0.2
kill -TERM $PID 2>/dev/null || true
wait $PID 2>/dev/null || true

sleep 2

# Check database integrity
INTEGRITY=$(sqlite3 "$DB_PATH" "PRAGMA integrity_check;" 2>/dev/null)
if echo "$INTEGRITY" | grep -q "ok"; then
    echo "✓ PASS: Database integrity maintained after SIGTERM"
    echo "SEVERITY: N/A"
else
    echo "✗ FAIL: Database corruption after SIGTERM"
    echo "SEVERITY: CRITICAL"
    echo "SUGGESTION: Add signal handlers and transaction rollback"
fi

COUNT=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM failures WHERE title='$TEST_TITLE'" 2>/dev/null || echo "0")
echo "Records created: $COUNT (0 expected if signal caught early)"
echo ""

# =================================================================
# TEST 5: Partial Git State (.git/index.lock)
# =================================================================
((TEST_NUM++))
echo "[$TEST_NUM] Testing: Partial git state (.git/index.lock exists)"
echo "-------------------------------------------------------------------"

GIT_DIR="$MEMORY_DIR/.git"
if [ ! -d "$GIT_DIR" ]; then
    echo "Initializing git repo in memory dir..."
    (cd "$MEMORY_DIR" && git init 2>/dev/null)
fi

LOCK_FILE="$GIT_DIR/index.lock"
echo "$$" > "$LOCK_FILE"
echo "Created stale .git/index.lock"

TEST_TITLE="EDGE_TEST_GIT_LOCK_$$"
export FAILURE_TITLE="$TEST_TITLE"
export FAILURE_DOMAIN="testing"
export FAILURE_SUMMARY="Testing with stale git lock"
"$SCRIPTS_DIR/record-failure.sh" 2>/dev/null
EXIT_CODE=$?

sleep 1

COUNT=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM failures WHERE title='$TEST_TITLE'" 2>/dev/null || echo "0")

if [ "$COUNT" -gt 0 ] && [ "$EXIT_CODE" -eq 0 ]; then
    echo "✓ PASS: Script handled stale git lock (count: $COUNT)"
    echo "SEVERITY: N/A"
else
    echo "✗ FAIL: Script failed with stale git lock (exit: $EXIT_CODE, count: $COUNT)"
    echo "SEVERITY: MEDIUM"
    echo "SUGGESTION: Add stale lock detection (check timestamp, remove if > 5 min old)"
fi

if [ -f "$LOCK_FILE" ]; then
    echo "⚠ WARNING: Lock file still exists after script run"
    rm -f "$LOCK_FILE"
fi
echo ""

# =================================================================
# TEST 6: Database Permission Race
# =================================================================
((TEST_NUM++))
echo "[$TEST_NUM] Testing: Database permission race (chmod during write)"
echo "-------------------------------------------------------------------"

TEST_TITLE="EDGE_TEST_CHMOD_$$"

# Start write in background
(
    export FAILURE_TITLE="$TEST_TITLE"
    export FAILURE_DOMAIN="testing"
    export FAILURE_SUMMARY="Permission race test"
    "$SCRIPTS_DIR/record-failure.sh" 2>/dev/null
) &
PID=$!

# Immediately chmod
sleep 0.1
chmod 444 "$DB_PATH" 2>/dev/null || true

wait $PID 2>/dev/null || true

# Restore permissions
chmod 644 "$DB_PATH" 2>/dev/null || true

sleep 1

COUNT=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM failures WHERE title='$TEST_TITLE'" 2>/dev/null || echo "0")

if [ "$COUNT" -gt 0 ]; then
    echo "✓ PASS: Write succeeded despite permission change"
    echo "SEVERITY: N/A"
else
    echo "✗ FAIL: Write failed when permissions changed"
    echo "SEVERITY: MEDIUM"
    echo "SUGGESTION: Handle EPERM errors gracefully, add retry logic"
fi
echo ""

# =================================================================
# TEST 7: Large Summary (Disk Space Pressure)
# =================================================================
((TEST_NUM++))
echo "[$TEST_NUM] Testing: Large summary (100KB - disk space pressure)"
echo "-------------------------------------------------------------------"

LARGE_SUMMARY=$(printf 'A%.0s' {1..102400})  # 100KB
TEST_TITLE="EDGE_TEST_LARGE_$$"

export FAILURE_TITLE="$TEST_TITLE"
export FAILURE_DOMAIN="testing"
export FAILURE_SUMMARY="$LARGE_SUMMARY"
"$SCRIPTS_DIR/record-failure.sh" 2>/dev/null
EXIT_CODE=$?

sleep 1

COUNT=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM failures WHERE title='$TEST_TITLE'" 2>/dev/null || echo "0")

if [ "$COUNT" -gt 0 ]; then
    SUMMARY_LEN=$(sqlite3 "$DB_PATH" "SELECT LENGTH(summary) FROM failures WHERE title='$TEST_TITLE'" 2>/dev/null)
    echo "✓ PASS: Large summary handled (stored: $SUMMARY_LEN bytes)"
    if [ "$SUMMARY_LEN" -lt 102400 ]; then
        echo "  Note: Summary truncated from 102400 to $SUMMARY_LEN bytes"
        echo "  This may be intentional validation"
    fi
    echo "SEVERITY: N/A"
else
    echo "✗ FAIL: Failed to handle large summary (exit: $EXIT_CODE)"
    echo "SEVERITY: MEDIUM"
    echo "SUGGESTION: Add input size validation and limits"
fi
echo ""

# =================================================================
# TEST 8: Concurrent Schema Check
# =================================================================
((TEST_NUM++))
echo "[$TEST_NUM] Testing: Concurrent operations during schema check"
echo "-------------------------------------------------------------------"

TEST_TITLE="EDGE_TEST_SCHEMA_$$"

# Start 5 parallel writes
for i in {1..5}; do
    (
        export FAILURE_TITLE="${TEST_TITLE}_$i"
        export FAILURE_DOMAIN="testing"
        export FAILURE_SUMMARY="Schema race test $i"
        "$SCRIPTS_DIR/record-failure.sh" 2>/dev/null
    ) &
done

# Concurrent schema check
sqlite3 "$DB_PATH" "PRAGMA table_info(failures);" 2>/dev/null &

wait
sleep 2

# Check integrity
INTEGRITY=$(sqlite3 "$DB_PATH" "PRAGMA integrity_check;" 2>/dev/null)
if echo "$INTEGRITY" | grep -q "ok"; then
    echo "✓ PASS: Database integrity maintained during concurrent schema checks"
    echo "SEVERITY: N/A"
else
    echo "✗ FAIL: Database corruption during schema operations"
    echo "SEVERITY: CRITICAL"
fi

COUNT=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM failures WHERE title LIKE '${TEST_TITLE}_%'" 2>/dev/null || echo "0")
if [ "$COUNT" -eq 5 ]; then
    echo "✓ PASS: All 5 records created during concurrent schema check"
    echo "SEVERITY: N/A"
else
    echo "⚠ WARNING: Only $COUNT/5 records created"
    echo "SEVERITY: MEDIUM"
fi
echo ""

# =================================================================
# FINAL SUMMARY
# =================================================================
echo "==================================================================="
echo "EDGE CASE TESTING COMPLETE"
echo "==================================================================="
echo "Total tests run: $TEST_NUM"
echo ""
echo "Review the output above for specific failures and suggestions."
echo "Database integrity checks were performed throughout."
echo ""
echo "Key findings:"
echo "  - Rapid concurrent calls handling"
echo "  - Date consistency across midnight boundary"
echo "  - File descriptor pressure tolerance"
echo "  - Signal interruption recovery"
echo "  - Stale git lock handling"
echo "  - Permission race conditions"
echo "  - Large data handling"
echo "  - Schema concurrency safety"
echo "==================================================================="
