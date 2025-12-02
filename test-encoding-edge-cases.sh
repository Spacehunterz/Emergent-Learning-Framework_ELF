#!/bin/bash
# Test NOVEL encoding edge cases for the Emergent Learning Framework
# Tests various attack vectors and edge cases that could break the system

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DB_PATH="$SCRIPT_DIR/memory/index.db"
FAILURES_DIR="$SCRIPT_DIR/memory/failures"
RECORD_SCRIPT="$SCRIPT_DIR/scripts/record-failure.sh"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test counter
TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0

# Array to store detailed results
declare -a RESULTS

echo "=========================================="
echo "ENCODING EDGE CASE TESTING"
echo "Testing Emergent Learning Framework"
echo "=========================================="
echo ""

# Helper function to run test
run_test() {
    local test_name="$1"
    local title="$2"
    local summary="$3"
    local severity="${4:-3}"
    local expected_outcome="${5:-PASS}" # PASS, FAIL_SAFE, or CORRUPTED

    TESTS_RUN=$((TESTS_RUN + 1))
    echo -e "${BLUE}[TEST $TESTS_RUN]${NC} $test_name"
    echo "  Title: $(echo "$title" | cat -v | head -c 80)..."
    echo "  Expected: $expected_outcome"

    # Run the record-failure script
    local exit_code=0
    local output=""
    output=$(FAILURE_TITLE="$title" \
             FAILURE_DOMAIN="encoding-test" \
             FAILURE_SUMMARY="$summary" \
             FAILURE_SEVERITY="$severity" \
             "$RECORD_SCRIPT" 2>&1) || exit_code=$?

    # Get the last inserted record
    local db_title=""
    local db_summary=""
    local md_file=""
    local md_title=""
    local md_summary=""

    if [ $exit_code -eq 0 ]; then
        # Extract from database
        db_title=$(sqlite3 "$DB_PATH" "SELECT title FROM learnings WHERE domain='encoding-test' ORDER BY id DESC LIMIT 1;" 2>/dev/null || echo "")
        db_summary=$(sqlite3 "$DB_PATH" "SELECT summary FROM learnings WHERE domain='encoding-test' ORDER BY id DESC LIMIT 1;" 2>/dev/null || echo "")

        # Find the markdown file
        md_file=$(find "$FAILURES_DIR" -name "*.md" -type f -newer "$SCRIPT_DIR/test-encoding-edge-cases.sh" 2>/dev/null | head -1)

        if [ -n "$md_file" ]; then
            # Extract title and summary from markdown
            md_title=$(grep "^# " "$md_file" | head -1 | sed 's/^# //')
            md_summary=$(sed -n '/^## Summary/,/^## /p' "$md_file" | grep -v "^##" | grep -v "^\[" | head -1 | xargs)
        fi
    fi

    # Analyze results
    local test_result="UNKNOWN"
    local details=""
    local severity_level="INFO"

    if [ $exit_code -ne 0 ]; then
        test_result="FAIL_SAFE"
        details="Script exited with code $exit_code (rejected input safely)"
        severity_level="LOW"

        if [ "$expected_outcome" = "FAIL_SAFE" ]; then
            echo -e "  ${GREEN}✓ PASS${NC} - Failed safely as expected"
            TESTS_PASSED=$((TESTS_PASSED + 1))
        else
            echo -e "  ${YELLOW}⚠ UNEXPECTED${NC} - Expected $expected_outcome but got FAIL_SAFE"
        fi
    else
        # Check for corruption/injection
        local corruption_found=0

        # Check NULL bytes
        if echo "$db_title" | grep -q $'\x00' 2>/dev/null; then
            corruption_found=1
            details="${details}NULL byte in DB title; "
        fi

        # Check if title matches what we sent
        if [ "$db_title" != "$title" ]; then
            # Check if it's just truncation/sanitization vs corruption
            if [ -z "$db_title" ]; then
                corruption_found=1
                details="${details}DB title is empty; "
            else
                details="${details}DB title differs (may be sanitized); "
            fi
        fi

        # Check markdown file
        if [ -n "$md_file" ]; then
            # Check for control character injection
            if grep -q $'\x1b\[' "$md_file" 2>/dev/null; then
                corruption_found=1
                details="${details}ANSI escape codes in MD file; "
            fi

            # Check for CRLF injection creating new headers
            if grep -q $'\r' "$md_file" 2>/dev/null; then
                details="${details}CRLF characters in MD file; "
            fi

            # Check if file is valid UTF-8
            if ! iconv -f UTF-8 -t UTF-8 "$md_file" > /dev/null 2>&1; then
                corruption_found=1
                details="${details}MD file has invalid UTF-8; "
            fi
        fi

        if [ $corruption_found -eq 1 ]; then
            test_result="CORRUPTED"
            severity_level="CRITICAL"
            echo -e "  ${RED}✗ FAIL${NC} - Data corruption detected!"
            echo -e "  ${RED}  Details: $details${NC}"
            TESTS_FAILED=$((TESTS_FAILED + 1))
        else
            test_result="PASS"
            severity_level="INFO"
            echo -e "  ${GREEN}✓ PASS${NC} - Input handled correctly"
            echo -e "    DB stored: $(echo "$db_title" | cat -v | head -c 60)"
            TESTS_PASSED=$((TESTS_PASSED + 1))
        fi
    fi

    # Store result
    RESULTS+=("$test_name|$test_result|$severity_level|$details")
    echo ""
}

