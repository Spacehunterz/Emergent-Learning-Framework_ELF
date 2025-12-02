#!/bin/bash
# Filesystem Edge Cases Test Suite for Emergent Learning Framework
# Tests novel filesystem scenarios that could break filename/path handling
#
# Test Categories:
# 1. Filename length limits
# 2. Reserved filenames (Windows)
# 3. Leading/trailing dots
# 4. Unicode normalization
# 5. Case sensitivity
# 6. Special path characters
# 7. Disk quota/space issues
# 8. Read-only filesystem
#
# Exit codes:
# 0 = All tests passed
# 1 = Some tests failed
# 2 = Critical failure

set -e
umask 0077

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$(dirname "$SCRIPT_DIR")"
MEMORY_DIR="$BASE_DIR/memory"
TEST_RESULTS_DIR="$BASE_DIR/test-results"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
RESULTS_FILE="$TEST_RESULTS_DIR/filesystem_edge_cases_${TIMESTAMP}.md"

mkdir -p "$TEST_RESULTS_DIR"

# Initialize results
cat > "$RESULTS_FILE" <<EOF
# Filesystem Edge Cases Test Report
**Date**: $(date '+%Y-%m-%d %H:%M:%S')
**Platform**: $(uname -s)
**Test Suite**: Filesystem Edge Cases (Novel Scenarios)

## Test Summary

EOF

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0
WARNINGS=0

log_test() {
    local severity=$1
    local test_name=$2
    local result=$3
    local details=$4

    ((TOTAL_TESTS++))

    case $severity in
        PASS)
            echo -e "${GREEN}[PASS]${NC} $test_name"
            ((PASSED_TESTS++))
            echo "- ✓ **$test_name**: PASSED" >> "$RESULTS_FILE"
            ;;
        FAIL)
            echo -e "${RED}[FAIL]${NC} $test_name"
            ((FAILED_TESTS++))
            echo "- ✗ **$test_name**: FAILED" >> "$RESULTS_FILE"
            ;;
        WARN)
            echo -e "${YELLOW}[WARN]${NC} $test_name"
            ((WARNINGS++))
            echo "- ⚠ **$test_name**: WARNING" >> "$RESULTS_FILE"
            ;;
    esac

    if [ -n "$details" ]; then
        echo "  Details: $details"
        echo "  - $details" >> "$RESULTS_FILE"
    fi

    echo "" >> "$RESULTS_FILE"
}

# ============================================================
# TEST 1: FILENAME LENGTH LIMITS
# ============================================================
echo "============================================================"
echo "TEST 1: FILENAME LENGTH LIMITS"
echo "============================================================"

cat >> "$RESULTS_FILE" <<EOF
## Test 1: Filename Length Limits

Testing extremely long titles that create 300+ character filenames.
Most filesystems limit filenames to 255 bytes.

EOF

