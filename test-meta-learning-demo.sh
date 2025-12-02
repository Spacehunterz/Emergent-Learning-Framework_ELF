#!/bin/bash
# Meta-Learning Capabilities Demonstration
# Runs all meta-learning tools to show system self-awareness

echo "========================================="
echo "META-LEARNING CAPABILITIES DEMONSTRATION"
echo "========================================="
echo ""
echo "The Emergent Learning Framework can now learn about itself."
echo ""

BASE_DIR="$HOME/.claude/emergent-learning"

echo "=== 1. SELF-DIAGNOSTICS ==="
echo "Testing system health..."
echo ""
$BASE_DIR/scripts/self-test.sh 2>&1 | grep -E "PASS|FAIL|WARN|Overall Status" | head -20
echo ""

echo "=== 2. LEARNING VELOCITY METRICS ==="
echo "How fast is the system learning?"
echo ""
$BASE_DIR/scripts/learning-metrics.sh 2>&1 | grep -A 15 "Overall Statistics"
echo ""

echo "=== 3. DEPENDENCY VALIDATION ==="
echo "Checking for circular dependencies..."
echo ""
$BASE_DIR/scripts/dependency-check.sh 2>&1 | grep -E "✓|✗|Dependency Check Summary" | head -15
echo ""

echo "=== 4. DEDUPLICATION ANALYSIS ==="
echo "Checking for duplicate failures..."
echo ""
$BASE_DIR/scripts/deduplicate-failures.sh --stats 2>&1 | grep -A 10 "Deduplication Statistics"
echo ""

echo "=== 5. HEURISTIC SUGGESTIONS ==="
echo "What heuristics should we extract?"
echo ""
$BASE_DIR/scripts/suggest-heuristics.sh --stats 2>&1 | grep -A 10 "Heuristic Generation Statistics"
echo ""

echo "========================================="
echo "DEMONSTRATION COMPLETE"
echo "========================================="
echo ""
echo "The system has demonstrated:"
echo "  ✓ Self-diagnostics capability"
echo "  ✓ Learning velocity tracking"
echo "  ✓ Dependency awareness"
echo "  ✓ Deduplication detection"
echo "  ✓ Heuristic auto-suggestion"
echo ""
echo "The building can now improve itself."
echo ""