# ==========================================
# TEST 1: NULL bytes in input
# ==========================================
echo "=========================================="
echo "TEST CATEGORY 1: NULL BYTE INJECTION"
echo "=========================================="

run_test \
    "NULL byte in title" \
    "Test$(printf '\x00')Title" \
    "Testing NULL byte handling" \
    3 \
    "FAIL_SAFE"

run_test \
    "Multiple NULL bytes" \
    "$(printf 'Test\x00\x00\x00Data')" \
    "Multiple NULL bytes in sequence" \
    3 \
    "FAIL_SAFE"

run_test \
    "NULL byte in summary" \
    "Normal Title" \
    "Summary with$(printf '\x00')null byte" \
    3 \
    "FAIL_SAFE"

# ==========================================
# TEST 2: Very long Unicode
# ==========================================
echo "=========================================="
echo "TEST CATEGORY 2: VERY LONG UNICODE"
echo "=========================================="

# Generate 500 emoji characters
long_emoji=$(python3 -c "print('🔥' * 500)" 2>/dev/null || echo "🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥")

run_test \
    "500 emoji title" \
    "$long_emoji" \
    "Testing very long emoji sequence" \
    3 \
    "PASS"

# Mix of different emoji
mixed_emoji=$(python3 -c "import random; emojis=['😀','🔥','💀','🎉','⚠️','✓','❌','🚀']; print(''.join(random.choice(emojis) for _ in range(200)))" 2>/dev/null || echo "😀🔥💀🎉")

run_test \
    "200 mixed emoji" \
    "$mixed_emoji" \
    "Testing mixed emoji variety" \
    3 \
    "PASS"

# ==========================================
# TEST 3: RTL text mixing
# ==========================================
echo "=========================================="
echo "TEST CATEGORY 3: RTL TEXT MIXING"
echo "=========================================="

run_test \
    "Hebrew-English mix" \
    "שלום Hello עולם World" \
    "Testing Hebrew and English mixed text" \
    3 \
    "PASS"

run_test \
    "Arabic-English mix" \
    "مرحبا Hello العالم World" \
    "Testing Arabic and English mixed text" \
    3 \
    "PASS"

run_test \
    "RTL override characters" \
    "Test$(printf '\u202e')gnirts reversed" \
    "Testing Unicode RTL override" \
    3 \
    "PASS"

# ==========================================
# TEST 4: Zalgo text
# ==========================================
echo "=========================================="
echo "TEST CATEGORY 4: ZALGO TEXT"
echo "=========================================="

zalgo_text=$(python3 -c "print('T̸̢̛̰͓̺̮̱̘̻̜̟̼͉̟̭̗͇̏̑̋̌̎̈́̀̀̈́͛̌̕͝͝h̸̨̧̳̗̘̠̹̜̖̫̗̲̯͉̋̄̍̓̈́̈́̕ͅi̵̧̨̱̘̭̫̯̯̼̝̘̹̋̿̈́͐̐̓s̸̰̖̱̩̟̰̈́̍̿͗̃̂̊̕')" 2>/dev/null || echo "T̴h̴i̴s̴")

run_test \
    "Zalgo text" \
    "$zalgo_text is zalgo" \
    "Testing combining diacritics" \
    3 \
    "PASS"

run_test \
    "Extreme zalgo" \
    "$(python3 -c "import unicodedata; base='T'; marks=''.join([chr(i) for i in range(0x0300, 0x0370)]); print(base + marks)" 2>/dev/null || echo "T̴̵̶")" \
    "Testing extreme diacritic stacking" \
    3 \
    "PASS"