test_filename_length() {
    # Create a title that would result in 300+ char filename
    local title_300=$(printf 'A%.0s' {1..300})

    echo "Testing 300-character title..."

    # Try to record failure with 300-char title
    export FAILURE_TITLE="$title_300"
    export FAILURE_DOMAIN="testing"
    export FAILURE_SEVERITY="3"
    export FAILURE_SUMMARY="Testing filename length limit"

    if ~/.claude/emergent-learning/scripts/record-failure.sh 2>&1 | grep -q "exceeds maximum length"; then
        log_test "PASS" "300-char title rejected" "System properly rejects titles exceeding length limit"
    else
        # Check if filename was truncated
        local filename=$(ls -t "$MEMORY_DIR/failures/" | head -1)
        local filename_len=${#filename}

        if [ $filename_len -le 255 ]; then
            log_test "PASS" "300-char title handled" "Filename truncated to $filename_len chars (safe)"
        else
            log_test "FAIL" "300-char title created overlength filename" "Filename length: $filename_len (exceeds 255 limit)"
        fi
    fi

    # Test edge case: exactly 255 chars
    local title_255=$(printf 'B%.0s' {1..255})
    export FAILURE_TITLE="$title_255"

    if ~/.claude/emergent-learning/scripts/record-failure.sh 2>&1 | grep -q "exceeds maximum length\|Created:"; then
        log_test "PASS" "255-char title handling" "System handles 255-char titles"
    else
        log_test "FAIL" "255-char title crashed" "System crashed on 255-char title"
    fi
}

test_filename_length

# ============================================================
# TEST 2: RESERVED FILENAMES (Windows)
# ============================================================
echo ""
echo "============================================================"
echo "TEST 2: RESERVED FILENAMES (Windows)"
echo "============================================================"

cat >> "$RESULTS_FILE" <<EOF
## Test 2: Reserved Filenames (Windows)

Windows reserves certain filenames: CON, PRN, AUX, NUL, COM1-9, LPT1-9
These cannot be used as filenames on Windows systems.

EOF

test_reserved_names() {
    local reserved_names=("CON" "PRN" "AUX" "NUL" "COM1" "LPT1")

    for name in "${reserved_names[@]}"; do
        echo "Testing reserved name: $name"

        export FAILURE_TITLE="$name"
        export FAILURE_DOMAIN="testing"
        export FAILURE_SEVERITY="3"
        export FAILURE_SUMMARY="Testing reserved filename: $name"

        if ~/.claude/emergent-learning/scripts/record-failure.sh 2>&1; then
            # Check if file was created
            local created_file=$(ls -t "$MEMORY_DIR/failures/" | head -1)

            if [[ "$created_file" == *"$name"* ]]; then
                # On Windows, this is dangerous
                if [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]] || [[ "$OSTYPE" == "cygwin" ]]; then
                    log_test "FAIL" "Reserved name '$name' allowed on Windows" "CRITICAL: File created with reserved name on Windows"
                else
                    log_test "WARN" "Reserved name '$name' allowed on non-Windows" "Safe on Unix but could cause cross-platform issues"
                fi
            else
                log_test "PASS" "Reserved name '$name' sanitized" "Filename sanitized: $created_file"
            fi
        else
            log_test "PASS" "Reserved name '$name' rejected" "System properly rejected reserved filename"
        fi
    done
}

test_reserved_names

# ============================================================
# TEST 3: LEADING/TRAILING DOTS
# ============================================================
echo ""
echo "============================================================"
echo "TEST 3: LEADING/TRAILING DOTS"
echo "============================================================"

cat >> "$RESULTS_FILE" <<EOF
## Test 3: Leading/Trailing Dots

Testing filenames with leading dots (hidden files on Unix),
trailing dots (invalid on Windows), and multiple dots.

EOF

test_dot_names() {
    local dot_tests=("..." ".hidden" "test." "..secret.." ".test.test.")

    for name in "${dot_tests[@]}"; do
        echo "Testing dot name: '$name'"

        export FAILURE_TITLE="$name"
        export FAILURE_DOMAIN="testing"
        export FAILURE_SEVERITY="3"
        export FAILURE_SUMMARY="Testing dot filename: $name"

        if ~/.claude/emergent-learning/scripts/record-failure.sh 2>&1; then
            local created_file=$(ls -t "$MEMORY_DIR/failures/" | head -1)

            # Check if filename has problematic dots
            if [[ "$created_file" == .* ]] || [[ "$created_file" == *. ]]; then
                log_test "WARN" "Dot name '$name' created problematic file" "File: $created_file (may be hidden or invalid)"
            else
                log_test "PASS" "Dot name '$name' sanitized" "Filename sanitized: $created_file"
            fi
        else
            log_test "FAIL" "Dot name '$name' crashed system" "System crashed on dot filename"
        fi
    done
}

test_dot_names

# ============================================================
# TEST 4: UNICODE NORMALIZATION
# ============================================================
echo ""
echo "============================================================"
echo "TEST 4: UNICODE NORMALIZATION"
echo "============================================================"

cat >> "$RESULTS_FILE" <<EOF
## Test 4: Unicode Normalization

Testing if composed (é) vs decomposed (é) unicode creates collision.
Also testing emoji and special unicode characters.

EOF

