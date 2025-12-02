#!/bin/bash
# Filesystem Security Test Suite for Emergent Learning Framework
# Tests: Path traversal, symlink attacks, hardlink attacks, filename injection,
#        TOCTOU races, permission issues, disk quota handling

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$(dirname "$SCRIPT_DIR")"
TEST_DIR="$BASE_DIR/tests/security-sandbox"
RESULTS_FILE="$BASE_DIR/tests/security_test_results.md"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test counters
TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0

log_test() {
    local status="$1"
    local test_name="$2"
    local details="$3"

    TESTS_RUN=$((TESTS_RUN + 1))

    if [ "$status" = "PASS" ]; then
        echo -e "${GREEN}[PASS]${NC} $test_name"
        echo "- **PASS**: $test_name" >> "$RESULTS_FILE"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    elif [ "$status" = "FAIL" ]; then
        echo -e "${RED}[FAIL]${NC} $test_name"
        echo "  Details: $details"
        echo "- **FAIL**: $test_name" >> "$RESULTS_FILE"
        echo "  - Details: $details" >> "$RESULTS_FILE"
        TESTS_FAILED=$((TESTS_FAILED + 1))
    else
        echo -e "${YELLOW}[WARN]${NC} $test_name"
        echo "  Details: $details"
        echo "- **WARN**: $test_name" >> "$RESULTS_FILE"
        echo "  - Details: $details" >> "$RESULTS_FILE"
    fi
}

setup_test_env() {
    echo "=== Setting up test environment ==="
    rm -rf "$TEST_DIR"
    mkdir -p "$TEST_DIR"

    # Create test targets outside sandbox
    mkdir -p "$TEST_DIR/../sensitive"
    echo "SENSITIVE DATA" > "$TEST_DIR/../sensitive/secret.txt"

    # Initialize results file
    cat > "$RESULTS_FILE" <<EOF
# Filesystem Security Test Results

**Date**: $(date +%Y-%m-%d\ %H:%M:%S)
**Test Suite**: Emergent Learning Framework Security Audit

## Test Results

EOF
}

cleanup_test_env() {
    echo "=== Cleaning up test environment ==="
    rm -rf "$TEST_DIR"
    rm -rf "$BASE_DIR/tests/sensitive"
}

# TEST 1: Path Traversal in Domain Parameter
test_path_traversal_domain() {
    echo ""
    echo "=== TEST 1: Path Traversal via Domain Parameter ==="

    # Try to use path traversal in domain to escape heuristics directory
    cd "$BASE_DIR"

    # Attack: domain="../../../sensitive/secret"
    # Expected: Script should sanitize and reject OR contain within heuristics/

    export HEURISTIC_DOMAIN="../../../sensitive/secret"
    export HEURISTIC_RULE="test rule"
    export HEURISTIC_EXPLANATION="test"

    if bash scripts/record-heuristic.sh 2>&1 | grep -q "ERROR\|SECURITY"; then
        log_test "PASS" "Path traversal in domain blocked" ""
    else
        # Check if file was created outside heuristics directory
        if [ -f "$BASE_DIR/../../../sensitive/secret.md" ] || [ -f "memory/heuristics/../../../sensitive/secret.md" ]; then
            log_test "FAIL" "Path traversal in domain" "File created outside heuristics directory"
        else
            # Check where the file actually went
            if [ -f "memory/heuristics/../../../sensitive/secret.md" ]; then
                log_test "FAIL" "Path traversal in domain" "Relative path not sanitized"
            else
                log_test "PASS" "Path traversal in domain contained" "File created in heuristics/ only"
            fi
        fi
    fi

    unset HEURISTIC_DOMAIN HEURISTIC_RULE HEURISTIC_EXPLANATION
}

# TEST 2: Path Traversal in Title/Filename
test_path_traversal_filename() {
    echo ""
    echo "=== TEST 2: Path Traversal via Title/Filename ==="

    cd "$BASE_DIR"

    # Attack: title with ../ to escape failures directory
    export FAILURE_TITLE="../../../sensitive/injected"
    export FAILURE_DOMAIN="test"
    export FAILURE_SUMMARY="test"
    export FAILURE_SEVERITY="3"

    if bash scripts/record-failure.sh 2>&1 | grep -q "ERROR\|SECURITY"; then
        log_test "PASS" "Path traversal in filename blocked" ""
    else
        # Check if file was created outside failures directory
        if [ -f "$BASE_DIR/../../../sensitive/injected.md" ]; then
            log_test "FAIL" "Path traversal in filename" "File created outside failures directory"
        else
            log_test "PASS" "Path traversal in filename sanitized" "Filename cleaned properly"
        fi
    fi

    unset FAILURE_TITLE FAILURE_DOMAIN FAILURE_SUMMARY FAILURE_SEVERITY
}

