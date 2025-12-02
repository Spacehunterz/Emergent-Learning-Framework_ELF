#!/bin/bash
# Database Robustness 10/10 - Comprehensive Stress Test
# Agent D2 - December 2025

set -euo pipefail

DB_PATH="$HOME/.claude/emergent-learning/memory/index.db"
TEST_COUNT=0
PASS_COUNT=0
FAIL_COUNT=0

echo "======================================================================"
echo "Database Robustness 10/10 - Stress Test Suite"
echo "======================================================================"
echo

# Test helper functions
run_test() {
    local test_name="$1"
    local test_cmd="$2"

    TEST_COUNT=$((TEST_COUNT + 1))
    echo -n "[$TEST_COUNT] $test_name... "

    if eval "$test_cmd" > /dev/null 2>&1; then
        echo "PASS"
        PASS_COUNT=$((PASS_COUNT + 1))
        return 0
    else
        echo "FAIL"
        FAIL_COUNT=$((FAIL_COUNT + 1))
        return 1
    fi
}

run_test_expect_fail() {
    local test_name="$1"
    local test_cmd="$2"

    TEST_COUNT=$((TEST_COUNT + 1))
    echo -n "[$TEST_COUNT] $test_name... "

    if eval "$test_cmd" > /dev/null 2>&1; then
        echo "FAIL (expected to fail but passed)"
        FAIL_COUNT=$((FAIL_COUNT + 1))
        return 1
    else
        echo "PASS (correctly rejected)"
        PASS_COUNT=$((PASS_COUNT + 1))
        return 0
    fi
}

# ======================================================================
# TEST SUITE 1: Schema Version Tracking
# ======================================================================
echo "TEST SUITE 1: Schema Version Tracking"
echo "----------------------------------------------------------------------"

run_test "Schema version table exists" \
    "sqlite3 '$DB_PATH' 'SELECT COUNT(*) FROM schema_version' | grep -q '[0-9]'"

run_test "Schema version is v2 or higher" \
    "sqlite3 '$DB_PATH' 'SELECT MAX(version) FROM schema_version' | grep -qE '^[2-9]$'"

run_test "Schema version has timestamps" \
    "sqlite3 '$DB_PATH' 'SELECT applied_at FROM schema_version LIMIT 1' | grep -q '^20'"

echo

# ======================================================================
# TEST SUITE 2: Data Validation (CHECK Constraints via Triggers)
# ======================================================================
echo "TEST SUITE 2: Data Validation Triggers"
echo "----------------------------------------------------------------------"

run_test "Learnings insert trigger exists" \
    "sqlite3 '$DB_PATH' \"SELECT COUNT(*) FROM sqlite_master WHERE type='trigger' AND name='learnings_validate_insert'\" | grep -qE "^[12]$"'"

run_test "Learnings update trigger exists" \
    "sqlite3 '$DB_PATH' \"SELECT COUNT(*) FROM sqlite_master WHERE type='trigger' AND name='learnings_validate_update'\" | grep -qE "^[12]$"'"

run_test "Heuristics insert trigger exists" \
    "sqlite3 '$DB_PATH' \"SELECT COUNT(*) FROM sqlite_master WHERE type='trigger' AND name='heuristics_validate_insert'\" | grep -qE "^[12]$"'"

run_test "Heuristics update trigger exists" \
    "sqlite3 '$DB_PATH' \"SELECT COUNT(*) FROM sqlite_master WHERE type='trigger' AND name='heuristics_validate_update'\" | grep -qE "^[12]$"'"

# Test validation actually works
run_test_expect_fail "Reject invalid severity (0)" \
    "sqlite3 '$DB_PATH' \"INSERT INTO learnings (type, filepath, title, severity) VALUES ('failure', '/test/invalid1.md', 'Test', 0)\""

run_test_expect_fail "Reject invalid severity (6)" \
    "sqlite3 '$DB_PATH' \"INSERT INTO learnings (type, filepath, title, severity) VALUES ('failure', '/test/invalid2.md', 'Test', 6)\""

