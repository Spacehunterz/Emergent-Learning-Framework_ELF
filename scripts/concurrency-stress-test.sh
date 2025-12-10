#!/bin/bash
# Concurrency Stress Test for Emergent Learning Framework
# Tests improvements made by Agent E

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$SCRIPT_DIR"
LOGS_DIR="$BASE_DIR/logs"
TEST_RESULTS_DIR="$BASE_DIR/test-results"
DB_PATH="$BASE_DIR/memory/index.db"

mkdir -p "$LOGS_DIR"
mkdir -p "$TEST_RESULTS_DIR"

TEST_LOG="$TEST_RESULTS_DIR/concurrency-test-$(date +%Y%m%d-%H%M%S).log"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$TEST_LOG"
}

log "=========================================="
log "CONCURRENCY STRESS TEST - Agent E"
log "=========================================="
log ""

# Test parameters
NUM_CONCURRENT_WRITERS="${1:-20}"
NUM_CONCURRENT_READERS="${2:-10}"

log "Test Parameters:"
log "  Concurrent Writers: $NUM_CONCURRENT_WRITERS"
log "  Concurrent Readers: $NUM_CONCURRENT_READERS"
log "  Log File: $TEST_LOG"
log ""

# Pre-test: Check database status
log "Pre-test Database Status:"
if [ -f "$DB_PATH" ]; then
    log "  Database exists: $DB_PATH"
    sqlite3 "$DB_PATH" "PRAGMA journal_mode;" | tee -a "$TEST_LOG"
    sqlite3 "$DB_PATH" "PRAGMA busy_timeout;" | tee -a "$TEST_LOG"
    log "  Total learnings: $(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM learnings")"
    log "  Total heuristics: $(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM heuristics")"
else
    log "  Database does not exist (will be created)"
fi
log ""

# Function to write a failure record (simulates concurrent writes)
write_failure_test() {
    local id=$1
    local start_time=$(date +%s.%N)

    FAILURE_TITLE="Concurrency Test Failure $id" \
    FAILURE_DOMAIN="testing" \
    FAILURE_SUMMARY="Testing concurrent writes - iteration $id" \
    FAILURE_SEVERITY="3" \
    FAILURE_TAGS="test,concurrency" \
    "$BASE_DIR/scripts/record-failure-v3.sh" >> "$TEST_RESULTS_DIR/writer-$id.log" 2>&1

    local exit_code=$?
    local end_time=$(date +%s.%N)
    local duration=$(awk "BEGIN {print $end_time - $start_time}")

    echo "$id,$exit_code,$duration" >> "$TEST_RESULTS_DIR/write-times.csv"

    if [ $exit_code -eq 0 ]; then
        echo "Writer $id: SUCCESS (${duration}s)" >> "$TEST_RESULTS_DIR/summary.txt"
    else
        echo "Writer $id: FAILED with code $exit_code (${duration}s)" >> "$TEST_RESULTS_DIR/summary.txt"
    fi

    return $exit_code
}

# Function to read from database (simulates concurrent reads)
read_test() {
    local id=$1
    local start_time=$(date +%s.%N)

    python3 "$BASE_DIR/query/query.py" --recent 10 --format json >> "$TEST_RESULTS_DIR/reader-$id.log" 2>&1

    local exit_code=$?
    local end_time=$(date +%s.%N)
    local duration=$(awk "BEGIN {print $end_time - $start_time}")

    echo "$id,$exit_code,$duration" >> "$TEST_RESULTS_DIR/read-times.csv"

    if [ $exit_code -eq 0 ]; then
        echo "Reader $id: SUCCESS (${duration}s)" >> "$TEST_RESULTS_DIR/summary.txt"
    else
        echo "Reader $id: FAILED with code $exit_code (${duration}s)" >> "$TEST_RESULTS_DIR/summary.txt"
    fi

    return $exit_code
}

# Clean up previous test results
rm -f "$TEST_RESULTS_DIR/write-times.csv"
rm -f "$TEST_RESULTS_DIR/read-times.csv"
rm -f "$TEST_RESULTS_DIR/summary.txt"
rm -f "$TEST_RESULTS_DIR/writer-"*.log
rm -f "$TEST_RESULTS_DIR/reader-"*.log