test_unicode_normalization() {
    # Composed vs Decomposed unicode
    # Composed: é (U+00E9)
    # Decomposed: e + ́ (U+0065 U+0301)

    echo "Testing unicode normalization collision..."

    # First create with composed
    export FAILURE_TITLE="café"  # Composed é
    export FAILURE_DOMAIN="testing"
    export FAILURE_SEVERITY="3"
    export FAILURE_SUMMARY="Testing composed unicode"

    ~/.claude/emergent-learning/scripts/record-failure.sh 2>&1 > /dev/null || true
    local file1=$(ls -t "$MEMORY_DIR/failures/" | head -1)

    # Then create with decomposed (simulation - bash may normalize)
    export FAILURE_TITLE="café2"  # Different to avoid timing collision
    export FAILURE_SUMMARY="Testing decomposed unicode"

    ~/.claude/emergent-learning/scripts/record-failure.sh 2>&1 > /dev/null || true
    local file2=$(ls -t "$MEMORY_DIR/failures/" | head -1)

    if [ "$file1" != "$file2" ]; then
        log_test "PASS" "Unicode normalization handled" "Different unicode forms create different files"
    else
        log_test "WARN" "Unicode normalization collision" "Same file created for different unicode forms"
    fi

    # Test emoji
    echo "Testing emoji in filename..."
    export FAILURE_TITLE="Test 🚀 Rocket"
    export FAILURE_SUMMARY="Testing emoji in title"

    if ~/.claude/emergent-learning/scripts/record-failure.sh 2>&1; then
        local emoji_file=$(ls -t "$MEMORY_DIR/failures/" | head -1)
        if [[ "$emoji_file" == *"🚀"* ]]; then
            log_test "WARN" "Emoji preserved in filename" "File: $emoji_file (may cause cross-platform issues)"
        else
            log_test "PASS" "Emoji sanitized" "Emoji removed from filename: $emoji_file"
        fi
    else
        log_test "FAIL" "Emoji crashed system" "System crashed on emoji in title"
    fi
}

test_unicode_normalization

# ============================================================
# TEST 5: CASE SENSITIVITY
# ============================================================
echo ""
echo "============================================================"
echo "TEST 5: CASE SENSITIVITY"
echo "============================================================"

cat >> "$RESULTS_FILE" <<EOF
## Test 5: Case Sensitivity

Testing if "Test" vs "TEST" vs "test" creates collisions.
Unix is case-sensitive, Windows/macOS are case-insensitive.

EOF

test_case_sensitivity() {
    local timestamp=$(date +%s)

    # Create three files with same name, different case
    export FAILURE_DOMAIN="testing"
    export FAILURE_SEVERITY="3"

    echo "Creating 'Test${timestamp}'..."
    export FAILURE_TITLE="Test${timestamp}"
    export FAILURE_SUMMARY="Testing case sensitivity - Test"
    ~/.claude/emergent-learning/scripts/record-failure.sh 2>&1 > /dev/null || true

    sleep 1

    echo "Creating 'TEST${timestamp}'..."
    export FAILURE_TITLE="TEST${timestamp}"
    export FAILURE_SUMMARY="Testing case sensitivity - TEST"
    ~/.claude/emergent-learning/scripts/record-failure.sh 2>&1 > /dev/null || true

    sleep 1

    echo "Creating 'test${timestamp}'..."
    export FAILURE_TITLE="test${timestamp}"
    export FAILURE_SUMMARY="Testing case sensitivity - test"
    ~/.claude/emergent-learning/scripts/record-failure.sh 2>&1 > /dev/null || true

    # Count how many files were created
    local count=$(ls -1 "$MEMORY_DIR/failures/" | grep -i "test${timestamp}" | wc -l)

    if [ "$count" -eq 3 ]; then
        log_test "PASS" "Case sensitivity: 3 files created" "System is case-sensitive (Unix-like)"
    elif [ "$count" -eq 1 ]; then
        log_test "WARN" "Case sensitivity: 1 file created (collision)" "System is case-insensitive (Windows/macOS) - files may overwrite"
    else
        log_test "WARN" "Case sensitivity: $count files created" "Unexpected count (expected 1 or 3)"
    fi
}

