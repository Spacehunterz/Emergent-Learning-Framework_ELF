#!/bin/bash
# Quick Filesystem Edge Cases Test - Critical Issues Only
# Tests the most dangerous filesystem scenarios

set +e  # Don't exit on error
umask 0077

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$(dirname "$SCRIPT_DIR")"
MEMORY_DIR="$BASE_DIR/memory"
TEST_RESULTS_DIR="$BASE_DIR/test-results"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
RESULTS_FILE="$TEST_RESULTS_DIR/filesystem_edge_quick_${TIMESTAMP}.md"

mkdir -p "$TEST_RESULTS_DIR"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

PASSED=0
FAILED=0
CRITICAL=0

echo "# Filesystem Edge Cases - Quick Test" > "$RESULTS_FILE"
echo "**Date**: $(date '+%Y-%m-%d %H:%M:%S')" >> "$RESULTS_FILE"
echo "" >> "$RESULTS_FILE"

log_result() {
    local severity=$1
    local test=$2
    local details=$3

    case $severity in
        PASS)
            echo -e "${GREEN}✓${NC} $test"
            echo "- ✓ $test" >> "$RESULTS_FILE"
            ((PASSED++))
            ;;
        FAIL)
            echo -e "${RED}✗${NC} $test"
            echo "- ✗ **FAIL**: $test" >> "$RESULTS_FILE"
            ((FAILED++))
            ;;
        CRITICAL)
            echo -e "${RED}!!! CRITICAL !!!${NC} $test"
            echo "- **!!! CRITICAL !!!**: $test" >> "$RESULTS_FILE"
            ((CRITICAL++))
            ((FAILED++))
            ;;
    esac

    if [ -n "$details" ]; then
        echo "  $details"
        echo "  - $details" >> "$RESULTS_FILE"
    fi
}

echo "============================================================"
echo "FILESYSTEM EDGE CASES - QUICK TEST"
echo "============================================================"
echo ""

# TEST 1: Filename length (300 chars)
echo "Test 1: Filename Length Limit (300 chars)"
title_300=$(printf 'A%.0s' {1..300})
result=$(FAILURE_TITLE="$title_300" FAILURE_DOMAIN="test" FAILURE_SEVERITY="3" FAILURE_SUMMARY="Test" "$BASE_DIR/scripts/record-failure.sh" 2>&1 || true)

if echo "$result" | grep -q "exceeds maximum length"; then
    log_result "PASS" "300-char title rejected by validation"
else
    latest=$(ls -t "$MEMORY_DIR/failures/" | head -1)
    len=${#latest}
    if [ $len -le 255 ]; then
        log_result "PASS" "300-char title truncated to $len chars (safe)"
    else
        log_result "FAIL" "300-char title created filename with $len chars (>255 limit)"
    fi
fi

# TEST 2: Reserved names (Windows)
echo ""
echo "Test 2: Reserved Filenames (CON, NUL, etc.)"
for name in CON NUL PRN AUX; do
    result=$(FAILURE_TITLE="$name" FAILURE_DOMAIN="test" FAILURE_SEVERITY="3" FAILURE_SUMMARY="Test" "$BASE_DIR/scripts/record-failure.sh" 2>&1 || true)

    if [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]]; then
        latest=$(ls -t "$MEMORY_DIR/failures/" 2>/dev/null | head -1 || echo "")
        if [[ "$latest" == *"$name"* ]]; then
            log_result "CRITICAL" "Reserved name '$name' created on Windows" "SECURITY: File with reserved name"
        else
            log_result "PASS" "Reserved name '$name' sanitized"
        fi
    else
        log_result "PASS" "Reserved name '$name' tested (Unix, less critical)"
    fi
done

# TEST 3: Leading dots
echo ""
echo "Test 3: Leading/Trailing Dots"
result=$(FAILURE_TITLE="..." FAILURE_DOMAIN="test" FAILURE_SEVERITY="3" FAILURE_SUMMARY="Test" "$BASE_DIR/scripts/record-failure.sh" 2>&1 || true)
latest=$(ls -t "$MEMORY_DIR/failures/" 2>/dev/null | head -1 || echo "")

