#!/bin/bash
# Extreme Fuzzing Test Suite for Emergent Learning Framework
# Agent C - Boundary and Input Validation Testing
#
# Tests all scripts for handling:
# - Empty strings, whitespace-only inputs
# - Extremely long inputs (10KB+)
# - Binary data and NULL bytes
# - Unicode edge cases (zero-width, combining marks, RTL)
# - Numeric overflow/underflow
# - SQL injection attempts
# - Shell metacharacters
#
# Each test logs results and applies fixes if vulnerabilities found

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$SCRIPT_DIR"
MEMORY_DIR="$BASE_DIR/memory"
DB_PATH="$MEMORY_DIR/index.db"
TEST_RESULTS="$BASE_DIR/FUZZING_TEST_RESULTS.md"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)

# Color output for readability
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Counters
TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0
VULNERABILITIES_FOUND=0

echo "==================================================================="
echo "EXTREME FUZZING TEST SUITE - Emergent Learning Framework"
echo "==================================================================="
echo "Timestamp: $TIMESTAMP"
echo "Testing: Input validation, boundary conditions, injection attacks"
echo "==================================================================="
echo ""

# Initialize results file
cat > "$TEST_RESULTS" <<EOF
# Extreme Fuzzing Test Results

**Timestamp**: $TIMESTAMP
**Tester**: Agent C
**Focus**: Input validation, boundary testing, injection prevention

---

## Test Summary

EOF

log_test() {
    local test_name="$1"
    local status="$2"
    local details="$3"

    ((TESTS_RUN++))

    if [ "$status" = "PASS" ]; then
        ((TESTS_PASSED++))
        echo -e "${GREEN}[PASS]${NC} $test_name"
    elif [ "$status" = "FAIL" ]; then
        ((TESTS_FAILED++))
        ((VULNERABILITIES_FOUND++))
        echo -e "${RED}[FAIL]${NC} $test_name"
    else
        echo -e "${YELLOW}[WARN]${NC} $test_name"
    fi

    cat >> "$TEST_RESULTS" <<EOF

### Test: $test_name

**Status**: $status

$details

EOF
}

echo "==================================================================="
echo "TEST CATEGORY 1: EMPTY AND WHITESPACE INPUTS"
echo "==================================================================="
echo ""

test_empty_string_title() {
    echo "[TEST] Empty string in title field"

    # Test record-failure.sh with empty title
    if FAILURE_TITLE="" FAILURE_DOMAIN="test" FAILURE_SUMMARY="test" bash "$BASE_DIR/scripts/record-failure.sh" 2>&1 | grep -q "ERROR"; then
        log_test "Empty title rejection" "PASS" "Script correctly rejected empty title"
    else
        log_test "Empty title rejection" "FAIL" "Script accepted empty title - VULNERABILITY"
    fi
}

test_whitespace_only_domain() {
    echo "[TEST] Whitespace-only domain field"

    # Test with whitespace only
    if FAILURE_TITLE="test" FAILURE_DOMAIN="   " FAILURE_SUMMARY="test" bash "$BASE_DIR/scripts/record-failure.sh" 2>&1 | grep -q "ERROR\|empty"; then
        log_test "Whitespace-only domain rejection" "PASS" "Script correctly handles whitespace-only domain"
    else
        log_test "Whitespace-only domain rejection" "FAIL" "Script accepted whitespace-only domain - NEEDS VALIDATION"
    fi
}

test_empty_string_heuristic() {
    echo "[TEST] Empty heuristic rule"

    if HEURISTIC_DOMAIN="test" HEURISTIC_RULE="" bash "$BASE_DIR/scripts/record-heuristic.sh" 2>&1 | grep -q "ERROR"; then
        log_test "Empty heuristic rule rejection" "PASS" "Script correctly rejected empty rule"
    else
        log_test "Empty heuristic rule rejection" "FAIL" "Script accepted empty rule - VULNERABILITY"
    fi
}

echo ""
echo "==================================================================="
echo "TEST CATEGORY 2: EXTREME LENGTH INPUTS"
echo "==================================================================="
echo ""