# Header for CSV files
echo "id,exit_code,duration" > "$TEST_RESULTS_DIR/write-times.csv"
echo "id,exit_code,duration" > "$TEST_RESULTS_DIR/read-times.csv"

log "=========================================="
log "TEST 1: Concurrent Writes Only"
log "=========================================="
log "Spawning $NUM_CONCURRENT_WRITERS concurrent writers..."
log ""

# Record start counts
learnings_before=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM learnings" 2>/dev/null || echo "0")

# Start time
test1_start=$(date +%s.%N)

# Spawn concurrent writers
pids=()
for i in $(seq 1 $NUM_CONCURRENT_WRITERS); do
    write_failure_test $i &
    pids+=($!)
done

# Wait for all writers to complete
log "Waiting for all writers to complete..."
failed_count=0
for pid in "${pids[@]}"; do
    if ! wait $pid; then
        ((failed_count++))
    fi
done

# End time
test1_end=$(date +%s.%N)
test1_duration=$(awk "BEGIN {print $test1_end - $test1_start}")

log ""
log "Test 1 Complete:"
log "  Duration: ${test1_duration}s"
log "  Failed Writers: $failed_count / $NUM_CONCURRENT_WRITERS"

# Verify database consistency
learnings_after=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM learnings")
learnings_added=$((learnings_after - learnings_before))
expected_additions=$((NUM_CONCURRENT_WRITERS - failed_count))

log "  Learnings Before: $learnings_before"
log "  Learnings After: $learnings_after"
log "  Learnings Added: $learnings_added"
log "  Expected: $expected_additions"

if [ $learnings_added -eq $expected_additions ]; then
    log "  ✓ DATABASE CONSISTENCY: PASS"
else
    log "  ✗ DATABASE CONSISTENCY: FAIL (data loss or corruption)"
fi
log ""

# Calculate statistics for Test 1
if [ -f "$TEST_RESULTS_DIR/write-times.csv" ]; then
    avg_write_time=$(awk -F, 'NR>1 {sum+=$3; count++} END {if (count>0) print sum/count; else print 0}' "$TEST_RESULTS_DIR/write-times.csv")
    max_write_time=$(awk -F, 'NR>1 {if ($3>max) max=$3} END {print max+0}' "$TEST_RESULTS_DIR/write-times.csv")
    min_write_time=$(awk -F, 'NR>1 {if (min=="" || $3<min) min=$3} END {print min+0}' "$TEST_RESULTS_DIR/write-times.csv")

    log "Write Performance:"
    log "  Average: ${avg_write_time}s"
    log "  Min: ${min_write_time}s"
    log "  Max: ${max_write_time}s"
fi
log ""

log "=========================================="
log "TEST 2: Concurrent Reads During Writes"
log "=========================================="
log "Spawning $NUM_CONCURRENT_WRITERS writers + $NUM_CONCURRENT_READERS readers..."
log ""

test2_start=$(date +%s.%N)

# Spawn concurrent writers
writer_pids=()
for i in $(seq 1 $NUM_CONCURRENT_WRITERS); do
    write_failure_test $((NUM_CONCURRENT_WRITERS + i)) &
    writer_pids+=($!)
done

# Spawn concurrent readers (slight delay to ensure writers are active)
sleep 0.5
reader_pids=()
for i in $(seq 1 $NUM_CONCURRENT_READERS); do
    read_test $i &
    reader_pids+=($!)
done

# Wait for all to complete
log "Waiting for all operations to complete..."
writer_failed=0
reader_failed=0

for pid in "${writer_pids[@]}"; do
    if ! wait $pid; then
        ((writer_failed++))
    fi
done

for pid in "${reader_pids[@]}"; do
    if ! wait $pid; then
        ((reader_failed++))
    fi
done

test2_end=$(date +%s.%N)
test2_duration=$(awk "BEGIN {print $test2_end - $test2_start}")

log ""
log "Test 2 Complete:"
log "  Duration: ${test2_duration}s"
log "  Failed Writers: $writer_failed / $NUM_CONCURRENT_WRITERS"
log "  Failed Readers: $reader_failed / $NUM_CONCURRENT_READERS"

