#!/bin/bash
# Synchronize database and markdown files in the Emergent Learning Framework
#
# Usage: ./sync-db-markdown.sh          # Report only
#        ./sync-db-markdown.sh --fix    # Report and fix issues
#
# Detects and optionally fixes:
# - Orphaned markdown files (exist in filesystem but not in database)
# - Orphaned database records (exist in database but file missing)
#
# Exit codes:
#   0 - Success (synchronized or no issues found)
#   1 - Input validation error
#   2 - Database error
#   3 - Git error (if --commit specified)
#   4 - Filesystem error
#   5 - Missing dependency
#   7 - Validation error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$(dirname "$SCRIPT_DIR")"
MEMORY_DIR="$BASE_DIR/memory"
DB_PATH="$MEMORY_DIR/index.db"
HEURISTICS_DIR="$MEMORY_DIR/heuristics"
FAILURES_DIR="$MEMORY_DIR/failures"
SUCCESSES_DIR="$MEMORY_DIR/successes"
LOGS_DIR="$BASE_DIR/logs"
SCRIPT_NAME="sync-db-markdown"

# Setup logging before loading library
LOG_FILE="$LOGS_DIR/$(date +%Y%m%d).log"
if ! mkdir -p "$LOGS_DIR" 2>/dev/null; then
    echo "ERROR: Cannot create logs directory: $LOGS_DIR" >&2
    exit 4
fi

# Load error handling library

# ========================================
# OBSERVABILITY INTEGRATION
# ========================================

# Source observability libraries
if [ -f "$SCRIPT_DIR/lib/logging.sh" ]; then
    source "$SCRIPT_DIR/lib/logging.sh"
    source "$SCRIPT_DIR/lib/metrics.sh" 2>/dev/null || true
    source "$SCRIPT_DIR/lib/alerts.sh" 2>/dev/null || true

    # Initialize observability
    log_init "sync-db-markdown" "$LOGS_DIR"
    metrics_init "$DB_PATH" 2>/dev/null || true
    alerts_init "$BASE_DIR" 2>/dev/null || true

    # Generate correlation ID for this execution
    CORRELATION_ID=$(log_get_correlation_id)
    export CORRELATION_ID

    log_info "Script started" user="$(whoami)" correlation_id="$CORRELATION_ID"

    # Start performance tracking
    log_timer_start "sync-db-markdown_total"
    OPERATION_START=$(metrics_operation_start "sync-db-markdown" 2>/dev/null || echo "")
else
    # Fallback if libraries not found
    CORRELATION_ID="${script_name}_$(date +%s)_$$"
    OPERATION_START=""
fi

# ========================================

LIB_DIR="$SCRIPT_DIR/lib"
if [ ! -f "$LIB_DIR/error-handling.sh" ]; then
    echo "FATAL: Error handling library not found: $LIB_DIR/error-handling.sh" >&2
    exit 5
fi
source "$LIB_DIR/error-handling.sh"

# Setup error trap
setup_error_trap

log_info "Script started"

# ============================================
# Parse arguments
# ============================================
FIX_MODE=false
VERBOSE=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --fix) FIX_MODE=true; shift ;;
        --verbose|-v) VERBOSE=true; shift ;;
        *)
            echo "Unknown argument: $1" >&2
            echo "Usage: $0 [--fix] [--verbose]" >&2
            exit 1
            ;;
    esac
done

log_info "Running in ${FIX_MODE} mode (verbose: $VERBOSE)"

# ============================================
# Counters
# ============================================
ORPHANED_MD_FILES=0
ORPHANED_DB_RECORDS=0
FIXED_MD_FILES=0
FIXED_DB_RECORDS=0
ERRORS_ENCOUNTERED=0

# ============================================
# Pre-flight checks
# ============================================
preflight_check() {
    log_info "Starting pre-flight checks"

    # Check required commands
    require_command "sqlite3" "Install sqlite3: apt-get install sqlite3 or brew install sqlite"

    # Check required files and directories
    require_file "$DB_PATH" "Database not found: $DB_PATH"

    # Database integrity check
    check_db_integrity "$DB_PATH"

    log_success "Pre-flight checks passed"
}

preflight_check

# ============================================
# Helper Functions
# ============================================