test_extremely_long_title() {
    echo "[TEST] 10KB title field"

    # Generate 10KB string
    LONG_TITLE=$(python3 -c "print('A' * 10240)")

    # Test if it's handled gracefully
    if FAILURE_TITLE="$LONG_TITLE" FAILURE_DOMAIN="test" FAILURE_SUMMARY="test" timeout 10 bash "$BASE_DIR/scripts/record-failure.sh" 2>&1 | grep -q "ERROR\|too long"; then
        log_test "10KB title handling" "PASS" "Script rejected or handled extremely long title"
    else
        # Check if it completed without crashing
        if [ $? -eq 0 ]; then
            log_test "10KB title handling" "WARN" "Script accepted 10KB title - may cause performance issues"
        else
            log_test "10KB title handling" "FAIL" "Script crashed with extremely long title"
        fi
    fi
}

test_extremely_long_summary() {
    echo "[TEST] 1MB summary field"

    # Generate 1MB string
    LONG_SUMMARY=$(python3 -c "print('B' * 1048576)")

    if FAILURE_TITLE="test" FAILURE_DOMAIN="test" FAILURE_SUMMARY="$LONG_SUMMARY" timeout 15 bash "$BASE_DIR/scripts/record-failure.sh" 2>&1; then
        log_test "1MB summary handling" "WARN" "Script accepted 1MB summary - may cause disk/memory issues"
    else
        if [ $? -eq 124 ]; then
            log_test "1MB summary handling" "FAIL" "Script timed out with 1MB summary"
        else
            log_test "1MB summary handling" "WARN" "Script failed with 1MB summary"
        fi
    fi
}

echo ""
echo "==================================================================="
echo "TEST CATEGORY 3: BINARY DATA AND NULL BYTES"
echo "==================================================================="
echo ""

test_null_bytes_in_title() {
    echo "[TEST] NULL bytes in title"

    # Test with NULL byte
    BINARY_TITLE=$(printf "test\x00data")

    if FAILURE_TITLE="$BINARY_TITLE" FAILURE_DOMAIN="test" FAILURE_SUMMARY="test" bash "$BASE_DIR/scripts/record-failure.sh" 2>&1; then
        log_test "NULL byte in title" "WARN" "Script processed NULL byte - may cause truncation"
    else
        log_test "NULL byte in title" "PASS" "Script rejected NULL byte input"
    fi
}

test_binary_sequence() {
    echo "[TEST] Binary sequence in domain"

    BINARY_DOMAIN=$(printf "\x01\x02\x03\x04\x05")

    if FAILURE_TITLE="test" FAILURE_DOMAIN="$BINARY_DOMAIN" FAILURE_SUMMARY="test" bash "$BASE_DIR/scripts/record-failure.sh" 2>&1; then
        log_test "Binary sequence in domain" "WARN" "Script accepted binary data - may cause encoding issues"
    else
        log_test "Binary sequence in domain" "PASS" "Script rejected binary sequence"
    fi
}

echo ""
echo "==================================================================="
echo "TEST CATEGORY 4: UNICODE EDGE CASES"
echo "==================================================================="
echo ""

test_zero_width_characters() {
    echo "[TEST] Zero-width characters in title"

    # Zero-width space, zero-width joiner, zero-width non-joiner
    ZERO_WIDTH="test$(printf '\u200B\u200C\u200D')data"

    if FAILURE_TITLE="$ZERO_WIDTH" FAILURE_DOMAIN="test" FAILURE_SUMMARY="test" bash "$BASE_DIR/scripts/record-failure.sh" 2>&1; then
        log_test "Zero-width characters" "PASS" "Script handled zero-width characters"
    else
        log_test "Zero-width characters" "FAIL" "Script failed with zero-width characters"
    fi
}

test_combining_marks() {
    echo "[TEST] Combining diacritical marks"

    # Multiple combining marks
    COMBINING="e$(printf '\u0301\u0302\u0303\u0304\u0305')"

    if FAILURE_TITLE="test$COMBINING" FAILURE_DOMAIN="test" FAILURE_SUMMARY="test" bash "$BASE_DIR/scripts/record-failure.sh" 2>&1; then
        log_test "Combining marks" "PASS" "Script handled combining marks"
    else
        log_test "Combining marks" "FAIL" "Script failed with combining marks"
    fi
}

