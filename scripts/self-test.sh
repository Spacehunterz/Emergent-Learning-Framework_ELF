#!/bin/bash
# Self-Test Script for Emergent Learning Framework
# Purpose: Meta-learning - can the system detect its own bugs?
#
# This script runs comprehensive self-diagnostics including:
# - Database integrity checks
# - Script functionality tests
# - Circular dependency detection
# - File system consistency
# - Auto-record failures found

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$(dirname "$SCRIPT_DIR")"
MEMORY_DIR="$BASE_DIR/memory"
DB_PATH="$MEMORY_DIR/index.db"
LOGS_DIR="$BASE_DIR/logs"

# Detect Python command
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
else
    echo "Error: Python not found. Install from https://python.org"
    exit 1
fi

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test results tracking
TESTS_PASSED=0
TESTS_FAILED=0
TESTS_WARNINGS=0
FAILURE_DETAILS=()

# Logging setup
LOG_FILE="$LOGS_DIR/self-test-$(date +%Y%m%d-%H%M%S).log"
mkdir -p "$LOGS_DIR"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

pass() {
    echo -e "${GREEN}✓ PASS${NC}: $*" | tee -a "$LOG_FILE"
    ((TESTS_PASSED++))
}

fail() {
    echo -e "${RED}✗ FAIL${NC}: $*" | tee -a "$LOG_FILE"
    ((TESTS_FAILED++))
    FAILURE_DETAILS+=("$*")
}

warn() {
    echo -e "${YELLOW}⚠ WARN${NC}: $*" | tee -a "$LOG_FILE"
    ((TESTS_WARNINGS++))
}

info() {
    echo -e "ℹ INFO: $*" | tee -a "$LOG_FILE"
}

# Test 1: Directory Structure
test_directory_structure() {
    log "=== Test 1: Directory Structure ==="

    local required_dirs=(
        "$MEMORY_DIR"
        "$MEMORY_DIR/failures"
        "$MEMORY_DIR/successes"
        "$MEMORY_DIR/heuristics"
        "$BASE_DIR/scripts"
        "$BASE_DIR/query"
        "$BASE_DIR/golden-rules"
        "$BASE_DIR/ceo-inbox"
        "$BASE_DIR/experiments"
        "$LOGS_DIR"
    )

    for dir in "${required_dirs[@]}"; do
        if [ -d "$dir" ]; then
            pass "Directory exists: $dir"
        else
            fail "Missing directory: $dir"
        fi
    done
}

# Test 2: Database Integrity
test_database_integrity() {
    log "=== Test 2: Database Integrity ==="

    if [ ! -f "$DB_PATH" ]; then
        fail "Database file does not exist: $DB_PATH"
        return
    fi
    pass "Database file exists"

    # Check database integrity
    if sqlite3 "$DB_PATH" "PRAGMA integrity_check" | grep -q "ok"; then
        pass "Database integrity check passed"
    else
        fail "Database integrity check failed"
    fi

    # Check required tables
    local required_tables=("learnings" "heuristics" "experiments" "ceo_reviews")
    for table in "${required_tables[@]}"; do
        if sqlite3 "$DB_PATH" "SELECT name FROM sqlite_master WHERE type='table' AND name='$table'" | grep -q "$table"; then
            pass "Table exists: $table"
        else
            fail "Missing table: $table"
        fi
    done

    # Check for orphaned records
    local orphaned=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM learnings WHERE filepath NOT LIKE '%/%'")
    if [ "$orphaned" -eq 0 ]; then
        pass "No orphaned records in learnings table"
    else
        warn "Found $orphaned potentially orphaned records in learnings"
    fi
}

# Test 3: File-Database Sync
test_file_database_sync() {
    log "=== Test 3: File-Database Synchronization ==="

    # Count files in each category
    local failure_files=$(find "$MEMORY_DIR/failures" -name "*.md" -type f 2>/dev/null | wc -l)
    local success_files=$(find "$MEMORY_DIR/successes" -name "*.md" -type f 2>/dev/null | wc -l)

    # Count DB records
    local db_failures=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM learnings WHERE type='failure'")
    local db_successes=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM learnings WHERE type='success'")

    info "Failure files: $failure_files, DB records: $db_failures"
    info "Success files: $success_files, DB records: $db_successes"

    # Allow some discrepancy due to TEMPLATE files
    if [ "$((failure_files - db_failures))" -le 1 ] && [ "$((failure_files - db_failures))" -ge -1 ]; then
        pass "Failure files and DB records are synchronized"
    else
        warn "Mismatch: $failure_files failure files vs $db_failures DB records"
    fi

    if [ "$((success_files - db_successes))" -le 1 ] && [ "$((success_files - db_successes))" -ge -1 ]; then
        pass "Success files and DB records are synchronized"
    else
        warn "Mismatch: $success_files success files vs $db_successes DB records"
    fi
}

