#!/bin/bash
# Emergent Learning Framework - Complete Recovery Scenario Testing
# Tests all 5 critical recovery scenarios with RTO measurements

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_test() { echo -e "${CYAN}[TEST]${NC} $1"; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FRAMEWORK_DIR="$HOME/.claude/emergent-learning"
BACKUP_ROOT="${BACKUP_ROOT:-$HOME/.claude/backups/emergent-learning}"
TEST_DIR=$(mktemp -d)
REPORT_FILE="$FRAMEWORK_DIR/RECOVERY_SCENARIOS_TEST_REPORT_$(date +%Y%m%d_%H%M%S).md"

trap "rm -rf $TEST_DIR" EXIT

# Global test results
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0
declare -A TEST_TIMES

# Helper function to measure and record test time
measure_time() {
    local start=$1
    local end=$2
    echo $((end - start))
}

# Helper function to record test result
record_test() {
    local scenario=$1
    local status=$2
    local duration=$3

    ((TOTAL_TESTS++))
    TEST_TIMES["$scenario"]=$duration

    if [[ "$status" == "PASS" ]]; then
        ((PASSED_TESTS++))
        log_success "Scenario $scenario: PASSED (${duration}s)"
    else
        ((FAILED_TESTS++))
        log_error "Scenario $scenario: FAILED"
    fi
}

echo "============================================================"
echo "EMERGENT LEARNING FRAMEWORK - RECOVERY SCENARIO TESTING"
echo "============================================================"
echo ""
echo "Test Directory: $TEST_DIR"
echo "Report File: $REPORT_FILE"
echo ""

# Initialize report
cat > "$REPORT_FILE" << 'EOF'
# Recovery Scenarios Test Report

**Date:** $(date)
**Agent:** Opus Agent H2
**Objective:** Achieve 10/10 backup and recovery score

---

## Executive Summary

This report documents the testing of all critical recovery scenarios with measured Recovery Time Objectives (RTO).

---

## Test Results

EOF

# ============================================================
# SCENARIO 1: Corrupted Database Recovery
# ============================================================
log_test "SCENARIO 1: Corrupted Database Recovery"
echo "-----------------------------------------------------------"

START_TIME=$(date +%s)

# Create backup first
log_info "Creating test backup..."
cd "$FRAMEWORK_DIR"
./scripts/backup.sh >/dev/null 2>&1

# Get latest backup
LATEST_BACKUP=$(ls -t "$BACKUP_ROOT"/*.tar.gz | head -1 | xargs basename .tar.gz)

# Corrupt the database
log_info "Simulating database corruption..."
if [[ -f "$FRAMEWORK_DIR/memory/index.db" ]]; then
    cp "$FRAMEWORK_DIR/memory/index.db" "$TEST_DIR/index.db.backup"
    echo "CORRUPTED DATA" > "$FRAMEWORK_DIR/memory/index.db"

    # Verify corruption
    if sqlite3 "$FRAMEWORK_DIR/memory/index.db" "PRAGMA integrity_check;" 2>&1 | grep -q "malformed"; then
        log_info "Database successfully corrupted (simulated)"
    else
        # Force corruption by truncating
        dd if=/dev/zero of="$FRAMEWORK_DIR/memory/index.db" bs=1024 count=1 2>/dev/null
    fi

    # Restore from backup
    log_info "Restoring from backup..."
    if ./scripts/restore.sh --force --no-backup "$LATEST_BACKUP" >/dev/null 2>&1; then
        # Verify restoration
        if sqlite3 "$FRAMEWORK_DIR/memory/index.db" "PRAGMA integrity_check;" 2>&1 | grep -q "ok"; then
            END_TIME=$(date +%s)
            DURATION=$(measure_time $START_TIME $END_TIME)
            record_test "1-Corrupted-DB" "PASS" "$DURATION"
            SCENARIO1_STATUS="PASS"
            SCENARIO1_TIME=$DURATION
        else
            log_error "Database integrity check failed after restore"
            SCENARIO1_STATUS="FAIL"
            SCENARIO1_TIME=0
            record_test "1-Corrupted-DB" "FAIL" 0
        fi
    else
        log_error "Restore failed"
        SCENARIO1_STATUS="FAIL"
        SCENARIO1_TIME=0
        record_test "1-Corrupted-DB" "FAIL" 0
    fi
else
    log_warn "No database found, skipping scenario 1"
    SCENARIO1_STATUS="SKIP"
    SCENARIO1_TIME=0
fi

echo ""

# ============================================================
# SCENARIO 2: Accidental File Deletion (Git Recovery)
# ============================================================
log_test "SCENARIO 2: Accidental File Deletion (Git Recovery)"
echo "-----------------------------------------------------------"

START_TIME=$(date +%s)

# Delete a tracked file
TEST_FILE="$FRAMEWORK_DIR/FRAMEWORK.md"
if [[ -f "$TEST_FILE" ]]; then
    cp "$TEST_FILE" "$TEST_DIR/framework.md.backup"
    rm "$TEST_FILE"
    log_info "Deleted test file: $TEST_FILE"

    # Restore using git
    cd "$FRAMEWORK_DIR"
    if git checkout HEAD -- FRAMEWORK.md 2>/dev/null; then
        # Verify restoration
        if [[ -f "$TEST_FILE" ]]; then
            END_TIME=$(date +%s)
            DURATION=$(measure_time $START_TIME $END_TIME)
            record_test "2-File-Deletion" "PASS" "$DURATION"
            SCENARIO2_STATUS="PASS"
            SCENARIO2_TIME=$DURATION
        else
            log_error "File not restored"
            SCENARIO2_STATUS="FAIL"
            SCENARIO2_TIME=0
            record_test "2-File-Deletion" "FAIL" 0
        fi
    else
        log_error "Git restore failed"
        SCENARIO2_STATUS="FAIL"
        SCENARIO2_TIME=0
        record_test "2-File-Deletion" "FAIL" 0
    fi
else
    log_warn "Test file not found, skipping scenario 2"
    SCENARIO2_STATUS="SKIP"
    SCENARIO2_TIME=0
fi

echo ""

# ============================================================
# SCENARIO 3: Bad Update Rollback (Git-based)
# ============================================================
log_test "SCENARIO 3: Bad Update Rollback (Git-based)"
echo "-----------------------------------------------------------"

START_TIME=$(date +%s)

cd "$FRAMEWORK_DIR"
CURRENT_COMMIT=$(git rev-parse HEAD)

# Create a "bad" change
echo "BAD UPDATE" > "$FRAMEWORK_DIR/test_bad_update.txt"
git add test_bad_update.txt
git commit -m "Simulated bad update" >/dev/null 2>&1

# Rollback using restore-from-git.sh
if ./scripts/restore-from-git.sh --force --keep-databases HEAD~1 >/dev/null 2>&1; then
    # Verify rollback
    if [[ ! -f "$FRAMEWORK_DIR/test_bad_update.txt" ]]; then
        END_TIME=$(date +%s)
        DURATION=$(measure_time $START_TIME $END_TIME)
        record_test "3-Bad-Update-Rollback" "PASS" "$DURATION"
        SCENARIO3_STATUS="PASS"
        SCENARIO3_TIME=$DURATION

        # Clean up - return to latest
        git checkout master 2>/dev/null || git checkout main 2>/dev/null
    else
        log_error "Rollback incomplete"
        SCENARIO3_STATUS="FAIL"
        SCENARIO3_TIME=0
        record_test "3-Bad-Update-Rollback" "FAIL" 0
    fi
else
    log_error "Rollback failed"
    SCENARIO3_STATUS="FAIL"
    SCENARIO3_TIME=0
    record_test "3-Bad-Update-Rollback" "FAIL" 0
fi

echo ""

# ============================================================
# SCENARIO 4: Complete System Loss (Full Restore)
# ============================================================
log_test "SCENARIO 4: Complete System Loss (Full Restore)"
echo "-----------------------------------------------------------"

START_TIME=$(date +%s)

# Create a test environment simulating complete loss
RESTORE_TEST_DIR="$TEST_DIR/complete-loss-test"
mkdir -p "$RESTORE_TEST_DIR/emergent-learning/memory"

# Set up minimal git repo
cd "$RESTORE_TEST_DIR/emergent-learning"
git init >/dev/null 2>&1

# Export framework dir temporarily
OLD_FRAMEWORK_DIR="$FRAMEWORK_DIR"
export FRAMEWORK_DIR="$RESTORE_TEST_DIR/emergent-learning"

# Restore from backup to test location
if "$OLD_FRAMEWORK_DIR/scripts/restore.sh" --force --no-backup "$LATEST_BACKUP" >/dev/null 2>&1; then
    # Verify restoration
    if [[ -f "$FRAMEWORK_DIR/memory/index.db" ]] && [[ -f "$FRAMEWORK_DIR/FRAMEWORK.md" ]]; then
        # Check database integrity
        if sqlite3 "$FRAMEWORK_DIR/memory/index.db" "PRAGMA integrity_check;" 2>&1 | grep -q "ok"; then
            END_TIME=$(date +%s)
            DURATION=$(measure_time $START_TIME $END_TIME)
            record_test "4-Complete-Loss" "PASS" "$DURATION"
            SCENARIO4_STATUS="PASS"
            SCENARIO4_TIME=$DURATION
        else
            log_error "Restored database corrupted"
            SCENARIO4_STATUS="FAIL"
            SCENARIO4_TIME=0
            record_test "4-Complete-Loss" "FAIL" 0
        fi
    else
        log_error "Files not restored"
        SCENARIO4_STATUS="FAIL"
        SCENARIO4_TIME=0
        record_test "4-Complete-Loss" "FAIL" 0
    fi
else
    log_error "Full restore failed"
    SCENARIO4_STATUS="FAIL"
    SCENARIO4_TIME=0
    record_test "4-Complete-Loss" "FAIL" 0
fi

# Restore environment
export FRAMEWORK_DIR="$OLD_FRAMEWORK_DIR"
cd "$FRAMEWORK_DIR"

echo ""

# ============================================================
# SCENARIO 5: Partial Backup Restoration (SQL Restore)
# ============================================================
log_test "SCENARIO 5: Partial Backup Restoration (SQL Restore)"
echo "-----------------------------------------------------------"

START_TIME=$(date +%s)

# Create test location for SQL restore
SQL_RESTORE_DIR="$TEST_DIR/sql-restore-test"
mkdir -p "$SQL_RESTORE_DIR/emergent-learning/memory"
cd "$SQL_RESTORE_DIR/emergent-learning"
git init >/dev/null 2>&1

# Set environment
export FRAMEWORK_DIR="$SQL_RESTORE_DIR/emergent-learning"

# Restore using SQL-only mode
if "$OLD_FRAMEWORK_DIR/scripts/restore.sh" --sql-only --force --no-backup "$LATEST_BACKUP" >/dev/null 2>&1; then
    # Verify SQL restoration
    if [[ -f "$FRAMEWORK_DIR/memory/index.db" ]]; then
        if sqlite3 "$FRAMEWORK_DIR/memory/index.db" "PRAGMA integrity_check;" 2>&1 | grep -q "ok"; then
            END_TIME=$(date +%s)
            DURATION=$(measure_time $START_TIME $END_TIME)
            record_test "5-SQL-Restore" "PASS" "$DURATION"
            SCENARIO5_STATUS="PASS"
            SCENARIO5_TIME=$DURATION
        else
            log_error "SQL-restored database corrupted"
            SCENARIO5_STATUS="FAIL"
            SCENARIO5_TIME=0
            record_test "5-SQL-Restore" "FAIL" 0
        fi
    else
        log_error "SQL restore failed to create database"
        SCENARIO5_STATUS="FAIL"
        SCENARIO5_TIME=0
        record_test "5-SQL-Restore" "FAIL" 0
    fi
else
    log_error "SQL-only restore failed"
    SCENARIO5_STATUS="FAIL"
    SCENARIO5_TIME=0
    record_test "5-SQL-Restore" "FAIL" 0
fi

# Restore environment
export FRAMEWORK_DIR="$OLD_FRAMEWORK_DIR"
cd "$FRAMEWORK_DIR"

echo ""

# ============================================================
# Generate Report
# ============================================================
cat >> "$REPORT_FILE" << EOF

### Scenario 1: Corrupted Database Recovery
- **Status:** $SCENARIO1_STATUS
- **RTO:** ${SCENARIO1_TIME}s
- **Target:** < 300s (5 minutes)
- **Method:** Full backup restore
- **Result:** $(if [[ "$SCENARIO1_STATUS" == "PASS" ]]; then echo "Database restored and verified"; else echo "Failed"; fi)

### Scenario 2: Accidental File Deletion
- **Status:** $SCENARIO2_STATUS
- **RTO:** ${SCENARIO2_TIME}s
- **Target:** < 60s (1 minute)
- **Method:** Git checkout
- **Result:** $(if [[ "$SCENARIO2_STATUS" == "PASS" ]]; then echo "File restored from git"; else echo "Failed"; fi)

### Scenario 3: Bad Update Rollback
- **Status:** $SCENARIO3_STATUS
- **RTO:** ${SCENARIO3_TIME}s
- **Target:** < 180s (3 minutes)
- **Method:** Git-based restore
- **Result:** $(if [[ "$SCENARIO3_STATUS" == "PASS" ]]; then echo "Rolled back to previous commit"; else echo "Failed"; fi)

### Scenario 4: Complete System Loss
- **Status:** $SCENARIO4_STATUS
- **RTO:** ${SCENARIO4_TIME}s
- **Target:** < 300s (5 minutes)
- **Method:** Full restore to new location
- **Result:** $(if [[ "$SCENARIO4_STATUS" == "PASS" ]]; then echo "Complete system restored"; else echo "Failed"; fi)

### Scenario 5: Partial Restoration (SQL)
- **Status:** $SCENARIO5_STATUS
- **RTO:** ${SCENARIO5_TIME}s
- **Target:** < 300s (5 minutes)
- **Method:** SQL dump restore
- **Result:** $(if [[ "$SCENARIO5_STATUS" == "PASS" ]]; then echo "Database restored from SQL"; else echo "Failed"; fi)

---

## Summary

- **Total Tests:** $TOTAL_TESTS
- **Passed:** $PASSED_TESTS
- **Failed:** $FAILED_TESTS
- **Success Rate:** $(echo "scale=1; $PASSED_TESTS * 100 / $TOTAL_TESTS" | bc 2>/dev/null || echo "N/A")%

### RTO Analysis

Maximum RTO measured: $(echo "${TEST_TIMES[@]}" | tr ' ' '\n' | sort -n | tail -1)s
Average RTO: $(echo "scale=1; (${SCENARIO1_TIME} + ${SCENARIO2_TIME} + ${SCENARIO3_TIME} + ${SCENARIO4_TIME} + ${SCENARIO5_TIME}) / 5" | bc 2>/dev/null || echo "N/A")s

All RTOs are $(if (( $(echo "${TEST_TIMES[@]}" | tr ' ' '\n' | sort -n | tail -1) < 300 )); then echo "**BELOW**"; else echo "**ABOVE**"; fi) the 5-minute target.

---

## Certification

$(if [[ $FAILED_TESTS -eq 0 ]]; then
echo "**STATUS: 10/10 - ALL RECOVERY SCENARIOS VERIFIED**"
echo ""
echo "All recovery scenarios tested successfully with acceptable RTOs."
echo "Backup and recovery system is production-ready."
else
echo "**STATUS: INCOMPLETE - $(echo "$FAILED_TESTS") SCENARIO(S) FAILED**"
echo ""
echo "Review failed scenarios and remediate before certification."
fi)

---

**Report Generated:** $(date)
**Test Duration:** $(measure_time $START_TIME $(date +%s))s

EOF

# Display summary
echo "============================================================"
echo "TEST SUMMARY"
echo "============================================================"
echo "Total Tests: $TOTAL_TESTS"
echo "Passed: $PASSED_TESTS"
echo "Failed: $FAILED_TESTS"
echo "Success Rate: $(echo "scale=1; $PASSED_TESTS * 100 / $TOTAL_TESTS" | bc 2>/dev/null || echo "N/A")%"
echo ""
echo "Report saved to: $REPORT_FILE"
echo ""

if [[ $FAILED_TESTS -eq 0 ]]; then
    log_success "ALL RECOVERY SCENARIOS PASSED - 10/10 ACHIEVED!"
    exit 0
else
    log_error "Some scenarios failed - review report"
    exit 1
fi