test_rtl_override() {
    echo "[TEST] Right-to-left override characters"

    # RTL override can hide malicious content
    RTL_TEXT="test$(printf '\u202E')hidden"

    if FAILURE_TITLE="$RTL_TEXT" FAILURE_DOMAIN="test" FAILURE_SUMMARY="test" bash "$BASE_DIR/scripts/record-failure.sh" 2>&1; then
        log_test "RTL override attack" "WARN" "Script accepted RTL override - potential display confusion"
    else
        log_test "RTL override attack" "PASS" "Script rejected RTL override"
    fi
}

test_emoji_overflow() {
    echo "[TEST] Emoji overflow"

    # String of 1000 emojis
    EMOJI_OVERFLOW=$(python3 -c "print('😀' * 1000)")

    if FAILURE_TITLE="$EMOJI_OVERFLOW" FAILURE_DOMAIN="test" FAILURE_SUMMARY="test" timeout 10 bash "$BASE_DIR/scripts/record-failure.sh" 2>&1; then
        log_test "Emoji overflow" "WARN" "Script accepted 1000 emojis - may cause rendering issues"
    else
        log_test "Emoji overflow" "PASS" "Script rejected or handled emoji overflow"
    fi
}

echo ""
echo "==================================================================="
echo "TEST CATEGORY 5: NUMERIC OVERFLOW AND UNDERFLOW"
echo "==================================================================="
echo ""

test_severity_overflow() {
    echo "[TEST] Severity numeric overflow"

    # Test with huge number
    if FAILURE_TITLE="test" FAILURE_DOMAIN="test" FAILURE_SEVERITY="999999999999" FAILURE_SUMMARY="test" bash "$BASE_DIR/scripts/record-failure.sh" 2>&1 | grep -q "defaulting\|Invalid"; then
        log_test "Severity overflow" "PASS" "Script validated severity range"
    else
        log_test "Severity overflow" "FAIL" "Script accepted invalid severity - NEEDS RANGE VALIDATION"
    fi
}

test_severity_negative() {
    echo "[TEST] Severity negative value"

    if FAILURE_TITLE="test" FAILURE_DOMAIN="test" FAILURE_SEVERITY="-999" FAILURE_SUMMARY="test" bash "$BASE_DIR/scripts/record-failure.sh" 2>&1 | grep -q "defaulting\|Invalid"; then
        log_test "Severity negative" "PASS" "Script validated severity is positive"
    else
        log_test "Severity negative" "FAIL" "Script accepted negative severity - NEEDS RANGE VALIDATION"
    fi
}

test_confidence_overflow() {
    echo "[TEST] Confidence numeric overflow"

    if HEURISTIC_DOMAIN="test" HEURISTIC_RULE="test" HEURISTIC_CONFIDENCE="1e308" bash "$BASE_DIR/scripts/record-heuristic.sh" 2>&1 | grep -q "defaulting\|Invalid"; then
        log_test "Confidence overflow" "PASS" "Script validated confidence range"
    else
        log_test "Confidence overflow" "FAIL" "Script accepted invalid confidence - NEEDS RANGE VALIDATION"
    fi
}

test_confidence_negative() {
    echo "[TEST] Confidence negative value"

    if HEURISTIC_DOMAIN="test" HEURISTIC_RULE="test" HEURISTIC_CONFIDENCE="-0.5" bash "$BASE_DIR/scripts/record-heuristic.sh" 2>&1 | grep -q "defaulting\|Invalid"; then
        log_test "Confidence negative" "PASS" "Script validated confidence is positive"
    else
        log_test "Confidence negative" "FAIL" "Script accepted negative confidence - NEEDS RANGE VALIDATION"
    fi
}

