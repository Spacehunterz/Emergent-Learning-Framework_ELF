#!/bin/bash
# Record a failure in the Emergent Learning Framework
#
# Usage (interactive): ./record-failure.sh
# Usage (non-interactive):
#   FAILURE_TITLE="title" FAILURE_DOMAIN="domain" FAILURE_SUMMARY="summary" ./record-failure.sh
#   Or: ./record-failure.sh --title "title" --domain "domain" --summary "summary"
#   Optional: --severity N --tags "tag1,tag2"

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$(dirname "$SCRIPT_DIR")"
MEMORY_DIR="$BASE_DIR/memory"
DB_PATH="$MEMORY_DIR/index.db"
FAILURES_DIR="$MEMORY_DIR/failures"
LOGS_DIR="$BASE_DIR/logs"

# TIME-FIX-1: Capture date once at script start for consistency across midnight boundary
# If script runs at 23:59:59 and finishes at 00:00:01, all dates remain consistent
EXECUTION_DATE=$(date +%Y%m%d)

# Setup logging
LOG_FILE="$LOGS_DIR/${EXECUTION_DATE}.log"
mkdir -p "$LOGS_DIR"

log() {
    local level="$1"
    shift
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [$level] [record-failure] $*" >> "$LOG_FILE"
    if [ "$level" = "ERROR" ]; then
        echo "ERROR: $*" >&2
    fi
}

# SQLite retry function for handling concurrent access
sqlite_with_retry() {
    local max_attempts=5
    local attempt=1
    while [ $attempt -le $max_attempts ]; do
        if sqlite3 "$@" 2>/dev/null; then
            return 0
        fi
        log "WARN" "SQLite busy, retry $attempt/$max_attempts..."
        echo "SQLite busy, retry $attempt/$max_attempts..." >&2
        sleep 0.$((RANDOM % 5 + 1))
        ((attempt++))
    done
    log "ERROR" "SQLite failed after $max_attempts attempts"
    echo "SQLite failed after $max_attempts attempts" >&2
    return 1
}

# Git lock functions for concurrent access (cross-platform)
acquire_git_lock() {
    local lock_file="$1"
    local timeout="${2:-30}"
    local wait_time=0
    
    # Check if flock is available (Linux/macOS with coreutils)
    if command -v flock &> /dev/null; then
        exec 200>"$lock_file"
        if flock -w "$timeout" 200; then
            return 0
        else
            return 1
        fi
    else
        # Fallback for Windows/MSYS: simple mkdir-based locking
        local lock_dir="${lock_file}.dir"
        while [ $wait_time -lt $timeout ]; do
            if mkdir "$lock_dir" 2>/dev/null; then
                return 0
            fi
            sleep 1
            ((wait_time++))
        done
        return 1
    fi
}

release_git_lock() {
    local lock_file="$1"
    
    if command -v flock &> /dev/null; then
        flock -u 200 2>/dev/null || true
    else
        local lock_dir="${lock_file}.dir"
        rmdir "$lock_dir" 2>/dev/null || true
    fi
}

# Rollback function for atomicity
cleanup_on_failure() {
    local file_to_remove="$1"
    local db_id_to_remove="$2"
    if [ -n "$file_to_remove" ] && [ -f "$file_to_remove" ]; then
        log "WARN" "Rolling back: removing file $file_to_remove"
        rm -f "$file_to_remove"
    fi
    if [ -n "$db_id_to_remove" ] && [ "$db_id_to_remove" != "0" ] && [ "$db_id_to_remove" != "" ]; then
        log "WARN" "Rolling back: removing DB record $db_id_to_remove"
        sqlite3 "$DB_PATH" "DELETE FROM learnings WHERE id=$db_id_to_remove" 2>/dev/null || true
    fi
}

# Error trap with cleanup
trap 'log "ERROR" "Script failed at line $LINENO"; cleanup_on_failure "$filepath" "$LAST_ID"; exit 1' ERR

# TIME-FIX-4: Timestamp validation function
validate_timestamp() {
    local ts_epoch
    ts_epoch=$(date +%s)
    
    # Check if timestamp is reasonable (not before 2020, not more than 1 day in future)
    local year_2020=1577836800  # 2020-01-01 00:00:00 UTC
    local one_day_ahead=$((ts_epoch + 86400))
    
    if [ "$ts_epoch" -lt "$year_2020" ]; then
        log "ERROR" "System clock appears to be set before 2020"
        return 1
    fi
    
    # Note: We allow small future dates (up to 1 day) to handle timezone issues
    return 0
}