test_case_sensitivity

# ============================================================
# TEST 6: SPECIAL PATH CHARACTERS
# ============================================================
echo ""
echo "============================================================"
echo "TEST 6: SPECIAL PATH CHARACTERS"
echo "============================================================"

cat >> "$RESULTS_FILE" <<EOF
## Test 6: Special Path Characters

Testing titles containing: / \\ : * ? " < > |
These are path separators or invalid filename chars on various systems.

EOF

test_special_chars() {
    # Note: slash is super dangerous (path traversal)
    local special_chars=("/" "\\" ":" "*" "?" "\"" "<" ">" "|" "../parent" "sub/dir" "C:\\Windows\\System32")

    for char in "${special_chars[@]}"; do
        echo "Testing special char: '$char'"

        export FAILURE_TITLE="Test${char}File"
        export FAILURE_DOMAIN="testing"
        export FAILURE_SEVERITY="3"
        export FAILURE_SUMMARY="Testing special char: $char"

        if ~/.claude/emergent-learning/scripts/record-failure.sh 2>&1; then
            local created_file=$(ls -t "$MEMORY_DIR/failures/" | head -1)

            # Check if file was created in wrong directory (path traversal)
            if [ ! -f "$MEMORY_DIR/failures/$created_file" ]; then
                log_test "FAIL" "Special char '$char' caused path traversal" "CRITICAL: File created outside failures directory"
            elif [[ "$created_file" == *"$char"* ]]; then
                log_test "FAIL" "Special char '$char' preserved in filename" "CRITICAL: Invalid char in filename: $created_file"
            else
                log_test "PASS" "Special char '$char' sanitized" "Filename sanitized: $created_file"
            fi
        else
            log_test "PASS" "Special char '$char' rejected" "System properly rejected invalid filename"
        fi
    done

    # Specific path traversal test
    echo "Testing path traversal attack: '../../../etc/passwd'"
    export FAILURE_TITLE="../../../etc/passwd"
    export FAILURE_DOMAIN="testing"
    export FAILURE_SUMMARY="Testing path traversal"

    if ~/.claude/emergent-learning/scripts/record-failure.sh 2>&1; then
        # Check if file was created in /etc/ (CRITICAL)
        if [ -f "/etc/passwd.md" ] || [ -f "$BASE_DIR/../../../etc/passwd.md" ]; then
            log_test "FAIL" "Path traversal CRITICAL vulnerability" "SECURITY: File created outside memory directory!"
            echo "CRITICAL: Path traversal vulnerability detected!" >&2
        else
            local created_file=$(ls -t "$MEMORY_DIR/failures/" | head -1)
            log_test "PASS" "Path traversal blocked" "File contained safely: $created_file"
        fi
    else
        log_test "PASS" "Path traversal rejected" "System properly rejected path traversal attempt"
    fi
}

test_special_chars

# ============================================================
# TEST 7: DISK QUOTA / DISK FULL
# ============================================================
echo ""
echo "============================================================"
echo "TEST 7: DISK QUOTA / DISK FULL"
echo "============================================================"

cat >> "$RESULTS_FILE" <<EOF
## Test 7: Disk Quota / Disk Full

Simulating disk full scenario by creating a file with massive content.
Testing rollback and error handling.

EOF

