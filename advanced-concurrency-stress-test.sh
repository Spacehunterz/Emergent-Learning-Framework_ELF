#!/bin/bash
# Advanced Concurrency Stress Test - 50+ parallel operations

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$SCRIPT_DIR"
TEST_RESULTS_DIR="$BASE_DIR/test-results/stress-$(date +%Y%m%d-%H%M%S)"

mkdir -p "$TEST_RESULTS_DIR"

log() {
    echo "[$(date '+%H:%M:%S')] $*" | tee -a "$TEST_RESULTS_DIR/test.log"
}

log "========================================"
log "ADVANCED CONCURRENCY STRESS TEST"
log "Target: 50+ parallel operations"  
log "Goal: 99%+ success rate"
log "========================================"

NUM_WRITERS="${1:-30}"
NUM_READERS="${2:-25}"
TOTAL_OPS=$((NUM_WRITERS + NUM_READERS))

log "Configuration: Writers=$NUM_WRITERS, Readers=$NUM_READERS, Total=$TOTAL_OPS"

write_test() {
    local id=$1
    local start=$(date +%s.%N)
    FAILURE_TITLE="Stress Test $id" FAILURE_DOMAIN="stress" FAILURE_SUMMARY="Test $id" FAILURE_SEVERITY="2" \
        "$BASE_DIR/scripts/record-failure.sh" >> "$TEST_RESULTS_DIR/writer-$id.log" 2>&1
    local exit_code=$?
    local dur=$(awk "BEGIN {print $(date +%s.%N) - $start}")
    echo "$id,$exit_code,$dur" >> "$TEST_RESULTS_DIR/write-results.csv"
    return $exit_code
}

read_test() {
    local id=$1
    local start=$(date +%s.%N)
    python3 "$BASE_DIR/query/query.py" --recent 5 >> "$TEST_RESULTS_DIR/reader-$id.log" 2>&1
    local exit_code=$?
    local dur=$(awk "BEGIN {print $(date +%s.%N) - $start}")
    echo "$id,$exit_code,$dur" >> "$TEST_RESULTS_DIR/read-results.csv"
    return $exit_code
}

echo "id,exit_code,duration" > "$TEST_RESULTS_DIR/write-results.csv"
echo "id,exit_code,duration" > "$TEST_RESULTS_DIR/read-results.csv"

log "TEST 1: Maximum Concurrency - Launching $TOTAL_OPS operations..."
test1_start=$(date +%s.%N)
pids=()

for i in $(seq 1 $NUM_WRITERS); do
    write_test $i &
    pids+=($!)
done

sleep 0.2

for i in $(seq 1 $NUM_READERS); do
    read_test $i &
    pids+=($!)
done

failed=0
for pid in "${pids[@]}"; do
    wait $pid || ((failed++))
done

test1_dur=$(awk "BEGIN {print $(date +%s.%N) - $test1_start}")
success_rate=$(awk "BEGIN {printf \"%.2f\", 100 * (1 - $failed / $TOTAL_OPS)}")

log "Test 1 Results: Duration=${test1_dur}s, Failed=$failed/$TOTAL_OPS, Success=${success_rate}%"

log "TEST 2: Stale Lock Detection"
LOCK_DIR="$BASE_DIR/.git/claude-lock.dir"
mkdir -p "$LOCK_DIR"
echo "99999" > "$LOCK_DIR/pid"
log "Created fake stale lock with non-existent PID"

write_test 9998 >> "$TEST_RESULTS_DIR/stale-test.log" 2>&1
if [ $? -eq 0 ]; then
    log "[PASS] Stale lock cleanup successful"
else
    log "[FAIL] Stale lock cleanup failed"
    ((failed++))
fi

log "TEST 3: Thundering Herd (20 rapid operations)"
BURST=20
burst_pids=()
for i in $(seq 1 $BURST); do
    write_test $((10000 + i)) &
    burst_pids+=($!)
done

burst_failed=0
for pid in "${burst_pids[@]}"; do
    wait $pid || ((burst_failed++))
done

log "Test 3 Results: Failed=$burst_failed/$BURST, Success=$(awk "BEGIN {printf \"%.1f\", 100*(1-$burst_failed/$BURST)}")%"

log "TEST 4: Database Integrity"
DB_PATH="$BASE_DIR/memory/index.db"
integrity=$(sqlite3 "$DB_PATH" "PRAGMA integrity_check;" 2>&1)
if echo "$integrity" | grep -q "ok"; then
    log "[PASS] Database integrity check"
else
    log "[FAIL] Database integrity check"
fi

total_failed=$((failed + burst_failed))
total_ops_run=$((TOTAL_OPS + BURST + 1))
overall_rate=$(awk "BEGIN {printf \"%.2f\", 100 * (1 - $total_failed / $total_ops_run)}")

log "========================================"
log "FINAL VERDICT"
log "Total Operations: $total_ops_run"
log "Total Failures: $total_failed"
log "Overall Success Rate: ${overall_rate}%"

if (( $(awk "BEGIN {print ($overall_rate >= 99)}") )); then
    log "SUCCESS: 99%+ achieved!"
    log "10/10 CONCURRENCY ACHIEVED!"
    exit 0
else
    log "Target not met: Need 99%+, got ${overall_rate}%"
    exit 1
fi