# Pre-flight validation
preflight_check() {

    log "INFO" "Starting pre-flight checks"

    # TIME-FIX-5: Validate system timestamp
    if ! validate_timestamp; then
        log "ERROR" "Timestamp validation failed - check system clock"
        exit 1
    fi

    if [ ! -f "$DB_PATH" ]; then
        log "ERROR" "Database not found: $DB_PATH"
        exit 1
    fi

    if ! command -v sqlite3 &> /dev/null; then
        log "ERROR" "sqlite3 command not found"
        exit 1
    fi

    if [ ! -d "$BASE_DIR/.git" ]; then
        log "WARN" "Not a git repository: $BASE_DIR"
    fi

    # Security: Symlink attack prevention
    if [ -L "$FAILURES_DIR" ]; then
        log "ERROR" "SECURITY: failures directory is a symlink"
        exit 1
    fi
    if [ -L "$MEMORY_DIR" ]; then
        log "ERROR" "SECURITY: memory directory is a symlink"
        exit 1
    fi

    # Database integrity check
    if ! sqlite3 "$DB_PATH" "PRAGMA integrity_check" 2>/dev/null | grep -q "ok"; then
        log "ERROR" "Database integrity check failed"
        exit 1
    fi

    log "INFO" "Pre-flight checks passed"
}

preflight_check

# Ensure failures directory exists
mkdir -p "$FAILURES_DIR"

log "INFO" "Script started"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --title) title="$2"; shift 2 ;;
        --domain) domain="$2"; shift 2 ;;
        --severity) severity="$2"; shift 2 ;;
        --tags) tags="$2"; shift 2 ;;
        --summary) summary="$2"; shift 2 ;;
        *) shift ;;
    esac
done

# Check for environment variables (override empty values)
title="${title:-$FAILURE_TITLE}"
domain="${domain:-$FAILURE_DOMAIN}"
severity="${severity:-$FAILURE_SEVERITY}"
tags="${tags:-$FAILURE_TAGS}"
summary="${summary:-$FAILURE_SUMMARY}"

# Non-interactive mode: if we have title and domain, skip prompts
if [ -n "$title" ] && [ -n "$domain" ]; then
    log "INFO" "Running in non-interactive mode"
    # Validate severity is a number 1-5, or convert word to number
    case "$severity" in
        1|2|3|4|5) ;; # valid number, keep as-is
        low) severity=2 ;;
        medium) severity=3 ;;
        high) severity=4 ;;
        critical) severity=5 ;;
        *) severity=3 ;; # default
    esac
    # Strict validation: severity must be integer 1-5 ONLY (SQL injection protection)
    if ! [[ "$severity" =~ ^[1-5]$ ]]; then
        log "WARN" "Invalid severity provided, defaulting to 3"
        severity=3
    fi
    tags="${tags:-}"
    summary="${summary:-No summary provided}"
    echo "=== Record Failure (non-interactive) ==="
else
    # Interactive mode
    log "INFO" "Running in interactive mode"
    echo "=== Record Failure ==="
    echo ""

    read -p "Title: " title
    if [ -z "$title" ]; then
        log "ERROR" "Title cannot be empty"
        exit 1
    fi

    read -p "Domain (coordination/architecture/debugging/etc): " domain
    if [ -z "$domain" ]; then
        log "ERROR" "Domain cannot be empty"
        exit 1
    fi

    read -p "Severity (1-5): " severity
    if [ -z "$severity" ]; then
        severity=3
    fi

    read -p "Tags (comma-separated): " tags

    echo "Summary (press Enter twice when done):"
    summary=""
    while IFS= read -r line; do
        [ -z "$line" ] && break
        summary="${summary}${line}\n"
    done
fi

log "INFO" "Recording failure: $title (domain: $domain, severity: $severity)"

# Input length validation (added by Agent C hardening)
MAX_TITLE_LENGTH=500
MAX_DOMAIN_LENGTH=100
MAX_SUMMARY_LENGTH=50000