# Parse metadata from failure markdown file - sets global variables
parse_failure_md() {
    local file="$1"

    if [ ! -f "$file" ]; then
        log_error "Cannot parse non-existent file: $file"
        return 1
    fi

    # Extract title from first heading
    PARSED_TITLE=$(grep -m1 '^# ' "$file" 2>/dev/null | sed 's/^# //' || echo "Unknown")

    # Extract domain
    PARSED_DOMAIN=$(grep -i '^\*\*Domain\*\*:' "$file" 2>/dev/null | sed 's/.*: *//' | head -1)
    if [ -z "$PARSED_DOMAIN" ]; then
        PARSED_DOMAIN=$(grep -i '^Domain:' "$file" 2>/dev/null | sed 's/.*: *//' | head -1)
    fi
    [ -z "$PARSED_DOMAIN" ] && PARSED_DOMAIN="unknown"

    # Extract severity
    PARSED_SEVERITY=$(grep -i '^\*\*Severity\*\*:' "$file" 2>/dev/null | sed 's/.*: *//' | head -1)
    if [ -z "$PARSED_SEVERITY" ]; then
        PARSED_SEVERITY=$(grep -i '^Severity:' "$file" 2>/dev/null | sed 's/.*: *//' | head -1)
    fi
    # Convert words to numbers
    case "$PARSED_SEVERITY" in
        [1-5]) ;; # already a number
        low) PARSED_SEVERITY=2 ;;
        medium|Medium) PARSED_SEVERITY=3 ;;
        high|High) PARSED_SEVERITY=4 ;;
        critical|Critical) PARSED_SEVERITY=5 ;;
        *) PARSED_SEVERITY=3 ;;
    esac

    # Extract tags
    PARSED_TAGS=$(grep -i '^\*\*Tags\*\*:' "$file" 2>/dev/null | sed 's/.*: *//' | head -1)
    if [ -z "$PARSED_TAGS" ]; then
        PARSED_TAGS=$(grep -i '^Tags:' "$file" 2>/dev/null | sed 's/.*: *//' | head -1)
    fi

    # Extract summary (use title as fallback)
    PARSED_SUMMARY=$(sed -n '/^## Summary/,/^##/p' "$file" 2>/dev/null | grep -v '^##' | head -1 | tr -d '\r\n')
    [ -z "$PARSED_SUMMARY" ] && PARSED_SUMMARY="$PARSED_TITLE"

    log_info "Parsed failure metadata: title='$PARSED_TITLE', domain='$PARSED_DOMAIN', severity=$PARSED_SEVERITY"
    return 0
}

# Check if heuristic file has YAML frontmatter with a rule
has_yaml_rule() {
    local file="$1"
    [ -f "$file" ] && head -1 "$file" 2>/dev/null | grep -q '^---$' && grep -q '^rule:' "$file" 2>/dev/null
}

# Parse YAML heuristic and insert into DB
insert_yaml_heuristic() {
    local file="$1"
    local domain
    domain=$(basename "$file" .md)

    # Override domain if specified in YAML
    local yaml_domain
    yaml_domain=$(grep '^domain:' "$file" 2>/dev/null | sed 's/domain: *//' | head -1)
    [ -n "$yaml_domain" ] && domain="$yaml_domain"

    local rule
    rule=$(grep '^rule:' "$file" 2>/dev/null | sed 's/rule: *//')

    if [ -z "$rule" ]; then
        log_error "No rule found in YAML heuristic: $file"
        return 1
    fi

    local explanation
    explanation=$(grep '^explanation:' "$file" 2>/dev/null | sed 's/explanation: *//')

    local source_type
    source_type=$(grep '^source_type:' "$file" 2>/dev/null | sed 's/source_type: *//')
    [ -z "$source_type" ] && source_type="observation"

    local confidence
    confidence=$(grep '^confidence:' "$file" 2>/dev/null | sed 's/confidence: *//')
    [ -z "$confidence" ] && confidence="0.7"

    # Escape for SQL
    local rule_escaped
    rule_escaped=$(escape_sql "$rule")
    local explanation_escaped
    explanation_escaped=$(escape_sql "$explanation")
    local domain_escaped
    domain_escaped=$(escape_sql "$domain")

    if ! sqlite_with_retry "$DB_PATH" "INSERT INTO heuristics (domain, rule, explanation, source_type, confidence) VALUES ('$domain_escaped', '$rule_escaped', '$explanation_escaped', '$source_type', $confidence);" >/dev/null; then
        log_error "Failed to insert YAML heuristic into database: $file"
        return 1
    fi

    log_success "Inserted YAML heuristic into database: $rule"
    echo 1
    return 0
}