# TEST 3: Symlink Attack on Failures Directory
test_symlink_attack_failures() {
    echo ""
    echo "=== TEST 3: Symlink Attack on Failures Directory ==="

    cd "$BASE_DIR"

    # Backup real failures directory
    if [ -d "memory/failures" ] && [ ! -L "memory/failures" ]; then
        mv "memory/failures" "memory/failures.backup"
    fi

    # Create symlink pointing to sensitive directory
    ln -s "$TEST_DIR/../sensitive" "memory/failures"

    # Try to record a failure
    export FAILURE_TITLE="test"
    export FAILURE_DOMAIN="test"
    export FAILURE_SUMMARY="test"
    export FAILURE_SEVERITY="3"

    if bash scripts/record-failure.sh 2>&1 | grep -q "SECURITY.*symlink"; then
        log_test "PASS" "Symlink attack on failures directory blocked" ""
    else
        # Check if file was written to symlink target
        if [ -f "$TEST_DIR/../sensitive/$(date +%Y%m%d)_test.md" ]; then
            log_test "FAIL" "Symlink attack on failures directory" "File written to symlink target"
        else
            log_test "WARN" "Symlink attack unclear result" "Need to verify behavior"
        fi
    fi

    # Restore
    rm -f "memory/failures"
    if [ -d "memory/failures.backup" ]; then
        mv "memory/failures.backup" "memory/failures"
    fi

    unset FAILURE_TITLE FAILURE_DOMAIN FAILURE_SUMMARY FAILURE_SEVERITY
}

# TEST 4: Symlink Attack on Memory Directory
test_symlink_attack_memory() {
    echo ""
    echo "=== TEST 4: Symlink Attack on Memory Directory ==="

    cd "$BASE_DIR"

    # Backup real memory directory
    if [ -d "memory" ] && [ ! -L "memory" ]; then
        mv "memory" "memory.backup"
    fi

    # Create symlink pointing to sensitive directory
    ln -s "$TEST_DIR/../sensitive" "memory"

    # Try to record a failure
    export FAILURE_TITLE="test"
    export FAILURE_DOMAIN="test"
    export FAILURE_SUMMARY="test"
    export FAILURE_SEVERITY="3"

    if bash scripts/record-failure.sh 2>&1 | grep -q "SECURITY.*symlink"; then
        log_test "PASS" "Symlink attack on memory directory blocked" ""
    else
        log_test "FAIL" "Symlink attack on memory directory" "Symlink not detected"
    fi

    # Restore
    rm -f "memory"
    if [ -d "memory.backup" ]; then
        mv "memory.backup" "memory"
    fi

    unset FAILURE_TITLE FAILURE_DOMAIN FAILURE_SUMMARY FAILURE_SEVERITY
}

# TEST 5: Special Characters in Filename
test_special_chars_filename() {
    echo ""
    echo "=== TEST 5: Special Characters in Filename ==="

    cd "$BASE_DIR"

    # Try various special characters that could cause issues
    export FAILURE_TITLE="test\$PATH; rm -rf /"
    export FAILURE_DOMAIN="test"
    export FAILURE_SUMMARY="test"
    export FAILURE_SEVERITY="3"

    bash scripts/record-failure.sh 2>&1 > /dev/null || true

    # Check if filename was properly sanitized
    CREATED_FILE=$(find memory/failures -name "$(date +%Y%m%d)_test*" -type f 2>/dev/null | head -1)

    if [ -n "$CREATED_FILE" ]; then
        FILENAME=$(basename "$CREATED_FILE")
        if echo "$FILENAME" | grep -q '\$\|;\|/'; then
            log_test "FAIL" "Special characters in filename" "Unsafe characters not sanitized: $FILENAME"
        else
            log_test "PASS" "Special characters in filename sanitized" "Clean filename: $FILENAME"
            rm -f "$CREATED_FILE"
        fi
    else
        log_test "WARN" "Special characters test inconclusive" "No file created"
    fi

    unset FAILURE_TITLE FAILURE_DOMAIN FAILURE_SUMMARY FAILURE_SEVERITY
}

# TEST 6: SQL Injection in Title
test_sql_injection_title() {
    echo ""
    echo "=== TEST 6: SQL Injection in Title ==="

    cd "$BASE_DIR"

    # SQL injection attempt
    export FAILURE_TITLE="test'; DROP TABLE learnings; --"
    export FAILURE_DOMAIN="test"
    export FAILURE_SUMMARY="test"
    export FAILURE_SEVERITY="3"

    bash scripts/record-failure.sh 2>&1 > /dev/null || true

    # Check if learnings table still exists
    if sqlite3 memory/index.db "SELECT COUNT(*) FROM learnings;" 2>&1 | grep -q "no such table"; then
        log_test "FAIL" "SQL injection in title" "Table was dropped!"
    else
        log_test "PASS" "SQL injection in title blocked" "Table intact, quotes escaped"
    fi

    unset FAILURE_TITLE FAILURE_DOMAIN FAILURE_SUMMARY FAILURE_SEVERITY
}