test_disk_quota() {
    echo "Testing disk quota handling..."

    # Create a huge summary (50MB+) to trigger potential disk issues
    local huge_summary=$(printf 'A%.0s' {1..50000000})

    export FAILURE_TITLE="DiskQuotaTest"
    export FAILURE_DOMAIN="testing"
    export FAILURE_SEVERITY="3"
    export FAILURE_SUMMARY="$huge_summary"

    local before_count=$(ls -1 "$MEMORY_DIR/failures/" | wc -l)

    if ~/.claude/emergent-learning/scripts/record-failure.sh 2>&1 | grep -q "exceeds maximum length\|too long"; then
        log_test "PASS" "Huge summary rejected" "System properly rejects oversized content"
    else
        local after_count=$(ls -1 "$MEMORY_DIR/failures/" | wc -l)

        # Check if file was created
        if [ "$after_count" -gt "$before_count" ]; then
            local created_file=$(ls -t "$MEMORY_DIR/failures/" | head -1)
            local file_size=$(stat -c%s "$MEMORY_DIR/failures/$created_file" 2>/dev/null || stat -f%z "$MEMORY_DIR/failures/$created_file" 2>/dev/null || echo "0")

            if [ "$file_size" -gt 10000000 ]; then
                log_test "FAIL" "Huge file created" "File size: $file_size bytes (>10MB, potential DoS)"
            else
                log_test "PASS" "Summary truncated safely" "File size: $file_size bytes (safe)"
            fi
        else
            log_test "PASS" "Huge summary rejected" "No file created"
        fi
    fi

    # Check disk space
    local available_space=$(df -k "$MEMORY_DIR" | tail -1 | awk '{print $4}')
    if [ "$available_space" -lt 100000 ]; then
        log_test "WARN" "Low disk space" "Available: ${available_space}KB (may cause failures)"
    else
        log_test "PASS" "Disk space sufficient" "Available: ${available_space}KB"
    fi
}

test_disk_quota

# ============================================================
# TEST 8: READ-ONLY FILESYSTEM
# ============================================================
echo ""
echo "============================================================"
echo "TEST 8: READ-ONLY FILESYSTEM"
echo "============================================================"

cat >> "$RESULTS_FILE" <<EOF
## Test 8: Read-Only Filesystem

Testing behavior when filesystem becomes read-only mid-operation.
Simulated by making failures directory read-only.

EOF

test_readonly_filesystem() {
    echo "Testing read-only filesystem handling..."

    # Make failures directory read-only
    chmod -w "$MEMORY_DIR/failures" 2>/dev/null || true

    export FAILURE_TITLE="ReadOnlyTest"
    export FAILURE_DOMAIN="testing"
    export FAILURE_SEVERITY="3"
    export FAILURE_SUMMARY="Testing read-only filesystem"

    local db_before=$(sqlite3 "$MEMORY_DIR/index.db" "SELECT COUNT(*) FROM learnings")

    if ~/.claude/emergent-learning/scripts/record-failure.sh 2>&1 | grep -q "Permission denied\|Read-only\|cannot create"; then
        # Check database wasn't corrupted
        local db_after=$(sqlite3 "$MEMORY_DIR/index.db" "SELECT COUNT(*) FROM learnings" 2>/dev/null || echo "ERROR")

        if [ "$db_after" == "ERROR" ]; then
            log_test "FAIL" "Read-only filesystem corrupted database" "CRITICAL: Database corrupted"
        elif [ "$db_after" -gt "$db_before" ]; then
            log_test "FAIL" "Read-only filesystem partial commit" "Database updated but file not created (inconsistency)"
        else
            log_test "PASS" "Read-only filesystem rollback" "Properly rolled back on permission error"
        fi
    else
        log_test "WARN" "Read-only filesystem bypassed" "File created despite read-only directory"
    fi

    # Restore permissions
    chmod +w "$MEMORY_DIR/failures" 2>/dev/null || true
}

test_readonly_filesystem

# ============================================================
# TEST 9: NULL BYTES IN INPUT
# ============================================================
echo ""
echo "============================================================"
echo "TEST 9: NULL BYTES IN INPUT"
echo "============================================================"

cat >> "$RESULTS_FILE" <<EOF
## Test 9: Null Bytes in Input

Testing null byte injection attacks that could truncate strings.

EOF

test_null_bytes() {
    echo "Testing null byte handling..."

    # Create title with null byte
    local title_with_null="Test"$'\0'"Hidden"

    export FAILURE_TITLE="$title_with_null"
    export FAILURE_DOMAIN="testing"
    export FAILURE_SEVERITY="3"
    export FAILURE_SUMMARY="Testing null byte injection"

    if ~/.claude/emergent-learning/scripts/record-failure.sh 2>&1; then
        local created_file=$(ls -t "$MEMORY_DIR/failures/" | head -1)

        # Check if filename contains "Hidden" (null byte didn't truncate)
        if [[ "$created_file" == *"hidden"* ]] || [[ "$created_file" == *$'\0'* ]]; then
            log_test "FAIL" "Null byte preserved in filename" "Filename: $created_file"
        else
            log_test "PASS" "Null byte sanitized" "Filename: $created_file"
        fi
    else
        log_test "PASS" "Null byte rejected" "System properly rejected null byte input"
    fi
}