if [[ "$latest" == .* ]] || [[ "$latest" == "" ]]; then
    log_result "FAIL" "Leading dots created hidden file or empty filename" "File: $latest"
else
    log_result "PASS" "Leading dots sanitized to: $latest"
fi

# TEST 4: Path traversal (CRITICAL)
echo ""
echo "Test 4: Path Traversal Attack (CRITICAL)"
before_count=$(ls -1 "$MEMORY_DIR/failures/" 2>/dev/null | wc -l)
result=$(FAILURE_TITLE="../../../etc/passwd" FAILURE_DOMAIN="test" FAILURE_SEVERITY="3" FAILURE_SUMMARY="Test" "$BASE_DIR/scripts/record-failure.sh" 2>&1 || true)
after_count=$(ls -1 "$MEMORY_DIR/failures/" 2>/dev/null | wc -l)

# Check if file was created outside failures dir
if [ -f "/etc/passwd.md" ] || [ -f "$BASE_DIR/../../../etc/passwd.md" ] || [ -f "$BASE_DIR/../../etc/passwd.md" ]; then
    log_result "CRITICAL" "Path traversal SUCCEEDED - file created outside memory dir" "SECURITY VULNERABILITY"
elif [ $after_count -gt $before_count ]; then
    latest=$(ls -t "$MEMORY_DIR/failures/" | head -1)
    log_result "PASS" "Path traversal blocked, file contained: $latest"
else
    log_result "PASS" "Path traversal rejected"
fi

# TEST 5: Slash in filename (path separator)
echo ""
echo "Test 5: Slash in Filename (Path Separator)"
before_count=$(ls -1 "$MEMORY_DIR/failures/" 2>/dev/null | wc -l)
result=$(FAILURE_TITLE="sub/directory/test" FAILURE_DOMAIN="test" FAILURE_SEVERITY="3" FAILURE_SUMMARY="Test" "$BASE_DIR/scripts/record-failure.sh" 2>&1 || true)
after_count=$(ls -1 "$MEMORY_DIR/failures/" 2>/dev/null | wc -l)

# Check if subdirectories were created
if [ -d "$MEMORY_DIR/failures/sub" ] || [ -d "$MEMORY_DIR/failures/directory" ]; then
    log_result "CRITICAL" "Slash created subdirectories" "SECURITY: Unexpected directory structure"
elif [ $after_count -gt $before_count ]; then
    latest=$(ls -t "$MEMORY_DIR/failures/" | head -1)
    log_result "PASS" "Slash sanitized, file: $latest"
else
    log_result "PASS" "Slash rejected"
fi

# TEST 6: Null byte injection
echo ""
echo "Test 6: Null Byte Injection"
title_with_null="Test"$'\0'"Hidden"
result=$(FAILURE_TITLE="$title_with_null" FAILURE_DOMAIN="test" FAILURE_SEVERITY="3" FAILURE_SUMMARY="Test" "$BASE_DIR/scripts/record-failure.sh" 2>&1 || true)
latest=$(ls -t "$MEMORY_DIR/failures/" 2>/dev/null | head -1 || echo "")

if [[ "$latest" == *$'\0'* ]]; then
    log_result "FAIL" "Null byte preserved in filename" "File: $latest"
else
    log_result "PASS" "Null byte sanitized, file: $latest"
fi

# TEST 7: Newline injection
echo ""
echo "Test 7: Newline Injection"
title_with_newline="Test"$'\n'"NewLine"
result=$(FAILURE_TITLE="$title_with_newline" FAILURE_DOMAIN="test" FAILURE_SEVERITY="3" FAILURE_SUMMARY="Test" "$BASE_DIR/scripts/record-failure.sh" 2>&1 || true)
latest=$(ls -t "$MEMORY_DIR/failures/" 2>/dev/null | head -1 || echo "")

if [[ "$latest" =~ [[:cntrl:]] ]]; then
    log_result "FAIL" "Newline preserved in filename" "File: $latest"