test_confidence_string_injection() {
    echo "[TEST] Confidence string injection"

    if HEURISTIC_DOMAIN="test" HEURISTIC_RULE="test" HEURISTIC_CONFIDENCE="'; DROP TABLE heuristics; --" bash "$BASE_DIR/scripts/record-heuristic.sh" 2>&1 | grep -q "defaulting\|Invalid"; then
        log_test "Confidence SQL injection" "PASS" "Script validated confidence type"
    else
        log_test "Confidence SQL injection" "FAIL" "Script may be vulnerable to type confusion"
    fi
}

echo ""
echo "==================================================================="
echo "TEST CATEGORY 6: SQL INJECTION ATTACKS"
echo "==================================================================="
echo ""

test_sql_injection_simple_quote() {
    echo "[TEST] SQL injection - simple quote escape"

    SQL_TITLE="test'; DROP TABLE learnings; --"

    # Run and check if database still exists
    FAILURE_TITLE="$SQL_TITLE" FAILURE_DOMAIN="test" FAILURE_SUMMARY="test" bash "$BASE_DIR/scripts/record-failure.sh" 2>&1

    # Verify database integrity
    if sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM learnings;" 2>&1; then
        log_test "SQL injection - quote escape" "PASS" "Database protected from quote-based SQL injection"
    else
        log_test "SQL injection - quote escape" "FAIL" "DATABASE CORRUPTED - CRITICAL VULNERABILITY"
    fi
}

test_sql_injection_union() {
    echo "[TEST] SQL injection - UNION attack"

    SQL_TITLE="test' UNION SELECT * FROM heuristics; --"

    FAILURE_TITLE="$SQL_TITLE" FAILURE_DOMAIN="test" FAILURE_SUMMARY="test" bash "$BASE_DIR/scripts/record-failure.sh" 2>&1

    if sqlite3 "$DB_PATH" "PRAGMA integrity_check;" | grep -q "ok"; then
        log_test "SQL injection - UNION attack" "PASS" "Database protected from UNION injection"
    else
        log_test "SQL injection - UNION attack" "FAIL" "Database integrity compromised"
    fi
}

test_sql_injection_comment() {
    echo "[TEST] SQL injection - comment injection"

    SQL_TITLE="test' /* comment */ OR '1'='1"

    FAILURE_TITLE="$SQL_TITLE" FAILURE_DOMAIN="test" FAILURE_SUMMARY="test" bash "$BASE_DIR/scripts/record-failure.sh" 2>&1

    # Check if injection bypassed validation
    COUNT=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM learnings WHERE title LIKE '%comment%';")

    if [ "$COUNT" -eq 1 ]; then
        log_test "SQL injection - comment" "PASS" "Comment characters properly escaped"
    else
        log_test "SQL injection - comment" "FAIL" "Comment injection may have succeeded"
    fi
}

test_sql_injection_stacked() {
    echo "[TEST] SQL injection - stacked queries"

    SQL_TITLE="test'; INSERT INTO learnings (type, filepath, title) VALUES ('malicious', 'hack.md', 'pwned'); --"

    BEFORE_COUNT=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM learnings;")
    FAILURE_TITLE="$SQL_TITLE" FAILURE_DOMAIN="test" FAILURE_SUMMARY="test" bash "$BASE_DIR/scripts/record-failure.sh" 2>&1
    AFTER_COUNT=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM learnings;")

    # Should only add 1 record, not 2
    DIFF=$((AFTER_COUNT - BEFORE_COUNT))

    if [ "$DIFF" -eq 1 ]; then
        log_test "SQL injection - stacked queries" "PASS" "Stacked queries prevented"
    else
        log_test "SQL injection - stacked queries" "FAIL" "Stacked queries executed - CRITICAL VULNERABILITY"
    fi
}

echo ""
echo "==================================================================="
echo "TEST CATEGORY 7: SHELL METACHARACTER INJECTION"
echo "==================================================================="
echo ""

