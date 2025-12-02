#!/bin/bash
# Stress test: 10 concurrent record-failure.sh calls

TEST_DIR="$PWD/test-run"
RESULTS_FILE="$TEST_DIR/stress-test-results.txt"
FAILURES_LOG="$TEST_DIR/failures.log"

# Clear previous results
> "$RESULTS_FILE"
> "$FAILURES_LOG"

echo "Starting stress test with 10 concurrent record-failure.sh calls..."
echo "Test started at: $(date)" >> "$RESULTS_FILE"
echo "" >> "$RESULTS_FILE"

SUCCESS_COUNT=0
FAIL_COUNT=0
PIDS=()

# Launch 10 concurrent processes
for i in {1..10}; do
    echo "Launching concurrent call $i..."
    (
        FAILURE_TITLE="Stress Test Failure $i" \
        FAILURE_DOMAIN="testing" \
        FAILURE_SUMMARY="Concurrent stress test run #$i" \
        FAILURE_SEVERITY="3" \
        timeout 60 ~/.claude/emergent-learning/scripts/record-failure.sh \
        >> "$FAILURES_LOG" 2>&1
        
        if [ $? -eq 0 ]; then
            echo "[SUCCESS] Process $i completed" >> "$RESULTS_FILE"
            exit 0
        else
            echo "[FAILURE] Process $i failed" >> "$RESULTS_FILE"
            exit 1
        fi
    ) &
    PIDS+=($!)
done

echo "Waiting for all processes to complete..."
echo "" >> "$RESULTS_FILE"

# Wait for all background jobs and count results
for i in "${!PIDS[@]}"; do
    pid=${PIDS[$i]}
    wait $pid
    if [ $? -eq 0 ]; then
        ((SUCCESS_COUNT++))
    else
        ((FAIL_COUNT++))
    fi
done

echo "Test completed at: $(date)" >> "$RESULTS_FILE"
echo "" >> "$RESULTS_FILE"
echo "Results Summary:" >> "$RESULTS_FILE"
echo "===============" >> "$RESULTS_FILE"
echo "Total Processes: 10" >> "$RESULTS_FILE"
echo "Successful: $SUCCESS_COUNT" >> "$RESULTS_FILE"
echo "Failed: $FAIL_COUNT" >> "$RESULTS_FILE"
echo "Success Rate: $((SUCCESS_COUNT * 100 / 10))%" >> "$RESULTS_FILE"
echo "" >> "$RESULTS_FILE"

# Display results
cat "$RESULTS_FILE"
