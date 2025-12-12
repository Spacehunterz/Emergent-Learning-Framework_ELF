#!/bin/bash
# Quick runner for ELF stress tests
#
# Usage:
#   ./run_stress_test.sh              # Run all tests
#   ./run_stress_test.sh --quick      # Run quick tests only (skip 30s resource test)
#   ./run_stress_test.sh --verbose    # Show all warnings
#   ./run_stress_test.sh --save       # Save output to timestamped file

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Default: suppress warnings
REDIRECT="2>/dev/null"
SAVE_OUTPUT=false
QUICK=false

# Parse arguments
for arg in "$@"; do
    case $arg in
        --verbose)
            REDIRECT=""
            ;;
        --save)
            SAVE_OUTPUT=true
            ;;
        --quick)
            QUICK=true
            ;;
        *)
            echo "Unknown option: $arg"
            echo "Usage: $0 [--verbose] [--save] [--quick]"
            exit 1
            ;;
    esac
done

# Run tests
if [ "$SAVE_OUTPUT" = true ]; then
    TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
    OUTPUT_FILE="stress_test_${TIMESTAMP}.log"
    echo "Running stress tests... (saving to $OUTPUT_FILE)"

    if [ "$QUICK" = true ]; then
        python test_stress.py --quick 2>&1 | tee "$OUTPUT_FILE"
    else
        python test_stress.py 2>&1 | tee "$OUTPUT_FILE"
    fi

    echo ""
    echo "Full output saved to: $OUTPUT_FILE"
else
    echo "Running ELF Coordination System Stress Tests..."
    echo "=============================================="
    echo ""

    if [ -z "$REDIRECT" ]; then
        python test_stress.py
    else
        # Suppress warnings, show summary
        python test_stress.py 2>/dev/null | grep -E "Running:|PASS|FAIL|Duration|Throughput|Errors|Total Tests|Success Rate"
    fi
fi

echo ""
echo "For detailed report, see: ~/Desktop/stress_test_report.md"
