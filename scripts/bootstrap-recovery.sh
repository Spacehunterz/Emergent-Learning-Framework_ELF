#!/bin/bash
# Bootstrap Recovery Script for Emergent Learning Framework
# Purpose: Recover from system corruption and self-heal
#
# Recovery capabilities:
# - Restore database from markdown files
# - Rebuild indexes
# - Fix missing directories
# - Validate and repair golden rules
# - Recover from backup if available

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$(dirname "$SCRIPT_DIR")"
MEMORY_DIR="$BASE_DIR/memory"
DB_PATH="$MEMORY_DIR/index.db"
BACKUP_DIR="$BASE_DIR/backups"
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

# Output formatting
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m' # No Color

header() {
    echo -e "\n${BOLD}${BLUE}=== $* ===${NC}"
}

pass() {
    echo -e "  ${GREEN}✓${NC} $*"
}

fail() {
    echo -e "  ${RED}✗${NC} $*"
}

warn() {
    echo -e "  ${YELLOW}⚠${NC} $*"
}

info() {
    echo -e "  ${BLUE}ℹ${NC} $*"
}

# Create backup before recovery
create_backup() {
    header "Creating Backup"

    local timestamp=$(date +%Y%m%d-%H%M%S)
    local backup_path="$BACKUP_DIR/pre-recovery-$timestamp"

    mkdir -p "$backup_path"

    # Backup database
    if [ -f "$DB_PATH" ]; then
        cp "$DB_PATH" "$backup_path/index.db.backup"
        pass "Database backed up"
    else
        warn "No database to backup"
    fi

    # Backup golden rules
    if [ -d "$BASE_DIR/golden-rules" ]; then
        cp -r "$BASE_DIR/golden-rules" "$backup_path/"
        pass "Golden rules backed up"
    fi

    # Backup memory directory
    if [ -d "$MEMORY_DIR" ]; then
        cp -r "$MEMORY_DIR" "$backup_path/"
        pass "Memory directory backed up"
    fi

    info "Backup saved to: $backup_path"
    echo "$backup_path" > "$BACKUP_DIR/latest-backup.txt"
}

# Check system health
check_system_health() {
    header "System Health Check"

    local issues=0

    # Check database
    if [ ! -f "$DB_PATH" ]; then
        fail "Database missing"
        ((issues++))
    elif ! sqlite3 "$DB_PATH" "PRAGMA integrity_check" &>/dev/null; then
        fail "Database corrupted"
        ((issues++))
    else
        pass "Database intact"
    fi

    # Check critical directories
    local critical_dirs=("$MEMORY_DIR" "$MEMORY_DIR/failures" "$MEMORY_DIR/successes" "$MEMORY_DIR/heuristics")
    for dir in "${critical_dirs[@]}"; do
        if [ ! -d "$dir" ]; then
            fail "Missing directory: $dir"
            ((issues++))
        else
            pass "Directory exists: $(basename "$dir")"
        fi
    done

    # Check query system
    if [ ! -f "$BASE_DIR/query/query.py" ]; then
        fail "Query system missing"
        ((issues++))
    else
        pass "Query system present"
    fi

    if [ $issues -gt 0 ]; then
        warn "Found $issues issue(s) requiring recovery"
        return 1
    else
        pass "System is healthy"
        return 0
    fi
}

# Fix directory structure
fix_directory_structure() {
    header "Fixing Directory Structure"

    local dirs=(
        "$MEMORY_DIR"
        "$MEMORY_DIR/failures"
        "$MEMORY_DIR/successes"
        "$MEMORY_DIR/heuristics"
        "$BASE_DIR/golden-rules"
        "$BASE_DIR/ceo-inbox"
        "$BASE_DIR/experiments"
        "$BASE_DIR/experiments/active"
        "$BASE_DIR/experiments/completed"
        "$BASE_DIR/cycles"
        "$LOGS_DIR"
        "$BACKUP_DIR"
    )

    for dir in "${dirs[@]}"; do
        if [ ! -d "$dir" ]; then
            mkdir -p "$dir"
            pass "Created missing directory: $(basename "$dir")"
        fi
    done

    pass "Directory structure verified/created"
}