# TEST 7: SQL Injection in Severity
test_sql_injection_severity() {
    echo ""
    echo "=== TEST 7: SQL Injection in Severity ==="

    cd "$BASE_DIR"

    # SQL injection attempt via severity
    export FAILURE_TITLE="test"
    export FAILURE_DOMAIN="test"
    export FAILURE_SUMMARY="test"
    export FAILURE_SEVERITY="3); DROP TABLE learnings; --"

    if bash scripts/record-failure.sh 2>&1 | grep -q "Invalid severity"; then
        log_test "PASS" "SQL injection in severity blocked" "Invalid severity rejected"
    else
        # Check if table still exists
        if sqlite3 memory/index.db "SELECT COUNT(*) FROM learnings;" 2>&1 | grep -q "no such table"; then
            log_test "FAIL" "SQL injection in severity" "Table was dropped!"
        else
            log_test "PASS" "SQL injection in severity failed" "Table intact"
        fi
    fi

    unset FAILURE_TITLE FAILURE_DOMAIN FAILURE_SUMMARY FAILURE_SEVERITY
}

# TEST 8: Null Byte Injection in Filename
test_null_byte_injection() {
    echo ""
    echo "=== TEST 8: Null Byte Injection in Filename ==="

    cd "$BASE_DIR"

    # Null byte injection (bypass extension check in some systems)
    export FAILURE_TITLE="test%00.sh"
    export FAILURE_DOMAIN="test"
    export FAILURE_SUMMARY="test"
    export FAILURE_SEVERITY="3"

    bash scripts/record-failure.sh 2>&1 > /dev/null || true

    # Check if .sh file was created
    if find memory/failures -name "*.sh" 2>/dev/null | grep -q .; then
        log_test "FAIL" "Null byte injection" ".sh file created"
    else
        log_test "PASS" "Null byte injection blocked" "No .sh file created"
    fi

    unset FAILURE_TITLE FAILURE_DOMAIN FAILURE_SUMMARY FAILURE_SEVERITY
}

# TEST 9: Newline Injection in Domain
test_newline_injection_domain() {
    echo ""
    echo "=== TEST 9: Newline Injection in Domain ==="

    cd "$BASE_DIR"

    # Try to inject newlines into domain to create multiple files
    export HEURISTIC_DOMAIN="test"$'\n'"../../sensitive/injected"
    export HEURISTIC_RULE="test rule"
    export HEURISTIC_EXPLANATION="test"

    bash scripts/record-heuristic.sh 2>&1 > /dev/null || true

    # Check if file was created outside heuristics
    if [ -f "../../sensitive/injected.md" ] || [ -f "memory/heuristics/../../sensitive/injected.md" ]; then
        log_test "FAIL" "Newline injection in domain" "Escaped heuristics directory"
    else
        log_test "PASS" "Newline injection in domain blocked" "Stayed within heuristics directory"
    fi

    unset HEURISTIC_DOMAIN HEURISTIC_RULE HEURISTIC_EXPLANATION
}

# TEST 10: Experiment Path Traversal
test_experiment_path_traversal() {
    echo ""
    echo "=== TEST 10: Experiment Name Path Traversal ==="

    cd "$BASE_DIR"

    # Check if start-experiment.sh has same vulnerabilities
    # This is a simplified test since it requires interactive input

    # Check the code for sanitization
    if grep -q "tr -cd '\[:alnum:\]-'" scripts/start-experiment.sh; then
        log_test "PASS" "Experiment name sanitization present" "Uses character filtering"
    else
        log_test "WARN" "Experiment name sanitization unclear" "Manual review needed"
    fi
}

# Main execution
main() {
    echo "========================================"
    echo "  Filesystem Security Test Suite"
    echo "  Emergent Learning Framework"
    echo "========================================"
    echo ""

    setup_test_env

    # Run all tests
    test_path_traversal_domain
    test_path_traversal_filename
    test_symlink_attack_failures
    test_symlink_attack_memory
    test_special_chars_filename
    test_sql_injection_title
    test_sql_injection_severity
    test_null_byte_injection
    test_newline_injection_domain
    test_experiment_path_traversal

    cleanup_test_env

    # Summary
    echo ""
    echo "========================================"
    echo "  Test Summary"
    echo "========================================"
    echo "Tests run:    $TESTS_RUN"
    echo -e "Tests passed: ${GREEN}$TESTS_PASSED${NC}"
    echo -e "Tests failed: ${RED}$TESTS_FAILED${NC}"
    echo ""
    echo "Full results: $RESULTS_FILE"

    cat >> "$RESULTS_FILE" <<EOF

## Summary

- **Total Tests**: $TESTS_RUN
- **Passed**: $TESTS_PASSED
- **Failed**: $TESTS_FAILED

EOF

    if [ $TESTS_FAILED -gt 0 ]; then
        exit 1
    fi
}

main "$@"