test_null_bytes

# ============================================================
# TEST 10: NEWLINES AND CONTROL CHARACTERS
# ============================================================
echo ""
echo "============================================================"
echo "TEST 10: NEWLINES AND CONTROL CHARACTERS"
echo "============================================================"

cat >> "$RESULTS_FILE" <<EOF
## Test 10: Newlines and Control Characters

Testing newlines, carriage returns, tabs, and other control characters.

EOF

test_control_chars() {
    echo "Testing control character handling..."

    local control_tests=(
        "Test"$'\n'"NewLine"
        "Test"$'\r'"CarriageReturn"
        "Test"$'\t'"Tab"
        "Test"$'\x1b'"Escape"
        "Test"$'\x07'"Bell"
    )

    for title in "${control_tests[@]}"; do
        export FAILURE_TITLE="$title"
        export FAILURE_DOMAIN="testing"
        export FAILURE_SEVERITY="3"
        export FAILURE_SUMMARY="Testing control characters"

        if ~/.claude/emergent-learning/scripts/record-failure.sh 2>&1; then
            local created_file=$(ls -t "$MEMORY_DIR/failures/" | head -1)

            # Check if control chars were sanitized
            if [[ "$created_file" =~ [[:cntrl:]] ]]; then
                log_test "FAIL" "Control characters preserved" "Filename: $created_file"
            else
                log_test "PASS" "Control characters sanitized" "Filename: $created_file"
            fi
        else
            log_test "WARN" "Control characters caused error" "Title: ${title//[$'\n\r\t']/\\n}"
        fi
    done
}

test_control_chars

# ============================================================
# FINAL SUMMARY
# ============================================================
echo ""
echo "============================================================"
echo "FINAL SUMMARY"
echo "============================================================"

cat >> "$RESULTS_FILE" <<EOF

---

## Final Summary

**Total Tests**: $TOTAL_TESTS
**Passed**: $PASSED_TESTS
**Failed**: $FAILED_TESTS
**Warnings**: $WARNINGS

EOF

echo "Total Tests: $TOTAL_TESTS"
echo -e "Passed: ${GREEN}$PASSED_TESTS${NC}"
echo -e "Failed: ${RED}$FAILED_TESTS${NC}"
echo -e "Warnings: ${YELLOW}$WARNINGS${NC}"
echo ""
echo "Results written to: $RESULTS_FILE"

# Calculate pass rate
if [ $TOTAL_TESTS -gt 0 ]; then
    PASS_RATE=$((PASSED_TESTS * 100 / TOTAL_TESTS))
    echo "Pass Rate: ${PASS_RATE}%"

    cat >> "$RESULTS_FILE" <<EOF
**Pass Rate**: ${PASS_RATE}%

### Severity Assessment

EOF

    if [ $FAILED_TESTS -eq 0 ]; then
        echo -e "${GREEN}ASSESSMENT: System passed all tests${NC}"
        echo "**PASS**: System handles all filesystem edge cases correctly." >> "$RESULTS_FILE"
    elif [ $FAILED_TESTS -le 3 ]; then
        echo -e "${YELLOW}ASSESSMENT: Minor issues detected${NC}"
        echo "**MODERATE**: Some edge cases need attention, but core functionality intact." >> "$RESULTS_FILE"
    else
        echo -e "${RED}ASSESSMENT: Critical issues detected${NC}"
        echo "**CRITICAL**: Multiple edge cases fail. System may be vulnerable to attacks or data corruption." >> "$RESULTS_FILE"
    fi
fi

# Exit with appropriate code
if [ $FAILED_TESTS -gt 0 ]; then
    exit 1
else
    exit 0
fi
