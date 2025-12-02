#!/bin/bash
# Verify that time-based fixes were applied correctly

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$SCRIPT_DIR"

echo "========================================="
echo "VERIFYING TIME-BASED FIXES"
echo "========================================="
echo ""

PASS=0
FAIL=0

test_check() {
    local test_name="$1"
    local file="$2"
    local pattern="$3"

    echo -n "  Testing: $test_name ... "

    if grep -q "$pattern" "$file"; then
        echo "PASS"
        PASS=$((PASS + 1))
    else
        echo "FAIL"
        FAIL=$((FAIL + 1))
    fi
}

echo "VERIFICATION 1: EXECUTION_DATE variable captured"
test_check "record-failure.sh has EXECUTION_DATE" \
    "$BASE_DIR/scripts/record-failure.sh" \
    "EXECUTION_DATE=\$(date +%Y%m%d)"

test_check "record-heuristic.sh has EXECUTION_DATE" \
    "$BASE_DIR/scripts/record-heuristic.sh" \
    "EXECUTION_DATE=\$(date +%Y%m%d)"

echo ""
echo "VERIFICATION 2: LOG_FILE uses EXECUTION_DATE (not inline date)"
test_check "record-failure.sh LOG_FILE" \
    "$BASE_DIR/scripts/record-failure.sh" \
    'LOG_FILE=.*\${EXECUTION_DATE}'

test_check "record-heuristic.sh LOG_FILE" \
    "$BASE_DIR/scripts/record-heuristic.sh" \
    'LOG_FILE=.*\${EXECUTION_DATE}'

echo ""
echo "VERIFICATION 3: date_prefix uses EXECUTION_DATE"
test_check "record-failure.sh date_prefix" \
    "$BASE_DIR/scripts/record-failure.sh" \
    'date_prefix=\$EXECUTION_DATE'

echo ""
echo "VERIFICATION 4: Markdown dates use EXECUTION_DATE"
test_check "record-failure.sh markdown date" \
    "$BASE_DIR/scripts/record-failure.sh" \
    '\*\*Date\*\*:.*EXECUTION_DATE'

test_check "record-heuristic.sh markdown date" \
    "$BASE_DIR/scripts/record-heuristic.sh" \
    '\*\*Created\*\*:.*EXECUTION_DATE'

echo ""
echo "VERIFICATION 5: Timestamp validation function exists"
test_check "validate_timestamp function in record-failure.sh" \
    "$BASE_DIR/scripts/record-failure.sh" \
    'validate_timestamp()'

test_check "validate_timestamp function in record-heuristic.sh" \
    "$BASE_DIR/scripts/record-heuristic.sh" \
    'validate_timestamp()'

echo ""
echo "VERIFICATION 6: Timestamp validation called in preflight"
test_check "record-failure.sh calls validate_timestamp" \
    "$BASE_DIR/scripts/record-failure.sh" \
    'if ! validate_timestamp; then'

test_check "record-heuristic.sh calls validate_timestamp" \
    "$BASE_DIR/scripts/record-heuristic.sh" \
    'if ! validate_timestamp; then'

echo ""
echo "VERIFICATION 7: No inline date calculations remain (except EXECUTION_DATE)"
echo -n "  Checking record-failure.sh ... "
INLINE_DATES=$(grep -c '\$(date +%Y%m%d)' "$BASE_DIR/scripts/record-failure.sh" || true)
if [ "$INLINE_DATES" -eq 1 ]; then
    echo "PASS (only 1 for EXECUTION_DATE)"
    PASS=$((PASS + 1))
else
    echo "FAIL (found $INLINE_DATES, expected 1)"
    FAIL=$((FAIL + 1))
fi

echo -n "  Checking record-heuristic.sh ... "
INLINE_DATES=$(grep -c '\$(date +%Y%m%d)' "$BASE_DIR/scripts/record-heuristic.sh" || true)
if [ "$INLINE_DATES" -eq 1 ]; then
    echo "PASS (only 1 for EXECUTION_DATE)"
    PASS=$((PASS + 1))
else
    echo "FAIL (found $INLINE_DATES, expected 1)"
    FAIL=$((FAIL + 1))
fi

echo ""
echo "VERIFICATION 8: Documentation added"
test_check "query.py has timezone documentation" \
    "$BASE_DIR/query/query.py" \
    'TIME-FIX-6:'

echo ""
echo "========================================="
echo "VERIFICATION SUMMARY"
echo "========================================="
echo "Passed: $PASS"
echo "Failed: $FAIL"
echo ""

if [ $FAIL -eq 0 ]; then
    echo "RESULT: ALL VERIFICATIONS PASSED"
    exit 0
else
    echo "RESULT: SOME VERIFICATIONS FAILED"
    exit 1
fi