# Test 4: Script Functionality
test_script_functionality() {
    log "=== Test 4: Script Functionality ==="

    local required_scripts=(
        "$SCRIPT_DIR/record-failure.sh"
        "$SCRIPT_DIR/record-heuristic.sh"
        "$SCRIPT_DIR/init.sh"
        "$BASE_DIR/query/query.py"
    )

    for script in "${required_scripts[@]}"; do
        if [ -f "$script" ]; then
            if [ -x "$script" ] || [[ "$script" == *.py ]]; then
                pass "Script exists and is executable: $(basename $script)"
            else
                warn "Script exists but is not executable: $(basename $script)"
            fi
        else
            fail "Missing script: $(basename $script)"
        fi
    done

    # Test query.py basic functionality
    if $PYTHON_CMD "$BASE_DIR/query/query.py" --stats >/dev/null 2>&1; then
        pass "query.py --stats executes successfully"
    else
        fail "query.py --stats failed to execute"
    fi
}

# Test 5: Circular Dependencies
test_circular_dependencies() {
    log "=== Test 5: Circular Dependencies ==="

    # Check for circular imports in Python scripts
    local python_files=$(find "$BASE_DIR" -name "*.py" -type f 2>/dev/null)
    local circular_found=false

    for py_file in $python_files; do
        # Simple heuristic: check if file imports itself or creates obvious cycles
        local filename=$(basename "$py_file" .py)
        if grep -q "from $filename import\|import $filename" "$py_file" 2>/dev/null; then
            fail "Potential circular import in $py_file"
            circular_found=true
        fi
    done

    if [ "$circular_found" = false ]; then
        pass "No obvious circular dependencies detected in Python files"
    fi

    # Check for circular dependencies in shell scripts
    # Look for scripts that source each other
    local shell_scripts=$(find "$SCRIPT_DIR" -name "*.sh" -type f 2>/dev/null)
    local script_deps=()

    for script in $shell_scripts; do
        local sourced=$(grep -E "^\s*\.\s+|^\s*source\s+" "$script" 2>/dev/null | grep -v "^#" || true)
        if [ -n "$sourced" ]; then
            info "$(basename $script) sources: $sourced"
        fi
    done

    pass "Shell script dependency check completed"
}

# Test 6: Golden Rules Integrity
test_golden_rules() {
    log "=== Test 6: Golden Rules Integrity ==="

    local golden_rules_dir="$BASE_DIR/golden-rules"

    if [ ! -d "$golden_rules_dir" ]; then
        warn "Golden rules directory does not exist"
        return
    fi

    local rule_count=$(find "$golden_rules_dir" -name "*.md" -type f 2>/dev/null | wc -l)
    info "Found $rule_count golden rule files"

    if [ "$rule_count" -gt 0 ]; then
        pass "Golden rules exist ($rule_count files)"
    else
        warn "No golden rules found"
    fi

    # Check if golden rules are loaded by query system
    if $PYTHON_CMD "$BASE_DIR/query/query.py" --golden-rules 2>/dev/null | grep -q "Golden Rules"; then
        pass "Golden rules can be loaded by query system"
    else
        warn "Golden rules query returned unexpected format"
    fi
}

# Test 7: Memory System Tests
test_memory_system() {
    log "=== Test 7: Memory System ==="

    # Test recent query
    if $PYTHON_CMD "$BASE_DIR/query/query.py" --recent 1 >/dev/null 2>&1; then
        pass "Recent learnings query works"
    else
        fail "Recent learnings query failed"
    fi

    # Test domain query (use a domain we know exists)
    local domains=$(sqlite3 "$DB_PATH" "SELECT DISTINCT domain FROM learnings LIMIT 1")
    if [ -n "$domains" ]; then
        if $PYTHON_CMD "$BASE_DIR/query/query.py" --domain "$domains" --limit 1 >/dev/null 2>&1; then
            pass "Domain query works"
        else
            fail "Domain query failed"
        fi
    else
        warn "No domains found in database to test query"
    fi

    # Test stats query
    local stats=$($PYTHON_CMD "$BASE_DIR/query/query.py" --stats 2>/dev/null)
    if echo "$stats" | grep -q "total_learnings"; then
        pass "Statistics query works"
    else
        fail "Statistics query failed or returned unexpected format"
    fi
}

# Test 8: Concurrent Access Safety
test_concurrent_access() {
    log "=== Test 8: Concurrent Access Safety ==="

    # Check if scripts have concurrent access protection
    if grep -q "acquire_git_lock\|flock" "$SCRIPT_DIR/record-failure.sh" 2>/dev/null; then
        pass "record-failure.sh has concurrent access protection"
    else
        warn "record-failure.sh may not have concurrent access protection"
    fi

    if grep -q "sqlite_with_retry" "$SCRIPT_DIR/record-failure.sh" 2>/dev/null; then
        pass "record-failure.sh has SQLite retry logic"
    else
        warn "record-failure.sh may not have SQLite retry logic"
    fi
}