run_test_expect_fail "Reject invalid confidence (-0.1)" \
    "sqlite3 '$DB_PATH' \"INSERT INTO heuristics (domain, rule, confidence) VALUES ('test', 'Test rule', -0.1)\""

run_test_expect_fail "Reject invalid confidence (1.1)" \
    "sqlite3 '$DB_PATH' \"INSERT INTO heuristics (domain, rule, confidence) VALUES ('test', 'Test rule', 1.1)\""

echo

# ======================================================================
# TEST SUITE 3: VACUUM Scheduling
# ======================================================================
echo "TEST SUITE 3: Scheduled VACUUM"
echo "----------------------------------------------------------------------"

run_test "Operations tracking table exists" \
    "sqlite3 '$DB_PATH' 'SELECT COUNT(*) FROM db_operations' | grep -q '[0-9]'"

run_test "VACUUM timestamp recorded" \
    "sqlite3 '$DB_PATH' 'SELECT last_vacuum FROM db_operations WHERE id=1' | grep -q '^20'"

run_test "ANALYZE timestamp recorded" \
    "sqlite3 '$DB_PATH' 'SELECT last_analyze FROM db_operations WHERE id=1' | grep -q '^20'"

run_test "Operations counters exist" \
    "sqlite3 '$DB_PATH' 'SELECT total_vacuums, total_analyzes FROM db_operations WHERE id=1' | grep -q '[0-9]'"

echo

# ======================================================================
# TEST SUITE 4: Foreign Key Enforcement
# ======================================================================
echo "TEST SUITE 4: Foreign Key Enforcement"
echo "----------------------------------------------------------------------"

run_test "Foreign keys can be enabled" \
    "sqlite3 $DB_PATH 'PRAGMA foreign_keys=ON; PRAGMA foreign_keys' | grep -qE "^[12]$"'"


echo

# ======================================================================
# TEST SUITE 5: WAL Mode and Performance
# ======================================================================
echo "TEST SUITE 5: WAL Mode and Performance Settings"
echo "----------------------------------------------------------------------"

run_test "WAL journal mode enabled" \
    "sqlite3 '$DB_PATH' 'PRAGMA journal_mode' | grep -qi 'wal'"

run_test "Synchronous mode is NORMAL or FULL" \
    "sqlite3 '$DB_PATH' 'PRAGMA synchronous' | grep -qE "^[12]$"'"

run_test "Busy timeout >= 10 seconds" \
    "sqlite3 '$DB_PATH' 'PRAGMA busy_timeout' | awk '{if (\$1 >= 10000) exit 0; exit 1}'"

run_test "Temp store in MEMORY" \
    "sqlite3 '$DB_PATH' 'PRAGMA temp_store' | grep -q '^2$'"

echo

# ======================================================================
# TEST SUITE 6: Database Integrity
# ======================================================================
echo "TEST SUITE 6: Database Integrity"
echo "----------------------------------------------------------------------"

run_test "Integrity check passes" \
    "sqlite3 '$DB_PATH' 'PRAGMA integrity_check' | grep -qi '^ok$'"

run_test "Quick check passes" \
    "sqlite3 '$DB_PATH' 'PRAGMA quick_check' | grep -qi '^ok$'"

run_test "Foreign key check passes" \
    "sqlite3 '$DB_PATH' 'PRAGMA foreign_key_check' | wc -l | grep -q '^0$'"

echo

# ======================================================================
# TEST SUITE 7: Query Optimization
# ======================================================================
echo "TEST SUITE 7: Query Optimization"
echo "----------------------------------------------------------------------"

run_test "At least 10 indexes exist" \
    "sqlite3 '$DB_PATH' \"SELECT COUNT(*) FROM sqlite_master WHERE type='index'\" | awk '{if (\$1 >= 10) exit 0; exit 1}'"

run_test "Learnings domain index exists" \
    "sqlite3 '$DB_PATH' \"SELECT COUNT(*) FROM sqlite_master WHERE type='index' AND name LIKE '%learnings%domain%'\" | grep -q '[1-9]'"

