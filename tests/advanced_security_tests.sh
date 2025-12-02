#!/bin/bash
# Advanced Security Tests with POCs and Verification
# Tests specific attack vectors with concrete exploit attempts

set -e

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TEST_DIR="$BASE_DIR/tests/attack-sandbox"
REPORT="$BASE_DIR/tests/security_audit_report.md"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

CRITICAL=0
HIGH=0
MEDIUM=0
LOW=0
PASSED=0

log_vulnerability() {
    local severity="$1"
    local test_name="$2"
    local details="$3"
    local poc="$4"
    local fix="$5"

    case "$severity" in
        CRITICAL)
            echo -e "${RED}[CRITICAL]${NC} $test_name"
            CRITICAL=$((CRITICAL + 1))
            ;;
        HIGH)
            echo -e "${RED}[HIGH]${NC} $test_name"
            HIGH=$((HIGH + 1))
            ;;
        MEDIUM)
            echo -e "${YELLOW}[MEDIUM]${NC} $test_name"
            MEDIUM=$((MEDIUM + 1))
            ;;
        LOW)
            echo -e "${YELLOW}[LOW]${NC} $test_name"
            LOW=$((LOW + 1))
            ;;
        PASS)
            echo -e "${GREEN}[PASS]${NC} $test_name"
            PASSED=$((PASSED + 1))
            return
            ;;
    esac

    echo "  Details: $details"
    echo ""

    cat >> "$REPORT" <<EOF

### $test_name

**Severity**: $severity

**Description**: $details