# Test 9: Bootstrap Recovery Test
test_bootstrap_recovery() {
    log "=== Test 9: Bootstrap Recovery ==="

    # Check if init scripts exist
    if [ -f "$SCRIPT_DIR/init.sh" ]; then
        pass "Bootstrap init script exists"
    else
        fail "Bootstrap init script missing"
    fi

    # Check if schema.sql exists for database recreation
    if [ -f "$MEMORY_DIR/schema.sql" ]; then
        pass "Database schema file exists for recovery"
    else
        warn "No schema.sql file found - database recovery may be difficult"
    fi

    # Check if query.py can recreate database if missing
    if grep -q "CREATE TABLE IF NOT EXISTS" "$BASE_DIR/query/query.py" 2>/dev/null; then
        pass "query.py has database auto-initialization"
    else
        warn "query.py may not auto-initialize database"
    fi
}

# Test 10: Learning Velocity Metrics
test_learning_metrics() {
    log "=== Test 10: Learning Velocity Metrics ==="

    # Calculate learnings per day over last 7 days
    local learnings_last_7d=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM learnings WHERE created_at >= datetime('now', '-7 days')")
    info "Learnings in last 7 days: $learnings_last_7d"

    # Calculate heuristics promotion rate
    local total_heuristics=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM heuristics")
    local golden_heuristics=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM heuristics WHERE is_golden = 1")

    if [ "$total_heuristics" -gt 0 ]; then
        local promotion_rate=$(echo "scale=2; $golden_heuristics * 100 / $total_heuristics" | bc)
        info "Heuristic promotion rate: $promotion_rate% ($golden_heuristics/$total_heuristics)"
    fi

    # Most active domain
    local most_active_domain=$(sqlite3 "$DB_PATH" "SELECT domain, COUNT(*) as cnt FROM learnings GROUP BY domain ORDER BY cnt DESC LIMIT 1")
    info "Most active domain: $most_active_domain"

    pass "Learning metrics calculated successfully"
}

# Test 11: Deduplication Check
test_deduplication() {
    log "=== Test 11: Deduplication Check ==="

    # Check for exact duplicate titles
    local duplicate_titles=$(sqlite3 "$DB_PATH" "SELECT title, COUNT(*) as cnt FROM learnings GROUP BY title HAVING cnt > 1")

    if [ -z "$duplicate_titles" ]; then
        pass "No exact duplicate titles found"
    else
        warn "Found duplicate titles in database:"
        echo "$duplicate_titles" | tee -a "$LOG_FILE"
    fi

    # Check for similar failures (simple similarity: same domain + similar severity)
    local similar_failures=$(sqlite3 "$DB_PATH" "
        SELECT l1.title, l2.title
        FROM learnings l1, learnings l2
        WHERE l1.id < l2.id
        AND l1.domain = l2.domain
        AND l1.severity = l2.severity
        AND l1.type = 'failure'
        AND l2.type = 'failure'
        LIMIT 5
    ")

    if [ -n "$similar_failures" ]; then
        info "Found potentially similar failures (same domain/severity)"
    fi

    pass "Deduplication check completed"
}

# Auto-record failures found during self-test
auto_record_failures() {
    if [ "$TESTS_FAILED" -gt 0 ]; then
        log "=== Auto-Recording Self-Test Failures ==="

        local failure_summary="Self-test found $TESTS_FAILED issue(s):\n"
        for detail in "${FAILURE_DETAILS[@]}"; do
            failure_summary="${failure_summary}- $detail\n"
        done

        # Record to the building
        FAILURE_TITLE="Self-test detected system issues" \
        FAILURE_DOMAIN="meta-learning" \
        FAILURE_SUMMARY="$failure_summary" \
        FAILURE_SEVERITY=3 \
        FAILURE_TAGS="self-test,meta-learning,automated" \
        "$SCRIPT_DIR/record-failure.sh" 2>/dev/null || warn "Failed to auto-record failures"

        if [ $? -eq 0 ]; then
            info "Self-test failures automatically recorded to the building"
        fi
    fi
}

# Generate summary report
generate_summary() {
    log "=== Self-Test Summary ==="
    log "Tests Passed: $TESTS_PASSED"
    log "Tests Failed: $TESTS_FAILED"
    log "Warnings: $TESTS_WARNINGS"
    log "Total Tests: $((TESTS_PASSED + TESTS_FAILED))"

    if [ "$TESTS_FAILED" -eq 0 ]; then
        log "Overall Status: ${GREEN}ALL TESTS PASSED${NC}"
        return 0
    else
        log "Overall Status: ${RED}SOME TESTS FAILED${NC}"
        log "See details in: $LOG_FILE"
        return 1
    fi
}

# Main execution
main() {
    log "========================================="
    log "Emergent Learning Framework - Self-Test"
    log "Started: $(date)"
    log "========================================="

    test_directory_structure
    test_database_integrity
    test_file_database_sync
    test_script_functionality
    test_circular_dependencies
    test_golden_rules
    test_memory_system
    test_concurrent_access
    test_bootstrap_recovery
    test_learning_metrics
    test_deduplication

    auto_record_failures
    generate_summary

    log "========================================="
    log "Self-Test Complete"
    log "Log saved to: $LOG_FILE"
    log "========================================="
}

# Run main
main
exit $?