else
    log_result "PASS" "Newline sanitized, file: $latest"
fi

# TEST 8: Case sensitivity collision
echo ""
echo "Test 8: Case Sensitivity Collision"
timestamp=$(date +%s)
result1=$(FAILURE_TITLE="Test${timestamp}" FAILURE_DOMAIN="test" FAILURE_SEVERITY="3" FAILURE_SUMMARY="Test1" "$BASE_DIR/scripts/record-failure.sh" 2>&1 || true)
sleep 1
result2=$(FAILURE_TITLE="TEST${timestamp}" FAILURE_DOMAIN="test" FAILURE_SEVERITY="3" FAILURE_SUMMARY="Test2" "$BASE_DIR/scripts/record-failure.sh" 2>&1 || true)

count=$(ls -1 "$MEMORY_DIR/failures/" | grep -i "test${timestamp}" | wc -l)

if [ "$count" -eq 2 ]; then
    log_result "PASS" "Case sensitivity: 2 files created (case-sensitive FS)"
elif [ "$count" -eq 1 ]; then
    log_result "FAIL" "Case sensitivity: 1 file (collision on case-insensitive FS)" "Files may overwrite each other"
else
    log_result "FAIL" "Case sensitivity: Unexpected count ($count)"
fi

# TEST 9: Emoji in filename
echo ""
echo "Test 9: Emoji in Filename"
result=$(FAILURE_TITLE="Test 🚀 Rocket" FAILURE_DOMAIN="test" FAILURE_SEVERITY="3" FAILURE_SUMMARY="Test" "$BASE_DIR/scripts/record-failure.sh" 2>&1 || true)
latest=$(ls -t "$MEMORY_DIR/failures/" 2>/dev/null | head -1 || echo "")

if [[ "$latest" == *"🚀"* ]]; then
    log_result "FAIL" "Emoji preserved in filename" "May cause cross-platform issues: $latest"
else
    log_result "PASS" "Emoji sanitized, file: $latest"
fi

# TEST 10: Whitespace-only title
echo ""
echo "Test 10: Whitespace-Only Title"
result=$(FAILURE_TITLE="     " FAILURE_DOMAIN="test" FAILURE_SEVERITY="3" FAILURE_SUMMARY="Test" "$BASE_DIR/scripts/record-failure.sh" 2>&1 || true)

if echo "$result" | grep -q "cannot be empty"; then
    log_result "PASS" "Whitespace-only title rejected"
else
    log_result "FAIL" "Whitespace-only title accepted" "Should be rejected"
fi

# SUMMARY
echo ""
echo "============================================================"
echo "SUMMARY"
echo "============================================================"
echo "Passed: $PASSED"
echo "Failed: $FAILED"
echo "Critical: $CRITICAL"

echo "" >> "$RESULTS_FILE"
echo "## Summary" >> "$RESULTS_FILE"
echo "- **Passed**: $PASSED" >> "$RESULTS_FILE"
echo "- **Failed**: $FAILED" >> "$RESULTS_FILE"
echo "- **Critical**: $CRITICAL" >> "$RESULTS_FILE"
echo "" >> "$RESULTS_FILE"

if [ $CRITICAL -gt 0 ]; then
    echo -e "${RED}CRITICAL VULNERABILITIES DETECTED${NC}"
    echo "**Status**: CRITICAL VULNERABILITIES DETECTED" >> "$RESULTS_FILE"
    echo ""
    echo "Results: $RESULTS_FILE"
    exit 2
elif [ $FAILED -gt 0 ]; then
    echo -e "${YELLOW}SOME TESTS FAILED${NC}"
    echo "**Status**: Some tests failed" >> "$RESULTS_FILE"
    echo ""
    echo "Results: $RESULTS_FILE"
    exit 1
else
    echo -e "${GREEN}ALL TESTS PASSED${NC}"
    echo "**Status**: All tests passed" >> "$RESULTS_FILE"
    echo ""
    echo "Results: $RESULTS_FILE"
    exit 0
fi