# Calculate read statistics
if [ -f "$TEST_RESULTS_DIR/read-times.csv" ]; then
    avg_read_time=$(awk -F, 'NR>1 {sum+=$3; count++} END {if (count>0) print sum/count; else print 0}' "$TEST_RESULTS_DIR/read-times.csv")
    max_read_time=$(awk -F, 'NR>1 {if ($3>max) max=$3} END {print max+0}' "$TEST_RESULTS_DIR/read-times.csv")
    min_read_time=$(awk -F, 'NR>1 {if (min=="" || $3<min) min=$3} END {print min+0}' "$TEST_RESULTS_DIR/read-times.csv")

    log ""
    log "Read Performance:"
    log "  Average: ${avg_read_time}s"
    log "  Min: ${min_read_time}s"
    log "  Max: ${max_read_time}s"
fi
log ""

log "=========================================="
log "TEST 3: Stale Lock Detection"
log "=========================================="
log "Creating artificial stale lock..."

LOCK_DIR="$BASE_DIR/.git/claude-lock.dir"
mkdir -p "$LOCK_DIR"
log "  Created stale lock: $LOCK_DIR"

# Make it old (use touch to set timestamp to 10 minutes ago)
touch -t $(date -d '10 minutes ago' +%Y%m%d%H%M 2>/dev/null || date -v-10M +%Y%m%d%H%M) "$LOCK_DIR" 2>/dev/null || true

log "  Testing if stale lock is cleaned..."

# Try to acquire lock (should clean stale lock and succeed)
test3_start=$(date +%s.%N)

write_failure_test 9999 >> "$TEST_RESULTS_DIR/stale-lock-test.log" 2>&1
stale_test_exit=$?

test3_end=$(date +%s.%N)
test3_duration=$(awk "BEGIN {print $test3_end - $test3_start}")

if [ $stale_test_exit -eq 0 ]; then
    log "  ✓ STALE LOCK CLEANUP: PASS (${test3_duration}s)"
else
    log "  ✗ STALE LOCK CLEANUP: FAIL (${test3_duration}s)"
fi
log ""

log "=========================================="
log "TEST 4: Database Integrity Check"
log "=========================================="

# Run SQLite integrity check
integrity_result=$(sqlite3 "$DB_PATH" "PRAGMA integrity_check;" 2>&1)
if echo "$integrity_result" | grep -q "ok"; then
    log "  ✓ DATABASE INTEGRITY: PASS"
else
    log "  ✗ DATABASE INTEGRITY: FAIL"
    log "  Result: $integrity_result"
fi

# Check for orphaned files/records
log ""
log "Checking for orphaned files/records..."
"$BASE_DIR/scripts/sync-db-markdown.sh" >> "$TEST_RESULTS_DIR/sync-check.log" 2>&1
orphaned_count=$(grep -c "ORPHANED" "$TEST_RESULTS_DIR/sync-check.log" || echo "0")

log "  Orphaned items found: $orphaned_count"
if [ "$orphaned_count" -eq 0 ]; then
    log "  ✓ FILE/DB SYNC: PASS"
else
    log "  ⚠ FILE/DB SYNC: Issues found (see sync-check.log)"
fi
log ""

log "=========================================="
log "FINAL RESULTS"
log "=========================================="
log ""
log "Overall Statistics:"
log "  Total Operations: $((NUM_CONCURRENT_WRITERS * 2 + NUM_CONCURRENT_READERS))"
log "  Total Failures: $((failed_count + writer_failed + reader_failed))"
log "  Success Rate: $(awk "BEGIN {printf \"%.2f%%\", 100 * (1 - ($failed_count + $writer_failed + $reader_failed) / ($NUM_CONCURRENT_WRITERS * 2 + $NUM_CONCURRENT_READERS))}")"
log ""
log "Performance Summary:"
log "  Test 1 (Writes Only): ${test1_duration}s"
log "  Test 2 (Mixed R/W): ${test2_duration}s"
log "  Test 3 (Stale Lock): ${test3_duration}s"
log ""

# Final database state
log "Final Database State:"
log "  Total Learnings: $(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM learnings")"
log "  Total Heuristics: $(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM heuristics")"
log "  Journal Mode: $(sqlite3 "$DB_PATH" "PRAGMA journal_mode;")"
log "  Busy Timeout: $(sqlite3 "$DB_PATH" "PRAGMA busy_timeout;")"
log ""

log "=========================================="
log "Test Complete!"
log "Full results: $TEST_RESULTS_DIR/"
log "=========================================="
