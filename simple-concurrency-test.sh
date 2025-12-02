#!/bin/bash
# Simple Concurrency Test - Tests query.py with concurrent reads

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$SCRIPT_DIR"
QUERY_PY="$BASE_DIR/query/query.py"

echo "=========================================="
echo "Simple Concurrency Test - Agent E"
echo "=========================================="
echo ""

NUM_READERS="${1:-20}"

echo "Test: $NUM_READERS concurrent readers"
echo ""

# Start time
start=$(date +%s.%N)

# Spawn concurrent readers
pids=()
for i in $(seq 1 $NUM_READERS); do
    python3 "$QUERY_PY" --recent 10 > "/tmp/reader-$i.log" 2>&1 &
    pids+=($!)
done

# Wait for all to complete
failed=0
for pid in "${pids[@]}"; do
    if ! wait $pid; then
        ((failed++))
    fi
done

# End time
end=$(date +%s.%N)
duration=$(awk "BEGIN {print $end - $start}")

echo "Results:"
echo "  Duration: ${duration}s"
echo "  Failed: $failed / $NUM_READERS"
echo "  Success Rate: $(awk "BEGIN {printf \"%.1f%%\", 100 * (1 - $failed / $NUM_READERS)}")"
echo ""

# Check database status
echo "Database Status:"
sqlite3 "$BASE_DIR/memory/index.db" "PRAGMA journal_mode;"
sqlite3 "$BASE_DIR/memory/index.db" "PRAGMA busy_timeout;" | head -1

echo ""
echo "Test Complete!"