# Parse markdown heuristic file and insert rules into DB
insert_markdown_heuristics() {
    local file="$1"
    local domain
    domain=$(basename "$file" .md)
    local count=0

    # Find lines that look like rule headings
    while IFS= read -r line; do
        # Match ## H-N: or ## N. patterns
        if echo "$line" | grep -qE '^## (H-[0-9]+:|[0-9]+\.)'; then
            # Extract the rule text from the heading
            local rule
            rule=$(echo "$line" | sed -E 's/^## (H-[0-9]+: ?|[0-9]+\. ?)//')

            # If rule is short, it might be just a title - look for quoted version
            if [ ${#rule} -lt 30 ]; then
                local quoted
                quoted=$(grep -A3 "^${line}" "$file" 2>/dev/null | grep '^>' | head -1 | sed 's/^> *//')
                [ -n "$quoted" ] && rule="$quoted"
            fi

            # Default confidence
            local conf="0.7"

            # Escape for SQL
            local rule_escaped
            rule_escaped=$(escape_sql "$rule")
            local domain_escaped
            domain_escaped=$(escape_sql "$domain")

            if sqlite_with_retry "$DB_PATH" "INSERT INTO heuristics (domain, rule, explanation, source_type, confidence) VALUES ('$domain_escaped', '$rule_escaped', '', 'observation', $conf);" >/dev/null; then
                count=$((count + 1))
                log_success "Inserted heuristic: $rule"
            else
                log_error "Failed to insert heuristic: $rule"
                ((ERRORS_ENCOUNTERED++))
            fi
        fi
    done < "$file"

    echo $count
    return 0
}

# ============================================
# Report Header
# ============================================
echo "=============================================="
echo "  Database/Markdown Synchronization Report"
echo "=============================================="
echo ""
echo "Mode: $([ "$FIX_MODE" = true ] && echo "FIX" || echo "REPORT ONLY")"
echo ""

# ============================================
# PHASE 1: Check for orphaned failure markdown files
# ============================================
echo "--- Failures: Checking for orphaned markdown files ---"

if [ -d "$FAILURES_DIR" ]; then
    for md_file in "$FAILURES_DIR"/*.md; do
        [ -f "$md_file" ] || continue
        [ "$(basename "$md_file")" = "TEMPLATE.md" ] && continue

        relative_path="memory/failures/$(basename "$md_file")"
        relative_path_escaped=$(escape_sql "$relative_path")

        # Check if exists in database
        if ! db_count=$(sqlite_with_retry "$DB_PATH" "SELECT COUNT(*) FROM learnings WHERE filepath='$relative_path_escaped'"); then
            log_error "Database query failed for: $relative_path"
            ((ERRORS_ENCOUNTERED++))
            continue
        fi

        if [ "$db_count" -eq 0 ]; then
            ((ORPHANED_MD_FILES++))
            report_status "warning" "ORPHANED FILE: $relative_path"
            log_info "Found orphaned failure file: $relative_path"

            if [ "$FIX_MODE" = true ]; then
                # Parse metadata from file
                if parse_failure_md "$md_file"; then
                    # Insert into database
                    title_escaped=$(escape_sql "$PARSED_TITLE")
                    summary_escaped=$(escape_sql "$PARSED_SUMMARY")
                    tags_escaped=$(escape_sql "$PARSED_TAGS")
                    domain_escaped=$(escape_sql "$PARSED_DOMAIN")

                    if sqlite_with_retry "$DB_PATH" <<SQL >/dev/null
INSERT INTO learnings (type, filepath, title, summary, tags, domain, severity)
VALUES (
    'failure',
    '$relative_path_escaped',
    '$title_escaped',
    '$summary_escaped',
    '$tags_escaped',
    '$domain_escaped',
    CAST($PARSED_SEVERITY AS INTEGER)
);
SQL
                    then
                        report_status "success" "  -> FIXED: Added to database"
                        log_success "Fixed orphaned failure file: $relative_path"
                        ((FIXED_MD_FILES++))
                    else
                        report_status "failure" "  -> FAILED: Could not add to database"
                        log_error "Failed to fix orphaned failure file: $relative_path"
                        ((ERRORS_ENCOUNTERED++))
                    fi
                else
                    report_status "failure" "  -> FAILED: Could not parse metadata"
                    ((ERRORS_ENCOUNTERED++))
                fi
            fi
        fi
    done
else
    log_warn "Failures directory does not exist: $FAILURES_DIR"
fi

# ============================================
# PHASE 2: Check for orphaned failure database records
# ============================================
echo ""
echo "--- Failures: Checking for orphaned database records ---"

while IFS='|' read -r id filepath title domain severity; do
    # Strip carriage return (Windows line endings)
    severity="${severity%$'\r'}"
    [ -z "$filepath" ] && continue

    full_path="$BASE_DIR/$filepath"

    if [ ! -f "$full_path" ]; then
        ((ORPHANED_DB_RECORDS++))
        report_status "warning" "ORPHANED DB RECORD: $filepath (ID: $id)"
        log_info "Found orphaned failure DB record: $filepath"

        if [ "$FIX_MODE" = true ]; then
            # Recreate the file from database data
            if safe_mkdir "$(dirname "$full_path")" "Creating parent directory for $filepath"; then
                if cat > "$full_path" <<EOF
# $title

**Domain**: $domain
**Severity**: $severity
**Tags**:
**Date**: $(date +%Y-%m-%d)

## Summary

(Recovered from database - original file was missing)

## What Happened

[Describe the failure in detail]

## Root Cause

[What was the underlying issue?]

## Impact

[What were the consequences?]

## Prevention

[What heuristic or practice would prevent this?]

## Related

- **Experiments**:
- **Heuristics**:
- **Similar Failures**:
EOF
                then
                    report_status "success" "  -> FIXED: Recreated markdown file"
                    log_success "Recreated missing failure file: $filepath"
                    ((FIXED_DB_RECORDS++))
                else
                    report_status "failure" "  -> FAILED: Could not recreate file"
                    log_error "Failed to recreate file: $filepath"
                    ((ERRORS_ENCOUNTERED++))
                fi
            else
                report_status "failure" "  -> FAILED: Could not create parent directory"
                ((ERRORS_ENCOUNTERED++))
            fi
        fi
    fi
done < <(sqlite_with_retry "$DB_PATH" "SELECT id, filepath, title, domain, severity FROM learnings WHERE type='failure'")

# ============================================
# PHASE 3: Check for orphaned heuristic markdown files
# ============================================
echo ""
echo "--- Heuristics: Checking for orphaned markdown files ---"

if [ -d "$HEURISTICS_DIR" ]; then
    for md_file in "$HEURISTICS_DIR"/*.md; do
        [ -f "$md_file" ] || continue
        [ "$(basename "$md_file")" = "TEMPLATE.md" ] && continue

        domain=$(basename "$md_file" .md)
        domain_escaped=$(escape_sql "$domain")

        # Check if domain exists in database
        if ! db_count=$(sqlite_with_retry "$DB_PATH" "SELECT COUNT(*) FROM heuristics WHERE domain='$domain_escaped'"); then
            log_error "Database query failed for domain: $domain"
            ((ERRORS_ENCOUNTERED++))
            continue
        fi

        if [ "$db_count" -eq 0 ]; then
            ((ORPHANED_MD_FILES++))
            report_status "warning" "ORPHANED FILE: memory/heuristics/$domain.md (domain not in DB)"
            log_info "Found orphaned heuristic file: $domain.md"

            if [ "$FIX_MODE" = true ]; then
                # Try YAML format first, then markdown format
                if has_yaml_rule "$md_file"; then
                    if rule_count=$(insert_yaml_heuristic "$md_file"); then
                        report_status "success" "  -> FIXED: Added YAML heuristic to database"
                        ((FIXED_MD_FILES++))
                    else
                        report_status "failure" "  -> FAILED: Could not add YAML heuristic"
                        ((ERRORS_ENCOUNTERED++))
                    fi
                else
                    rule_count=$(insert_markdown_heuristics "$md_file")
                    if [ "$rule_count" -gt 0 ]; then
                        report_status "success" "  -> FIXED: Added $rule_count heuristics to database"
                        ((FIXED_MD_FILES++))
                    else
                        report_status "warning" "  -> SKIPPED: No parseable rules found"
                    fi
                fi
            fi
        fi
    done
else
    log_warn "Heuristics directory does not exist: $HEURISTICS_DIR"
fi

# ============================================
# PHASE 4: Check for orphaned heuristic database records
# ============================================
echo ""
echo "--- Heuristics: Checking database domains without files ---"

while IFS= read -r domain; do
    # Strip carriage return (Windows line endings from sqlite3 on Windows)
    domain="${domain%$'\r'}"
    [ -z "$domain" ] && continue

    domain_file="$HEURISTICS_DIR/${domain}.md"

    if [ ! -f "$domain_file" ]; then
        # Count how many rules for this domain
        domain_escaped=$(escape_sql "$domain")
        if ! rule_count=$(sqlite_with_retry "$DB_PATH" "SELECT COUNT(*) FROM heuristics WHERE domain='$domain_escaped'"); then
            log_error "Database query failed for domain: $domain"
            ((ERRORS_ENCOUNTERED++))
            continue
        fi

        ((ORPHANED_DB_RECORDS++))
        report_status "warning" "ORPHANED DOMAIN: $domain ($rule_count rules in DB, no file)"
        log_info "Found orphaned heuristic domain: $domain"

        if [ "$FIX_MODE" = true ]; then
            # Recreate the file from database
            if cat > "$domain_file" <<EOF
# Heuristics: $domain

Generated from database recovery on $(date +%Y-%m-%d).

---

EOF
            then
                # Add each rule
                while IFS='|' read -r id rule explanation source_type confidence; do
                    cat >> "$domain_file" <<EOF
## H-$id: $rule

**Confidence**: $confidence
**Source**: $source_type

$explanation

---

EOF
                done < <(sqlite_with_retry "$DB_PATH" "SELECT id, rule, explanation, source_type, confidence FROM heuristics WHERE domain='$domain_escaped'")

                report_status "success" "  -> FIXED: Created markdown file with $rule_count rules"
                log_success "Created missing heuristic file: $domain.md"
                ((FIXED_DB_RECORDS++))
            else
                report_status "failure" "  -> FAILED: Could not create markdown file"
                log_error "Failed to create heuristic file: $domain.md"
                ((ERRORS_ENCOUNTERED++))
            fi
        fi
    fi
done < <(sqlite_with_retry "$DB_PATH" "SELECT DISTINCT domain FROM heuristics ORDER BY domain")

# ============================================
# SUMMARY
# ============================================
echo ""
echo "=============================================="
echo "  Summary"
echo "=============================================="
echo "  Orphaned markdown files (not in DB): $ORPHANED_MD_FILES"
echo "  Orphaned database records (no file): $ORPHANED_DB_RECORDS"
echo ""

if [ "$FIX_MODE" = true ]; then
    echo "  Fixed markdown files:    $FIXED_MD_FILES"
    echo "  Fixed database records:  $FIXED_DB_RECORDS"
    echo "  Errors encountered:      $ERRORS_ENCOUNTERED"
    echo ""

    if [ $((FIXED_MD_FILES + FIXED_DB_RECORDS)) -gt 0 ]; then
        report_status "success" "Status: SYNCHRONIZED"
        log_success "Sync completed: fixed $FIXED_MD_FILES files and $FIXED_DB_RECORDS DB records"
    else
        report_status "info" "Status: NO CHANGES NEEDED"
    fi
else
    TOTAL_ISSUES=$((ORPHANED_MD_FILES + ORPHANED_DB_RECORDS))
    if [ "$TOTAL_ISSUES" -gt 0 ]; then
        report_status "warning" "Status: OUT OF SYNC ($TOTAL_ISSUES issues)"
        echo ""
        echo "  Run with --fix to synchronize"
    else
        report_status "success" "Status: SYNCHRONIZED"
    fi
fi

if [ "$ERRORS_ENCOUNTERED" -gt 0 ]; then
    report_status "failure" "Completed with $ERRORS_ENCOUNTERED errors"
    log_error "Sync check completed with errors: $ERRORS_ENCOUNTERED"
    exit "$EXIT_DB_ERROR"
fi

log_success "Sync check completed successfully: $ORPHANED_MD_FILES orphaned files, $ORPHANED_DB_RECORDS orphaned records"
echo ""

exit "$EXIT_SUCCESS"