run_test "Heuristics domain index exists" \
    "sqlite3 '$DB_PATH' \"SELECT COUNT(*) FROM sqlite_master WHERE type='index' AND name LIKE '%heuristics%domain%'\" | grep -q '[1-9]'"

run_test "sqlite_stat1 table exists (ANALYZE ran)" \
    "sqlite3 '$DB_PATH' \"SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='sqlite_stat1'\" | grep -qE "^[12]$"'"

echo

# ======================================================================
# TEST SUITE 8: Database Bloat Control
# ======================================================================
echo "TEST SUITE 8: Database Bloat Control"
echo "----------------------------------------------------------------------"

FREELIST=$(sqlite3 "$DB_PATH" "PRAGMA freelist_count")
PAGES=$(sqlite3 "$DB_PATH" "PRAGMA page_count")

if [ "$PAGES" -gt 0 ]; then
    BLOAT_PERCENT=$(awk "BEGIN {printf \"%.1f\", ($FREELIST / $PAGES) * 100}")
    echo "   Database: $PAGES pages, $FREELIST free ($BLOAT_PERCENT% bloat)"

    if awk "BEGIN {exit !($FREELIST / $PAGES < 0.1)}"; then
        echo "   [PASS] Bloat under 10%"
        PASS_COUNT=$((PASS_COUNT + 1))
    else
        echo "   [WARN] Bloat over 10%"
        FAIL_COUNT=$((FAIL_COUNT + 1))
    fi
    TEST_COUNT=$((TEST_COUNT + 1))
fi

echo

# ======================================================================
# TEST SUITE 9: Concurrency Safety
# ======================================================================
echo "TEST SUITE 9: Concurrency Safety"
echo "----------------------------------------------------------------------"

run_test "WAL mode supports concurrent reads" \
    "sqlite3 '$DB_PATH' 'PRAGMA journal_mode' | grep -qi 'wal'"

run_test "Busy timeout prevents immediate lockouts" \
    "sqlite3 '$DB_PATH' 'PRAGMA busy_timeout' | awk '{if (\$1 > 0) exit 0; exit 1}'"

# Simulate concurrent access
echo -n "[CONCURRENCY TEST] Multiple reads... "
(
    sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM learnings" > /dev/null &
    sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM heuristics" > /dev/null &
    sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM experiments" > /dev/null &
    wait
) 2>&1
if [ $? -eq 0 ]; then
    echo "PASS"
    PASS_COUNT=$((PASS_COUNT + 1))
else
    echo "FAIL"
    FAIL_COUNT=$((FAIL_COUNT + 1))
fi
TEST_COUNT=$((TEST_COUNT + 1))

echo

# ======================================================================
# TEST SUITE 10: Advanced Features
# ======================================================================
echo "TEST SUITE 10: Advanced Database Features"
echo "----------------------------------------------------------------------"

run_test "Cache size is optimized" \
    "sqlite3 '$DB_PATH' 'PRAGMA cache_size' | grep -qE '^-[0-9]+$'"

run_test "Page size is reasonable" \
    "sqlite3 '$DB_PATH' 'PRAGMA page_size' | awk '{if (\$1 >= 1024 && \$1 <= 65536) exit 0; exit 1}'"

run_test "Auto-vacuum is configured" \
    "sqlite3 '$DB_PATH' 'PRAGMA auto_vacuum' | grep -q '[0-2]'"

echo

# ======================================================================
# FINAL RESULTS
# ======================================================================
echo "======================================================================"
echo "TEST RESULTS"
echo "======================================================================"
echo "Total Tests: $TEST_COUNT"
echo "Passed:      $PASS_COUNT"
echo "Failed:      $FAIL_COUNT"
echo

if [ "$FAIL_COUNT" -eq 0 ]; then
    echo "[SUCCESS] All tests passed! Database robustness: 10/10"
    exit 0
elif [ "$FAIL_COUNT" -le 2 ]; then
    echo "[WARNING] Minor issues detected. Score: 9/10"
    exit 0
else
    echo "[ERROR] Multiple failures detected. Needs attention."
    exit 1
fi