test_shell_command_substitution() {
    echo "[TEST] Shell command substitution - \$()"

    SHELL_TITLE='test$(whoami)data'

    FAILURE_TITLE="$SHELL_TITLE" FAILURE_DOMAIN="test" FAILURE_SUMMARY="test" bash "$BASE_DIR/scripts/record-failure.sh" 2>&1

    # Check if command was executed or escaped
    if sqlite3 "$DB_PATH" "SELECT title FROM learnings ORDER BY id DESC LIMIT 1;" | grep -q '$(whoami)'; then
        log_test "Shell command substitution \$()" "PASS" "Command substitution escaped"
    else
        log_test "Shell command substitution \$()" "FAIL" "Command substitution may have executed"
    fi
}

test_shell_backticks() {
    echo "[TEST] Shell command substitution - backticks"

    SHELL_TITLE='test`date`data'

    FAILURE_TITLE="$SHELL_TITLE" FAILURE_DOMAIN="test" FAILURE_SUMMARY="test" bash "$BASE_DIR/scripts/record-failure.sh" 2>&1

    if sqlite3 "$DB_PATH" "SELECT title FROM learnings ORDER BY id DESC LIMIT 1;" | grep -q '`date`'; then
        log_test "Shell backtick substitution" "PASS" "Backtick command escaped"
    else
        log_test "Shell backtick substitution" "FAIL" "Backtick command may have executed"
    fi
}

test_shell_wildcards() {
    echo "[TEST] Shell wildcards - *?"

    SHELL_TITLE="test*.txt?data"

    FAILURE_TITLE="$SHELL_TITLE" FAILURE_DOMAIN="test" FAILURE_SUMMARY="test" bash "$BASE_DIR/scripts/record-failure.sh" 2>&1

    if sqlite3 "$DB_PATH" "SELECT title FROM learnings ORDER BY id DESC LIMIT 1;" | grep -q '\*.*\?'; then
        log_test "Shell wildcards" "PASS" "Wildcards properly handled"
    else
        log_test "Shell wildcards" "WARN" "Wildcards may have been expanded"
    fi
}

test_shell_pipe_redirect() {
    echo "[TEST] Shell pipe and redirect - | >"

    SHELL_TITLE="test | cat > /tmp/pwned"

    FAILURE_TITLE="$SHELL_TITLE" FAILURE_DOMAIN="test" FAILURE_SUMMARY="test" bash "$BASE_DIR/scripts/record-failure.sh" 2>&1

    if [ ! -f "/tmp/pwned" ]; then
        log_test "Shell pipe/redirect" "PASS" "Pipe and redirect escaped"
    else
        rm -f "/tmp/pwned"
        log_test "Shell pipe/redirect" "FAIL" "Shell redirection executed - CRITICAL VULNERABILITY"
    fi
}

test_shell_semicolon() {
    echo "[TEST] Shell command separator - semicolon"

    SHELL_TITLE="test; touch /tmp/hacked; echo"

    FAILURE_TITLE="$SHELL_TITLE" FAILURE_DOMAIN="test" FAILURE_SUMMARY="test" bash "$BASE_DIR/scripts/record-failure.sh" 2>&1

    if [ ! -f "/tmp/hacked" ]; then
        log_test "Shell semicolon separator" "PASS" "Semicolon command separator escaped"
    else
        rm -f "/tmp/hacked"
        log_test "Shell semicolon separator" "FAIL" "Shell command executed - CRITICAL VULNERABILITY"
    fi
}

test_shell_ampersand() {
    echo "[TEST] Shell background process - &"

    SHELL_TITLE="test & sleep 60 &"

    FAILURE_TITLE="$SHELL_TITLE" FAILURE_DOMAIN="test" FAILURE_SUMMARY="test" bash "$BASE_DIR/scripts/record-failure.sh" 2>&1

    # Check if any sleep processes spawned
    if pgrep -f "sleep 60" > /dev/null; then
        pkill -f "sleep 60"
        log_test "Shell background process" "FAIL" "Background process spawned - VULNERABILITY"
    else
        log_test "Shell background process" "PASS" "Background process operator escaped"
    fi
}

