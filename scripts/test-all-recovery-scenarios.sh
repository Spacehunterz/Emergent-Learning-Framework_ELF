#!/bin/bash
# Test All Recovery Scenarios
# This script orchestrates a full suite of recovery tests.

echo "=== Starting Full Recovery Test Suite ==="

# 1. Simple Recovery Test
./tools/scripts/test-recovery-simple.sh
if [ $? -ne 0 ]; then
    echo "Check 1 Failed."
    exit 1
fi

echo "=== All Recovery Scenarios Passed ==="
exit 0
