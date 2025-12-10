#!/bin/bash
# Test resource exhaustion scenarios

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$SCRIPT_DIR"
DB_PATH="$BASE_DIR/memory/index.db"

echo "========================================="
echo "RESOURCE EXHAUSTION TESTS"
echo "========================================="
echo ""

# TEST 1: File handle exhaustion
echo "TEST 1: File Handle Limits"
echo "--------------------------"

ulimit -n 2>/dev/null || echo "Cannot check ulimit on Windows"

# Launch 50 processes simultaneously
echo "Launching 50 concurrent processes..."
pids=()
for i in {1..50}; do
    bash "$BASE_DIR/scripts/record-failure.sh" \
        --title "Handles_$i" \
        --domain "resource-test" \
        --summary "Testing file handles" \
        --severity 2 \
        > "/tmp/handles_$i.log" 2>&1 &
    pids+=($!)
done

echo "Waiting for completion..."
failures=0
for pid in "${pids[@]}"; do
    if ! wait $pid; then
        ((failures++))
    fi
done

sleep 2

count=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM learnings WHERE title LIKE 'Handles_%';")
echo "Launched: 50"
echo "Succeeded: $count"
echo "Failed: $failures script errors"
echo ""

# Check for specific errors
too_many=$(grep -h "Too many open files" /tmp/handles_*.log 2>/dev/null | wc -l)
if [ $too_many -gt 0 ]; then
    echo "✗ CRITICAL: 'Too many open files' errors: $too_many"
else
    echo "✓ No file handle exhaustion"
fi

echo ""

# TEST 2: Rapid successive writes (timing)
echo "TEST 2: Rapid Successive Operations"
echo "------------------------------------"

echo "Testing lock release timing..."

# Write 1
start1=$(date +%s%N)
bash "$BASE_DIR/scripts/record-failure.sh" \
    --title "Timing_1" \
    --domain "resource-test" \
    --summary "First write" \
    --severity 2 \
    > /tmp/timing_1.log 2>&1
end1=$(date +%s%N)
duration1=$(( (end1 - start1) / 1000000 ))

# Write 2 (immediately after)
start2=$(date +%s%N)
bash "$BASE_DIR/scripts/record-failure.sh" \
    --title "Timing_2" \
    --domain "resource-test" \
    --summary "Second write" \
    --severity 2 \
    > /tmp/timing_2.log 2>&1
end2=$(date +%s%N)
duration2=$(( (end2 - start2) / 1000000 ))

echo "First write: ${duration1}ms"
echo "Second write: ${duration2}ms"

if [ $duration2 -gt $((duration1 * 3)) ]; then
    echo "⚠ WARNING: Second write took 3x longer (lock delay?)"
else
    echo "✓ Lock release timing OK"
fi

echo ""

# TEST 3: Memory usage
echo "TEST 3: Memory Usage"
echo "--------------------"

# Check database size
db_size=$(ls -lh "$DB_PATH" | awk '{print $5}')
echo "Database size: $db_size"

# Check for WAL files
if [ -f "$DB_PATH-wal" ]; then
    wal_size=$(ls -lh "$DB_PATH-wal" | awk '{print $5}')
    echo "WAL file size: $wal_size"
else
    echo "No WAL file (not using WAL mode)"
fi

echo ""

# TEST 4: Database lock modes
echo "TEST 4: SQLite Locking Modes"
echo "-----------------------------"

# Check current journal mode
journal_mode=$(sqlite3 "$DB_PATH" "PRAGMA journal_mode;")
echo "Journal mode: $journal_mode"

# Check current synchronous mode
sync_mode=$(sqlite3 "$DB_PATH" "PRAGMA synchronous;")
echo "Synchronous: $sync_mode"

# Check current timeout
timeout=$(sqlite3 "$DB_PATH" "PRAGMA busy_timeout;")
echo "Busy timeout: ${timeout}ms"

echo ""

if [ "$journal_mode" != "wal" ]; then
    echo "RECOMMENDATION: Enable WAL mode for better concurrency"
    echo "  sqlite3 \$DB_PATH 'PRAGMA journal_mode=WAL;'"
fi

echo ""

# TEST 5: Concurrent queries during writes
echo "TEST 5: Read/Write Concurrency"
echo "-------------------------------"

# Start writes in background
for i in {1..10}; do
    bash "$BASE_DIR/scripts/record-failure.sh" \
        --title "RW_Concurrent_$i" \
        --domain "resource-test" \
        --summary "RW test $i" \
        --severity 2 \
        > "/tmp/rw_write_$i.log" 2>&1 &
done

# Attempt reads while writing
read_success=0
read_failures=0

for i in {1..50}; do
    if sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM learnings;" > /dev/null 2>&1; then
        ((read_success++))
    else
        ((read_failures++))
    fi
    sleep 0.05
done

wait

echo "Read attempts: 50"
echo "Read success: $read_success"
echo "Read failures: $read_failures"

if [ $read_failures -gt 10 ]; then
    echo "⚠ WARNING: High read failure rate during writes"
else
    echo "✓ Reads mostly succeeded during writes"
fi

echo ""

# CLEANUP
echo "Cleaning up test data..."
sqlite3 "$DB_PATH" "DELETE FROM learnings WHERE domain = 'resource-test';" 2>/dev/null
rm -f /tmp/handles_*.log /tmp/timing_*.log /tmp/rw_*.log

echo ""
echo "========================================="
echo "RESOURCE EXHAUSTION SUMMARY"
echo "========================================="
echo ""

echo "Findings:"
echo "1. Maximum concurrent processes tested: 50"
echo "2. Journal mode: $journal_mode (WAL recommended)"
echo "3. Read/write concurrency: $read_success/50 reads succeeded"
echo ""

echo "For 10/10 error handling, implement:"
echo "1. Enable SQLite WAL mode for better concurrency"
echo "2. Monitor file handle usage"
echo "3. Implement connection pooling if needed"
echo "4. Add retry backoff with exponential delay"
echo "5. Set appropriate busy_timeout (currently ${timeout}ms)"
