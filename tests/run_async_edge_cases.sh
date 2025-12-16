#!/bin/bash
# Run all async QuerySystem edge case tests
cd "$(dirname "$0")/.."
export PYTHONPATH=.

echo "Running async edge case tests..."
echo ""

echo "=== test_edge_cases_v2.py ==="
python tests/test_edge_cases_v2.py 2>&1 | tail -15

echo ""
echo "=== test_edge_cases.py ==="
python tests/test_edge_cases.py 2>&1 | tail -10

echo ""
echo "=== test_destructive_edge_cases.py ==="
python tests/test_destructive_edge_cases.py 2>&1 | tail -15