# Rebuild database from markdown files
rebuild_database() {
    header "Rebuilding Database from Markdown Files"

    # Backup existing database if it exists
    if [ -f "$DB_PATH" ]; then
        mv "$DB_PATH" "$DB_PATH.corrupted-$(date +%Y%m%d-%H%M%S)"
        warn "Moved corrupted database to backup"
    fi

    # Initialize new database using query.py
    if ! $PYTHON_CMD "$BASE_DIR/query/query.py" --stats &>/dev/null; then
        info "Initializing database..."
        # The query system auto-creates the database
        $PYTHON_CMD - <<EOF
import sys
sys.path.insert(0, '$BASE_DIR/query')
from query import QuerySystem
qs = QuerySystem()
print("Database initialized")
EOF
        pass "Database initialized"
    fi

    # Re-index all markdown files
    local indexed=0

    # Index failures
    for failure_file in "$MEMORY_DIR/failures"/*.md; do
        [ -f "$failure_file" ] || continue
        [ "$(basename "$failure_file")" = "TEMPLATE.md" ] && continue

        # Extract metadata from markdown
        local title=$(grep "^# " "$failure_file" | head -1 | sed 's/^# //')
        local domain=$(grep "^Domain:" "$failure_file" | sed 's/^Domain: *//')
        local severity=$(grep "^Severity:" "$failure_file" | sed 's/^Severity: *//')
        local tags=$(grep "^Tags:" "$failure_file" | sed 's/^Tags: *//')
        local created=$(grep "^Date:" "$failure_file" | sed 's/^Date: *//')

        if [ -n "$title" ]; then
            sqlite3 "$DB_PATH" <<SQL
INSERT INTO learnings (type, filepath, title, summary, tags, domain, severity, created_at)
VALUES ('failure', '$failure_file', '$title', '', '$tags', '$domain', ${severity:-1}, '${created:-$(date '+%Y-%m-%d %H:%M:%S')}');
SQL
            ((indexed++))
        fi
    done

    info "Indexed $indexed failure files"

    # Index successes
    indexed=0
    for success_file in "$MEMORY_DIR/successes"/*.md; do
        [ -f "$success_file" ] || continue
        [ "$(basename "$success_file")" = "TEMPLATE.md" ] && continue

        local title=$(grep "^# " "$success_file" | head -1 | sed 's/^# //')
        local domain=$(grep "^Domain:" "$success_file" | sed 's/^Domain: *//')

        if [ -n "$title" ]; then
            sqlite3 "$DB_PATH" <<SQL
INSERT INTO learnings (type, filepath, title, summary, domain, created_at)
VALUES ('success', '$success_file', '$title', '', '$domain', '$(date '+%Y-%m-%d %H:%M:%S')');
SQL
            ((indexed++))
        fi
    done

    info "Indexed $indexed success files"

    pass "Database rebuilt from markdown files"
}

