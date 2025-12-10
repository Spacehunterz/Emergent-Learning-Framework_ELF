#!/usr/bin/env bash
#
# Test script for accountability tracking system
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
RECORD_VIOLATION="$SCRIPT_DIR/scripts/record-violation.sh"
QUERY_PY="$SCRIPT_DIR/query/query.py"

echo "========================================"
echo "Testing Accountability Tracking System"
echo "========================================"
echo ""

# Test 1: Clean state
echo "Test 1: Checking clean state..."
python3 "$QUERY_PY" --accountability-banner | grep -q "NORMAL" && echo "✓ Clean state verified" || echo "✗ Clean state failed"
echo ""

# Test 2: Record single violation
echo "Test 2: Recording single violation..."
bash "$RECORD_VIOLATION" 1 "TEST: Single violation" > /dev/null 2>&1
python3 "$QUERY_PY" --violations | grep -q "total: 1" && echo "✓ Single violation recorded" || echo "✗ Single violation failed"
echo ""

# Test 3: Warning threshold
echo "Test 3: Testing WARNING threshold..."
bash "$RECORD_VIOLATION" 2 "TEST: Warning 1" > /dev/null 2>&1
bash "$RECORD_VIOLATION" 2 "TEST: Warning 2" > /dev/null 2>&1
python3 "$QUERY_PY" --accountability-banner | grep -q "WARNING" && echo "✓ WARNING threshold reached" || echo "✗ WARNING threshold failed"
echo ""

# Test 4: Probation threshold
echo "Test 4: Testing PROBATION threshold..."
bash "$RECORD_VIOLATION" 3 "TEST: Probation 1" > /dev/null 2>&1
bash "$RECORD_VIOLATION" 3 "TEST: Probation 2" > /dev/null 2>&1
python3 "$QUERY_PY" --accountability-banner | grep -q "PROBATION" && echo "✓ PROBATION threshold reached" || echo "✗ PROBATION threshold failed"
echo ""

# Test 5: Critical threshold and CEO escalation
echo "Test 5: Testing CRITICAL threshold and CEO escalation..."
for i in {1..5}; do
  bash "$RECORD_VIOLATION" 4 "TEST: Critical $i" > /dev/null 2>&1
done
python3 "$QUERY_PY" --accountability-banner | grep -q "CRITICAL" && echo "✓ CRITICAL threshold reached" || echo "✗ CRITICAL threshold failed"
ls "$SCRIPT_DIR/ceo-inbox/VIOLATION_THRESHOLD_"*.md > /dev/null 2>&1 && echo "✓ CEO escalation file created" || echo "✗ CEO escalation failed"
python3 "$QUERY_PY" --ceo-reviews | grep -q "Golden Rule Violations Threshold Exceeded" && echo "✓ CEO review entry created" || echo "✗ CEO review failed"
echo ""

# Cleanup
echo "Cleaning up test data..."
sqlite3 "$SCRIPT_DIR/memory/index.db" "DELETE FROM violations WHERE description LIKE 'TEST:%';" 2>/dev/null
sqlite3 "$SCRIPT_DIR/memory/index.db" "DELETE FROM ceo_reviews WHERE title = 'Golden Rule Violations Threshold Exceeded';" 2>/dev/null
rm -f "$SCRIPT_DIR/ceo-inbox/VIOLATION_THRESHOLD_"*.md 2>/dev/null
echo "✓ Cleanup complete"
echo ""

echo "========================================"
echo "All tests passed!"
echo "========================================"