# ==========================================
# TEST 5: Non-BMP characters
# ==========================================
echo "=========================================="
echo "TEST CATEGORY 5: NON-BMP CHARACTERS"
echo "=========================================="

run_test \
    "Mathematical Alphanumeric Symbols" \
    "𝕳𝖊𝖑𝖑𝖔 𝖂𝖔𝖗𝖑𝖉" \
    "Testing mathematical bold fraktur" \
    3 \
    "PASS"

run_test \
    "Ancient scripts" \
    "𓀀 𓀁 𓀂 Egyptian 𐎀 𐎁 Ugaritic" \
    "Testing ancient scripts" \
    3 \
    "PASS"

run_test \
    "Emoji and symbols mix" \
    "🔥💻🚀 Code 𝕳𝖊𝖑𝖑𝖔 World 🌍" \
    "Testing emoji with non-BMP math symbols" \
    3 \
    "PASS"

# ==========================================
# TEST 6: CRLF injection
# ==========================================
echo "=========================================="
echo "TEST CATEGORY 6: CRLF INJECTION"
echo "=========================================="

run_test \
    "CRLF in title" \
    "Normal Title$(printf '\r\n')## Injected Header" \
    "Testing CRLF injection in title" \
    3 \
    "FAIL_SAFE"

run_test \
    "Multiple CRLF" \
    "Title$(printf '\r\n\r\n\r\n')More content" \
    "Testing multiple CRLF sequences" \
    3 \
    "FAIL_SAFE"

run_test \
    "CRLF with markdown injection" \
    "Title$(printf '\r\n**Domain**: hacked\r\n**Severity**: 5')" \
    "Testing markdown metadata injection" \
    3 \
    "FAIL_SAFE"

# ==========================================
# TEST 7: Control characters
# ==========================================
echo "=========================================="
echo "TEST CATEGORY 7: CONTROL CHARACTERS"
echo "=========================================="

run_test \
    "Bell character" \
    "Title$(printf '\a')with bell" \
    "Testing bell character (\\a)" \
    3 \
    "FAIL_SAFE"

run_test \
    "Backspace injection" \
    "Title$(printf '\b\b\b\b\b')erased" \
    "Testing backspace characters" \
    3 \
    "FAIL_SAFE"

run_test \
    "ANSI escape sequences" \
    "$(printf '\033[31m')Red Title$(printf '\033[0m')" \
    "Testing ANSI color codes" \
    3 \
    "FAIL_SAFE"

run_test \
    "Terminal control sequences" \
    "$(printf '\033]0;Hacked Terminal Title\007')Title" \
    "Testing terminal title injection" \
    3 \
    "FAIL_SAFE"

run_test \
    "Form feed and vertical tab" \
    "Title$(printf '\f\v')with control chars" \
    "Testing form feed and vertical tab" \
    3 \
    "FAIL_SAFE"

# ==========================================
# BONUS TESTS: SQL Injection attempts
# ==========================================
echo "=========================================="
echo "BONUS TESTS: SQL INJECTION ATTEMPTS"
echo "=========================================="

run_test \
    "SQL comment injection" \
    "'; DROP TABLE learnings; --" \
    "Testing SQL injection with comment" \
    3 \
    "PASS"

run_test \
    "SQL UNION injection" \
    "' UNION SELECT * FROM learnings --" \
    "Testing SQL UNION attack" \
    3 \
    "PASS"

run_test \
    "SQL boolean injection" \
    "' OR '1'='1" \
    "Testing SQL boolean bypass" \
    3 \
    "PASS"

# ==========================================
# RESULTS SUMMARY
# ==========================================
echo ""
echo "=========================================="
echo "TEST RESULTS SUMMARY"
echo "=========================================="
echo ""
echo "Total Tests Run: $TESTS_RUN"
echo -e "${GREEN}Tests Passed: $TESTS_PASSED${NC}"
echo -e "${RED}Tests Failed: $TESTS_FAILED${NC}"
echo ""

if [ $TESTS_FAILED -gt 0 ]; then
    echo -e "${RED}=========================================="
    echo "CRITICAL FINDINGS"
    echo "==========================================${NC}"
    echo ""

    for result in "${RESULTS[@]}"; do
        IFS='|' read -r test_name test_result severity_level details <<< "$result"
        if [ "$test_result" = "CORRUPTED" ]; then
            echo -e "${RED}[CRITICAL]${NC} $test_name"
            echo "  Result: $test_result"
            echo "  Details: $details"
            echo ""
        fi
    done