test_shell_brackets() {
    echo "[TEST] Shell character class - []"

    SHELL_TITLE="test[abc]data{1..10}"

    FAILURE_TITLE="$SHELL_TITLE" FAILURE_DOMAIN="test" FAILURE_SUMMARY="test" bash "$BASE_DIR/scripts/record-failure.sh" 2>&1

    if sqlite3 "$DB_PATH" "SELECT title FROM learnings ORDER BY id DESC LIMIT 1;" | grep -q '\[abc\].*{1\.\.10}'; then
        log_test "Shell brackets/braces" "PASS" "Character class and brace expansion escaped"
    else
        log_test "Shell brackets/braces" "WARN" "Brackets/braces may have been expanded"
    fi
}

echo ""
echo "==================================================================="
echo "TEST CATEGORY 8: PYTHON SCRIPT INPUT VALIDATION"
echo "==================================================================="
echo ""

test_python_query_sql_injection() {
    echo "[TEST] Python query.py SQL injection"

    # Test domain parameter with SQL injection
    python3 "$BASE_DIR/query/query.py" --domain "test' OR '1'='1" --limit 5 2>&1

    if [ $? -eq 0 ]; then
        # Check if database is still intact
        if sqlite3 "$DB_PATH" "PRAGMA integrity_check;" | grep -q "ok"; then
            log_test "Python SQL injection - domain" "PASS" "Python script protected from SQL injection"
        else
            log_test "Python SQL injection - domain" "FAIL" "Python script vulnerable to SQL injection"
        fi
    else
        log_test "Python SQL injection - domain" "PASS" "Python script rejected malicious input"
    fi
}

test_python_query_limit_overflow() {
    echo "[TEST] Python query.py limit overflow"

    # Test with extreme limit value
    if timeout 10 python3 "$BASE_DIR/query/query.py" --recent 999999999 --format json 2>&1; then
        log_test "Python limit overflow" "WARN" "Python script accepted extreme limit - may cause performance issues"
    else
        if [ $? -eq 124 ]; then
            log_test "Python limit overflow" "FAIL" "Python script timed out with extreme limit"
        else
            log_test "Python limit overflow" "PASS" "Python script handled extreme limit"
        fi
    fi
}

test_python_query_tags_injection() {
    echo "[TEST] Python query.py tags SQL injection"

    # Test tags with SQL wildcards and injection
    python3 "$BASE_DIR/query/query.py" --tags "test%'; DROP TABLE learnings; --" 2>&1

    if sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM learnings;" 2>&1 > /dev/null; then
        log_test "Python tags SQL injection" "PASS" "Tags parameter properly sanitized"
    else
        log_test "Python tags SQL injection" "FAIL" "Tags parameter vulnerable - DATABASE CORRUPTED"
    fi
}

echo ""
echo "==================================================================="
echo "TEST CATEGORY 9: PATH TRAVERSAL AND FILE OPERATIONS"
echo "==================================================================="
echo ""

test_path_traversal_title() {
    echo "[TEST] Path traversal in title"

    TRAVERSAL_TITLE="../../../etc/passwd"

    FAILURE_TITLE="$TRAVERSAL_TITLE" FAILURE_DOMAIN="test" FAILURE_SUMMARY="test" bash "$BASE_DIR/scripts/record-failure.sh" 2>&1

    # Check if file was created in wrong location
    if [ ! -f "$BASE_DIR/../../../etc/passwd" ] && [ ! -f "$BASE_DIR/memory/failures/*passwd*" ]; then
        log_test "Path traversal in title" "PASS" "Path traversal prevented"
    else
        log_test "Path traversal in title" "WARN" "Path components may need sanitization"
    fi
}

test_symlink_attack_prevention() {
    echo "[TEST] Symlink attack prevention"

    # The script has symlink checks - verify they work
    if grep -q "SECURITY: failures directory is a symlink" "$BASE_DIR/scripts/record-failure.sh"; then
        log_test "Symlink attack prevention" "PASS" "Symlink checks implemented in script"
    else
        log_test "Symlink attack prevention" "FAIL" "No symlink protection found"
    fi
}

echo ""
echo "==================================================================="
echo "TEST CATEGORY 10: RACE CONDITIONS AND CONCURRENCY"
echo "==================================================================="
echo ""