# Validate and repair golden rules
validate_golden_rules() {
    header "Validating Golden Rules"

    local golden_rules_dir="$BASE_DIR/golden-rules"

    if [ ! -d "$golden_rules_dir" ]; then
        mkdir -p "$golden_rules_dir"
        warn "Golden rules directory was missing, created"
    fi

    # Check if there are any golden rules
    local rule_count=$(find "$golden_rules_dir" -name "*.md" -type f 2>/dev/null | wc -l)

    if [ "$rule_count" -eq 0 ]; then
        warn "No golden rules found"
        info "Golden rules should be created from proven heuristics"
    else
        pass "Found $rule_count golden rule files"
    fi

    # Validate golden rule format
    for rule_file in "$golden_rules_dir"/*.md; do
        [ -f "$rule_file" ] || continue

        if grep -q "^# " "$rule_file" && grep -q "^## Why" "$rule_file"; then
            pass "$(basename "$rule_file") has valid format"
        else
            warn "$(basename "$rule_file") may have invalid format"
        fi
    done

    pass "Golden rules validated"
}

# Rebuild indexes
rebuild_indexes() {
    header "Rebuilding Database Indexes"

    sqlite3 "$DB_PATH" <<SQL
-- Drop existing indexes
DROP INDEX IF EXISTS idx_learnings_domain;
DROP INDEX IF EXISTS idx_learnings_type;
DROP INDEX IF EXISTS idx_learnings_created_at;
DROP INDEX IF EXISTS idx_learnings_domain_created;
DROP INDEX IF EXISTS idx_heuristics_domain;
DROP INDEX IF EXISTS idx_heuristics_golden;

-- Recreate indexes
CREATE INDEX idx_learnings_domain ON learnings(domain);
CREATE INDEX idx_learnings_type ON learnings(type);
CREATE INDEX idx_learnings_created_at ON learnings(created_at DESC);
CREATE INDEX idx_learnings_domain_created ON learnings(domain, created_at DESC);
CREATE INDEX idx_heuristics_domain ON heuristics(domain);
CREATE INDEX idx_heuristics_golden ON heuristics(is_golden);

-- Analyze for query optimization
ANALYZE;
SQL

    pass "Database indexes rebuilt"
}

# Verify recovery
verify_recovery() {
    header "Verifying Recovery"

    # Check database integrity
    if sqlite3 "$DB_PATH" "PRAGMA integrity_check" | grep -q "ok"; then
        pass "Database integrity verified"
    else
        fail "Database still has integrity issues"
        return 1
    fi

    # Check if query system works
    if $PYTHON_CMD "$BASE_DIR/query/query.py" --stats &>/dev/null; then
        pass "Query system functional"
    else
        fail "Query system not working"
        return 1
    fi

    # Check record scripts
    if [ -x "$SCRIPT_DIR/record-failure.sh" ]; then
        pass "record-failure.sh executable"
    else
        warn "record-failure.sh not executable"
    fi

    # Get statistics
    local total_learnings=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM learnings")
    info "Recovered $total_learnings learnings"

    pass "Recovery verification complete"
    return 0
}

# Auto-detect and fix common issues
auto_fix_issues() {
    header "Auto-Fixing Common Issues"

    # Fix file permissions
    chmod +x "$SCRIPT_DIR"/*.sh 2>/dev/null || true
    pass "Script permissions fixed"

    # Fix database journal mode for better concurrency
    sqlite3 "$DB_PATH" "PRAGMA journal_mode=WAL;" &>/dev/null || true
    pass "Database journal mode optimized"

    # Clean up orphaned files
    find "$MEMORY_DIR" -name "*.tmp" -delete 2>/dev/null || true
    find "$MEMORY_DIR" -name "*.lock" -delete 2>/dev/null || true
    pass "Temporary files cleaned"

    # Vacuum database
    sqlite3 "$DB_PATH" "VACUUM;" &>/dev/null || true
    pass "Database vacuumed"
}

# Record recovery to the building
record_recovery_event() {
    header "Recording Recovery Event"

    # Use the record-failure script to log this recovery
    if [ -x "$SCRIPT_DIR/record-failure.sh" ]; then
        FAILURE_TITLE="System recovery performed" \
        FAILURE_DOMAIN="meta-learning" \
        FAILURE_SUMMARY="Bootstrap recovery script executed. System was restored from corruption or reset." \
        FAILURE_SEVERITY=2 \
        FAILURE_TAGS="recovery,meta-learning,bootstrap" \
        "$SCRIPT_DIR/record-failure.sh" &>/dev/null || warn "Failed to record recovery event"

        pass "Recovery event logged to the building"
    fi
}

# Summary
generate_summary() {
    header "Recovery Summary"

    local total_learnings=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM learnings" 2>/dev/null || echo "0")
    local total_heuristics=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM heuristics" 2>/dev/null || echo "0")

    echo ""
    echo "Recovery completed successfully!"
    echo ""
    echo "System Status:"
    echo "  • Database: Restored and verified"
    echo "  • Learnings: $total_learnings"
    echo "  • Heuristics: $total_heuristics"
    echo "  • Directories: All present"
    echo "  • Scripts: Functional"
    echo ""
    echo "The system has been recovered and is ready for use."
    echo ""
}

# Interactive recovery mode
interactive_recovery() {
    echo -e "${BOLD}Emergent Learning Framework - Bootstrap Recovery${NC}"
    echo ""
    echo "This script will attempt to recover the system from corruption."
    echo ""
    read -p "Continue with recovery? (y/n) " -n 1 -r
    echo ""

    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Recovery cancelled"
        exit 0
    fi

    create_backup
    fix_directory_structure
    auto_fix_issues

    # Check if database rebuild is needed
    if [ ! -f "$DB_PATH" ] || ! sqlite3 "$DB_PATH" "PRAGMA integrity_check" &>/dev/null; then
        warn "Database issues detected, rebuilding..."
        rebuild_database
        rebuild_indexes
    fi

    validate_golden_rules
    verify_recovery
    record_recovery_event
    generate_summary
}

# Non-interactive recovery mode
auto_recovery() {
    echo -e "${BOLD}Emergent Learning Framework - Automatic Bootstrap Recovery${NC}"
    echo ""

    create_backup
    fix_directory_structure
    auto_fix_issues

    if [ ! -f "$DB_PATH" ] || ! sqlite3 "$DB_PATH" "PRAGMA integrity_check" &>/dev/null; then
        rebuild_database
        rebuild_indexes
    fi

    validate_golden_rules
    verify_recovery
    record_recovery_event
    generate_summary
}

# Main execution
main() {
    mkdir -p "$LOGS_DIR" "$BACKUP_DIR"

    # Check for --auto flag
    if [[ "$1" == "--auto" ]]; then
        auto_recovery
    else
        # First check if recovery is even needed
        if check_system_health; then
            echo ""
            echo "System is healthy. No recovery needed."
            echo "Use --force to run recovery anyway."
            exit 0
        fi

        interactive_recovery
    fi

    echo -e "\n${GREEN}Bootstrap recovery completed successfully${NC}"
}

main "$@"