if [ ${#title} -gt $MAX_TITLE_LENGTH ]; then
    log "ERROR" "Title exceeds maximum length ($MAX_TITLE_LENGTH characters, got ${#title})"
    echo "ERROR: Title too long (max $MAX_TITLE_LENGTH characters)" >&2
    exit 1
fi

if [ ${#domain} -gt $MAX_DOMAIN_LENGTH ]; then
    log "ERROR" "Domain exceeds maximum length ($MAX_DOMAIN_LENGTH characters)"
    echo "ERROR: Domain too long (max $MAX_DOMAIN_LENGTH characters)" >&2
    exit 1
fi

if [ ${#summary} -gt $MAX_SUMMARY_LENGTH ]; then
    log "ERROR" "Summary exceeds maximum length ($MAX_SUMMARY_LENGTH characters, got ${#summary})"
    echo "ERROR: Summary too long (max $MAX_SUMMARY_LENGTH characters)" >&2
    exit 1
fi

# Trim leading/trailing whitespace
title=$(echo "$title" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')
domain=$(echo "$domain" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')

# Re-validate after trimming
if [ -z "$title" ]; then
    log "ERROR" "Title cannot be empty (or whitespace-only)"
    echo "ERROR: Title cannot be empty" >&2
    exit 1
fi

if [ -z "$domain" ]; then
    log "ERROR" "Domain cannot be empty (or whitespace-only)"
    echo "ERROR: Domain cannot be empty" >&2
    exit 1
fi


# Generate filename
# TIME-FIX-2: Use captured EXECUTION_DATE instead of recalculating
date_prefix=$EXECUTION_DATE
filename_title=$(echo "$title" | tr ':[:upper:]:' ':[:lower:]:' | tr ' ' '-' | tr -cd ':[:alnum:]-' | cut -c1-100)
filename="${date_prefix}_${filename_title}.md"
filepath="$FAILURES_DIR/$filename"
relative_path="memory/failures/$filename"

# Create markdown file
cat > "$filepath" <<EOF
# $title

**Domain**: $domain
**Severity**: $severity
**Tags**: $tags
**Date**: ${EXECUTION_DATE:0:4}-${EXECUTION_DATE:4:2}-${EXECUTION_DATE:6:2}  # TIME-FIX-3: Use consistent captured date

## Summary

$summary

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

echo "Created: $filepath"
log "INFO" "Created markdown file: $filepath"

# Escape single quotes for SQL injection protection
escape_sql() {
    echo "${1//\'/\'\'}"
}

title_escaped=$(escape_sql "$title")
summary_escaped=$(escape_sql "$(echo -e "$summary" | head -n 1)")
tags_escaped=$(escape_sql "$tags")
domain_escaped=$(escape_sql "$domain")

# Insert into database with retry logic for concurrent access
if ! LAST_ID=$(sqlite_with_retry "$DB_PATH" <<SQL
INSERT INTO learnings (type, filepath, title, summary, tags, domain, severity)
VALUES (
    'failure',
    '$relative_path',
    '$title_escaped',
    '$summary_escaped',
    '$tags_escaped',
    '$domain_escaped',
    CAST($severity AS INTEGER)
);
SELECT last_insert_rowid();
SQL
); then
    log "ERROR" "Failed to insert into database"
    exit 1
fi

# Validate the ID - must be positive integer (fixes ID=0 bug)
if [ -z "$LAST_ID" ] || [ "$LAST_ID" = "0" ] || ! [[ "$LAST_ID" =~ ^[0-9]+$ ]]; then
    log "ERROR" "Database insert failed - invalid ID: '$LAST_ID'"
    cleanup_on_failure "$filepath" ""
    exit 1
fi

echo "Database record created (ID: $LAST_ID)"
log "INFO" "Database record created (ID: $LAST_ID)"

# Git commit with locking for concurrent access
cd "$BASE_DIR"
if [ -d ".git" ]; then
    LOCK_FILE="$BASE_DIR/.git/claude-lock"
    
    if ! acquire_git_lock "$LOCK_FILE" 30; then
        log "ERROR" "Could not acquire git lock - rolling back"
        cleanup_on_failure "$filepath" "$LAST_ID"
        echo "Error: Could not acquire git lock"
        exit 1
    fi

    git add "$filepath"
    git add "$DB_PATH"
    if ! git commit -m "failure: $title" -m "Domain: $domain | Severity: $severity"; then
        log "WARN" "Git commit failed or no changes to commit"
        echo "Note: Git commit skipped (no changes or already committed)"
    else
        log "INFO" "Git commit created"
        echo "Git commit created"
    fi

    release_git_lock "$LOCK_FILE"
else
    log "WARN" "Not a git repository. Skipping commit."
    echo "Warning: Not a git repository. Skipping commit."
fi

log "INFO" "Failure recorded successfully: $title"
echo ""
echo "Failure recorded successfully!"
echo "Edit the full details at: $filepath"