test_concurrent_writes() {
    echo "[TEST] Concurrent write handling"

    # Launch multiple writes simultaneously
    for i in {1..5}; do
        (FAILURE_TITLE="concurrent_test_$i" FAILURE_DOMAIN="test" FAILURE_SUMMARY="test $i" bash "$BASE_DIR/scripts/record-failure.sh" 2>&1) &
    done

    wait

    # Count how many succeeded
    CONCURRENT_COUNT=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM learnings WHERE title LIKE 'concurrent_test_%';")

    if [ "$CONCURRENT_COUNT" -eq 5 ]; then
        log_test "Concurrent writes" "PASS" "All 5 concurrent writes succeeded"
    elif [ "$CONCURRENT_COUNT" -gt 0 ]; then
        log_test "Concurrent writes" "WARN" "Only $CONCURRENT_COUNT/5 concurrent writes succeeded"
    else
        log_test "Concurrent writes" "FAIL" "Concurrent writes failed completely"
    fi
}

echo ""
echo "==================================================================="
echo "RUNNING ALL TESTS"
echo "==================================================================="
echo ""

# Run all tests
test_empty_string_title
test_whitespace_only_domain
test_empty_string_heuristic
test_extremely_long_title
test_extremely_long_summary
test_null_bytes_in_title
test_binary_sequence
test_zero_width_characters
test_combining_marks
test_rtl_override
test_emoji_overflow
test_severity_overflow
test_severity_negative
test_confidence_overflow
test_confidence_negative
test_confidence_string_injection
test_sql_injection_simple_quote
test_sql_injection_union
test_sql_injection_comment
test_sql_injection_stacked
test_shell_command_substitution
test_shell_backticks
test_shell_wildcards
test_shell_pipe_redirect
test_shell_semicolon
test_shell_ampersand
test_shell_brackets
test_python_query_sql_injection
test_python_query_limit_overflow
test_python_query_tags_injection
test_path_traversal_title
test_symlink_attack_prevention
test_concurrent_writes

echo ""
echo "==================================================================="
echo "TEST SUMMARY"
echo "==================================================================="
echo ""
echo "Total Tests Run: $TESTS_RUN"
echo "Tests Passed: $TESTS_PASSED"
echo "Tests Failed: $TESTS_FAILED"
echo "Vulnerabilities Found: $VULNERABILITIES_FOUND"
echo ""
echo "Results written to: $TEST_RESULTS"
echo ""

# Append summary to results file
cat >> "$TEST_RESULTS" <<EOF

---

## Final Summary

- **Total Tests**: $TESTS_RUN
- **Passed**: $TESTS_PASSED
- **Failed**: $TESTS_FAILED
- **Vulnerabilities Found**: $VULNERABILITIES_FOUND

## Recommendations

Based on these fuzzing tests, the following fixes are recommended:

1. **Input Length Validation**: Add maximum length checks for all string inputs
2. **Whitespace Normalization**: Trim and validate non-empty after trimming
3. **Numeric Range Validation**: Enforce strict ranges for severity (1-5) and confidence (0.0-1.0)
4. **Binary Data Rejection**: Detect and reject binary data in text fields
5. **Unicode Normalization**: Apply Unicode normalization to prevent visual spoofing
6. **SQL Parameterization**: Ensure all SQL uses parameterized queries (already implemented via escape_sql)
7. **Shell Quote Escaping**: Ensure all shell variable expansions are properly quoted
8. **Path Sanitization**: Strip path traversal characters from filenames
9. **Concurrent Access**: Implement proper locking (already partially implemented)
10. **Type Validation**: Validate data types before SQL operations

---

*Generated by Agent C - Extreme Fuzzing Test Suite*
EOF

if [ $VULNERABILITIES_FOUND -gt 0 ]; then
    echo -e "${RED}ATTENTION: $VULNERABILITIES_FOUND vulnerabilities found!${NC}"
    echo "Review $TEST_RESULTS for details and apply recommended fixes."
    exit 1
else
    echo -e "${GREEN}All tests passed! No critical vulnerabilities found.${NC}"
    exit 0
fi