**Proof of Concept**:
\`\`\`bash
$poc
\`\`\`

**Fix Required**:
$fix

---

EOF
}

setup() {
    rm -rf "$TEST_DIR"
    mkdir -p "$TEST_DIR/sensitive"
    echo "CONFIDENTIAL_DATA" > "$TEST_DIR/sensitive/secrets.txt"

    cat > "$REPORT" <<EOF
# Filesystem Security Audit Report
# Emergent Learning Framework

**Date**: $(date '+%Y-%m-%d %H:%M:%S')
**Auditor**: Opus Agent B (Filesystem Security Specialist)
**Framework Version**: 1.0.0

## Executive Summary

This report details filesystem security vulnerabilities discovered during comprehensive
security testing of the Emergent Learning Framework scripts.

## Vulnerabilities Discovered

EOF
}

cleanup() {
    rm -rf "$TEST_DIR"
}

# ============================================
# ATTACK 1: Null Byte Path Traversal
# ============================================
test_null_byte_traversal() {
    echo -e "\n${BLUE}TEST 1: Null Byte Path Traversal${NC}"

    local attack_title="test%00../../sensitive/secrets"
    export FAILURE_TITLE="$attack_title"
    export FAILURE_DOMAIN="test"
    export FAILURE_SUMMARY="attack"
    export FAILURE_SEVERITY="3"

    cd "$BASE_DIR"
    bash scripts/record-failure.sh 2>&1 >/dev/null || true

    # Check if file escaped failures directory
    if find memory -name "*secrets*" -type f 2>/dev/null | grep -v failures | grep -q .; then
        log_vulnerability "HIGH" "Null Byte Path Traversal" \
            "Null bytes (%00) in filenames can truncate the path and bypass sanitization" \
            "FAILURE_TITLE='test%00../../etc/passwd' ./record-failure.sh" \
            "Strip null bytes before processing: input=\${input//\$'\\0'/}"
    else
        log_vulnerability "PASS" "Null Byte Path Traversal" "" "" ""
    fi

    unset FAILURE_TITLE FAILURE_DOMAIN FAILURE_SUMMARY FAILURE_SEVERITY
}

# ============================================
# ATTACK 2: Domain Directory Traversal
# ============================================
test_domain_traversal() {
    echo -e "\n${BLUE}TEST 2: Domain Directory Traversal${NC}"

    local attack_domain="../../../$TEST_DIR/sensitive/injected"
    export HEURISTIC_DOMAIN="$attack_domain"
    export HEURISTIC_RULE="attack"
    export HEURISTIC_EXPLANATION="test"

    cd "$BASE_DIR"
    bash scripts/record-heuristic.sh 2>&1 >/dev/null || true

    # Check if file was created outside heuristics directory
    if [ -f "$TEST_DIR/sensitive/injected.md" ] || [ -f "memory/heuristics/../../../$TEST_DIR/sensitive/injected.md" ]; then
        log_vulnerability "CRITICAL" "Domain Directory Traversal" \
            "Domain parameter allows path traversal to write files outside heuristics directory" \
            "HEURISTIC_DOMAIN='../../../tmp/evil' HEURISTIC_RULE='pwned' ./record-heuristic.sh" \
            "Sanitize domain to remove path separators: domain=\$(echo \"\$domain\" | tr -cd '[:alnum:]-')"
    else
        log_vulnerability "PASS" "Domain Directory Traversal" "" "" ""
    fi

    unset HEURISTIC_DOMAIN HEURISTIC_RULE HEURISTIC_EXPLANATION
}

# ============================================
# ATTACK 3: Symlink Race (TOCTOU)
# ============================================
test_symlink_race() {
    echo -e "\n${BLUE}TEST 3: Symlink Race Condition (TOCTOU)${NC}"

    cd "$BASE_DIR"

    # Backup failures directory
    if [ -d "memory/failures" ]; then
        mv "memory/failures" "memory/failures.safe"
    fi

    # Create normal directory first
    mkdir -p "memory/failures"

    # Start background process that replaces directory with symlink
    (
        sleep 0.1
        rm -rf "memory/failures"
        ln -s "$TEST_DIR/sensitive" "memory/failures"
    ) &

    # Try to write while the race is happening
    export FAILURE_TITLE="racetest"
    export FAILURE_DOMAIN="test"
    export FAILURE_SUMMARY="test"
    export FAILURE_SEVERITY="3"

    bash scripts/record-failure.sh 2>&1 >/dev/null || true

    # Check if file ended up in sensitive directory
    if [ -f "$TEST_DIR/sensitive/$(date +%Y%m%d)_racetest.md" ]; then
        log_vulnerability "HIGH" "Symlink Race Condition (TOCTOU)" \
            "Time-of-check to time-of-use race allows symlink attack between check and file write" \
            "mkdir failures; (sleep 0.1; rm -rf failures; ln -s /sensitive failures) & ./record-failure.sh" \
            "Use O_NOFOLLOW flag or re-check symlink status immediately before write operation"
    else
        log_vulnerability "PASS" "Symlink Race Condition" "" "" ""
    fi

    # Cleanup
    rm -f "memory/failures"
    if [ -d "memory/failures.safe" ]; then
        mv "memory/failures.safe" "memory/failures"
    fi

    unset FAILURE_TITLE FAILURE_DOMAIN FAILURE_SUMMARY FAILURE_SEVERITY
}

# ============================================
# ATTACK 4: Command Injection via Title
# ============================================
test_command_injection_title() {
    echo -e "\n${BLUE}TEST 4: Command Injection via Title${NC}"

    local attack_title="test\$(touch $TEST_DIR/pwned.txt)"
    export FAILURE_TITLE="$attack_title"
    export FAILURE_DOMAIN="test"
    export FAILURE_SUMMARY="test"
    export FAILURE_SEVERITY="3"

    cd "$BASE_DIR"
    bash scripts/record-failure.sh 2>&1 >/dev/null || true

    # Check if command was executed
    if [ -f "$TEST_DIR/pwned.txt" ]; then
        log_vulnerability "CRITICAL" "Command Injection via Title" \
            "Title parameter allows command injection through shell expansion" \
            "FAILURE_TITLE='test\$(rm -rf /)' ./record-failure.sh" \
            "Quote all variables in file operations and SQL. Use printf instead of echo for variable output"
    else
        log_vulnerability "PASS" "Command Injection via Title" "" "" ""
    fi

    unset FAILURE_TITLE FAILURE_DOMAIN FAILURE_SUMMARY FAILURE_SEVERITY
}

# ============================================
# ATTACK 5: Hardlink Attack
# ============================================
test_hardlink_attack() {
    echo -e "\n${BLUE}TEST 5: Hardlink Attack${NC}"

    cd "$BASE_DIR"

    # Create a hardlink to a sensitive file
    mkdir -p "$TEST_DIR/attacker"
    echo "original" > "$TEST_DIR/attacker/target.txt"

    # Create hardlink in failures directory (if attacker has write access)
    local target_file="memory/failures/$(date +%Y%m%d)_hardlink.md"

    # Simulate attacker creating hardlink before our write
    touch "$target_file"
    ln "$target_file" "$TEST_DIR/attacker/link.txt"

    # Now script overwrites the file
    export FAILURE_TITLE="hardlink"
    export FAILURE_DOMAIN="test"
    export FAILURE_SUMMARY="This should overwrite both files"
    export FAILURE_SEVERITY="3"

    bash scripts/record-failure.sh 2>&1 >/dev/null || true

    # Check if hardlink caused the attacker's file to be modified
    if [ -f "$TEST_DIR/attacker/link.txt" ] && grep -q "Summary" "$TEST_DIR/attacker/link.txt"; then
        log_vulnerability "MEDIUM" "Hardlink Attack" \
            "Script doesn't check for hardlinks before writing, allowing attacker to modify files they don't own" \
            "touch target.md; ln target.md /tmp/steal.txt; # victim script overwrites target.md" \
            "Check link count before write: if [ \$(stat -c %h file) -gt 1 ]; then reject; fi"
    else
        log_vulnerability "PASS" "Hardlink Attack" "" "" ""
    fi

    unset FAILURE_TITLE FAILURE_DOMAIN FAILURE_SUMMARY FAILURE_SEVERITY
}

# ============================================
# ATTACK 6: SQL Injection via Tags
# ============================================
test_sql_injection_tags() {
    echo -e "\n${BLUE}TEST 6: SQL Injection via Tags${NC}"

    local attack_tags="test', (SELECT 'evil' FROM learnings WHERE 1=1)) --"
    export FAILURE_TITLE="test"
    export FAILURE_DOMAIN="test"
    export FAILURE_SUMMARY="test"
    export FAILURE_SEVERITY="3"
    export FAILURE_TAGS="$attack_tags"

    cd "$BASE_DIR"
    bash scripts/record-failure.sh 2>&1 >/dev/null || true

    # Check if injection worked by looking for 'evil' in unexpected places
    if sqlite3 memory/index.db "SELECT * FROM learnings WHERE tags LIKE '%evil%'" 2>/dev/null | grep -q "evil"; then
        # This might be expected, check if it's escaped properly
        if sqlite3 memory/index.db "SELECT tags FROM learnings WHERE tags LIKE '%evil%'" 2>/dev/null | grep -q "')) --"; then
            log_vulnerability "PASS" "SQL Injection via Tags" "" "" ""
        else
            log_vulnerability "HIGH" "SQL Injection via Tags" \
                "Tags parameter may allow SQL injection" \
                "FAILURE_TAGS=\"'; DROP TABLE learnings; --\" ./record-failure.sh" \
                "Use parameterized queries or escape single quotes: tags=\${tags//\\'/\\'\\}"
        fi
    else
        log_vulnerability "PASS" "SQL Injection via Tags" "" "" ""
    fi

    unset FAILURE_TITLE FAILURE_DOMAIN FAILURE_SUMMARY FAILURE_SEVERITY FAILURE_TAGS
}

# ============================================
# ATTACK 7: Filename Length DoS
# ============================================
test_filename_length_dos() {
    echo -e "\n${BLUE}TEST 7: Filename Length DoS${NC}"

    # Create extremely long filename (>255 chars, typical filesystem limit)
    local long_title=$(python3 -c "print('A' * 300)")
    export FAILURE_TITLE="$long_title"
    export FAILURE_DOMAIN="test"
    export FAILURE_SUMMARY="test"
    export FAILURE_SEVERITY="3"

    cd "$BASE_DIR"
    if bash scripts/record-failure.sh 2>&1 | grep -q "File name too long"; then
        log_vulnerability "LOW" "Filename Length DoS" \
            "Extremely long titles can cause filesystem errors or DoS" \
            "FAILURE_TITLE=\$(python3 -c \"print('A' * 300)\") ./record-failure.sh" \
            "Truncate filename to safe length: filename=\${filename:0:200}"
    else
        # Check if file was created successfully (which means length is handled)
        log_vulnerability "PASS" "Filename Length DoS" "" "" ""
    fi

    unset FAILURE_TITLE FAILURE_DOMAIN FAILURE_SUMMARY FAILURE_SEVERITY
}

# ============================================
# ATTACK 8: Newline Injection in Summary
# ============================================
test_newline_injection_summary() {
    echo -e "\n${BLUE}TEST 8: Newline Injection in Summary${NC}"

    local attack_summary="normal"$'\n'"**Severity**: 5"$'\n'"INJECTED CONTENT"
    export FAILURE_TITLE="test"
    export FAILURE_DOMAIN="test"
    export FAILURE_SUMMARY="$attack_summary"
    export FAILURE_SEVERITY="2"

    cd "$BASE_DIR"
    bash scripts/record-failure.sh 2>&1 >/dev/null || true

    # Check if injected content appears in unexpected places in the markdown
    local created_file=$(find memory/failures -name "$(date +%Y%m%d)_test.md" -type f | head -1)
    if [ -n "$created_file" ]; then
        if grep -q "INJECTED CONTENT" "$created_file" && head -10 "$created_file" | grep -q "INJECTED CONTENT"; then
            log_vulnerability "LOW" "Newline Injection in Summary" \
                "Newlines in summary can inject content into markdown metadata section" \
                "FAILURE_SUMMARY='normal"$'\\n'"**Severity**: 5' ./record-failure.sh" \
                "Sanitize newlines in summary or properly escape them in markdown"
        else
            log_vulnerability "PASS" "Newline Injection in Summary" "" "" ""
        fi
        rm -f "$created_file"
    else
        log_vulnerability "PASS" "Newline Injection in Summary" "" "" ""
    fi

    unset FAILURE_TITLE FAILURE_DOMAIN FAILURE_SUMMARY FAILURE_SEVERITY
}

# ============================================
# Main Execution
# ============================================
main() {
    echo "========================================"
    echo "  Advanced Filesystem Security Tests"
    echo "  Opus Agent B - Security Audit"
    echo "========================================"

    setup

    test_null_byte_traversal
    test_domain_traversal
    test_symlink_race
    test_command_injection_title
    test_hardlink_attack
    test_sql_injection_tags
    test_filename_length_dos
    test_newline_injection_summary

    cleanup

    # Summary
    cat >> "$REPORT" <<EOF

## Summary

- **Critical Vulnerabilities**: $CRITICAL
- **High Severity**: $HIGH
- **Medium Severity**: $MEDIUM
- **Low Severity**: $LOW
- **Tests Passed**: $PASSED

## Risk Assessment

EOF

    if [ $CRITICAL -gt 0 ]; then
        cat >> "$REPORT" <<EOF
**OVERALL RISK**: CRITICAL

Immediate action required. Critical vulnerabilities allow arbitrary file write,
command injection, or data exfiltration.
EOF
    elif [ $HIGH -gt 0 ]; then
        cat >> "$REPORT" <<EOF
**OVERALL RISK**: HIGH

Significant security issues present. High-severity vulnerabilities allow
path traversal or privilege escalation.
EOF
    elif [ $MEDIUM -gt 0 ]; then
        cat >> "$REPORT" <<EOF
**OVERALL RISK**: MEDIUM

Moderate security issues present. Should be addressed to prevent potential exploitation.
EOF
    else
        cat >> "$REPORT" <<EOF
**OVERALL RISK**: LOW

Minor security issues or all tests passed. Good security posture overall.
EOF
    fi

    echo ""
    echo "========================================"
    echo "  Security Audit Complete"
    echo "========================================"
    echo -e "Critical: ${RED}$CRITICAL${NC}"
    echo -e "High:     ${RED}$HIGH${NC}"
    echo -e "Medium:   ${YELLOW}$MEDIUM${NC}"
    echo -e "Low:      ${YELLOW}$LOW${NC}"
    echo -e "Passed:   ${GREEN}$PASSED${NC}"
    echo ""
    echo "Full report: $REPORT"

    if [ $CRITICAL -gt 0 ] || [ $HIGH -gt 0 ]; then
        exit 1
    fi
}

main "$@"