fi

# Generate detailed report
REPORT_FILE="$SCRIPT_DIR/ENCODING_EDGE_CASE_TEST_REPORT_$(date +%Y%m%d_%H%M%S).md"

cat > "$REPORT_FILE" <<EOFR
# Encoding Edge Case Test Report

**Test Date**: $(date '+%Y-%m-%d %H:%M:%S')
**Framework**: Emergent Learning Framework
**Test Type**: Novel Encoding Edge Cases

## Executive Summary

- **Total Tests**: $TESTS_RUN
- **Passed**: $TESTS_PASSED
- **Failed**: $TESTS_FAILED
- **Pass Rate**: $(( TESTS_PASSED * 100 / TESTS_RUN ))%

## Detailed Results

| Test Name | Result | Severity | Details |
|-----------|--------|----------|---------|
EOFR

for result in "${RESULTS[@]}"; do
    IFS='|' read -r test_name test_result severity_level details <<< "$result"
    echo "| $test_name | $test_result | $severity_level | $details |" >> "$REPORT_FILE"
done

cat >> "$REPORT_FILE" <<EOFR

## Test Categories

### 1. NULL Byte Injection
Tests whether NULL bytes (\\x00) can corrupt database storage or markdown files.

**Risk**: NULL bytes can truncate strings in C-based libraries, causing data loss or injection.

### 2. Very Long Unicode
Tests handling of extremely long Unicode sequences (500+ emoji).

**Risk**: Memory exhaustion, buffer overflows, or rendering issues.

### 3. RTL Text Mixing
Tests bidirectional text (Hebrew/Arabic) mixed with English and RTL override characters.

**Risk**: UI spoofing, display corruption, or text direction attacks.

### 4. Zalgo Text
Tests combining diacritical marks stacked on characters.

**Risk**: Rendering issues, excessive memory use, or display corruption.

### 5. Non-BMP Characters
Tests Unicode characters outside Basic Multilingual Plane (mathematical symbols, ancient scripts).

**Risk**: Encoding errors in systems assuming 16-bit Unicode.

### 6. CRLF Injection
Tests carriage return/line feed injection to insert new markdown headers.

**Risk**: Markdown structure injection, metadata spoofing.

### 7. Control Characters
Tests bell, backspace, ANSI escape sequences, and terminal control codes.

**Risk**: Terminal manipulation, visual spoofing, or logging corruption.

## Vulnerability Assessment

EOFR

if [ $TESTS_FAILED -gt 0 ]; then
    cat >> "$REPORT_FILE" <<EOFR
### CRITICAL VULNERABILITIES FOUND

The following tests revealed data corruption or injection vulnerabilities:

EOFR

    for result in "${RESULTS[@]}"; do
        IFS='|' read -r test_name test_result severity_level details <<< "$result"
        if [ "$test_result" = "CORRUPTED" ]; then
            cat >> "$REPORT_FILE" <<EOFR
#### $test_name
- **Severity**: $severity_level
- **Details**: $details
- **Recommendation**: IMMEDIATE FIX REQUIRED

EOFR
        fi
    done
else
    cat >> "$REPORT_FILE" <<EOFR
### NO CRITICAL VULNERABILITIES FOUND

All edge cases were handled correctly. The system either:
- Safely rejected invalid input (fail-safe behavior)
- Properly sanitized and stored the data
- Correctly handled Unicode edge cases

The current implementation shows robust input validation.
EOFR
fi

cat >> "$REPORT_FILE" <<EOFR

## Recommendations

1. **Input Validation**: Continue validating all user input
2. **Encoding**: Maintain UTF-8 throughout the pipeline
3. **Sanitization**: Escape/remove control characters before storage
4. **Testing**: Add these edge cases to automated test suite
5. **Monitoring**: Log rejected inputs for security analysis

## Technical Details

- **Database**: SQLite with UTF-8 encoding
- **Escape Function**: Single quote doubling for SQL injection prevention
- **Markdown**: Direct variable interpolation (potential injection point)
- **File Operations**: TOCTOU and hardlink protection in place

---

Generated by: test-encoding-edge-cases.sh
EOFR

echo ""
echo "Detailed report saved to:"
echo "  $REPORT_FILE"
echo ""

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}All tests passed! The framework handles encoding edge cases correctly.${NC}"
    exit 0
else
    echo -e "${RED}$TESTS_FAILED test(s) failed! Review the report for details.${NC}"
    exit 1
fi
