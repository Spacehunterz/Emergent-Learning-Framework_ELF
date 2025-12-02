#!/bin/bash
# Record a failure in the Emergent Learning Framework - V3 with Concurrency Improvements
#
# Usage (interactive): ./record-failure-v3.sh
# Usage (non-interactive):
#   FAILURE_TITLE="title" FAILURE_DOMAIN="domain" FAILURE_SUMMARY="summary" ./record-failure-v3.sh
#   Or: ./record-failure-v3.sh --title "title" --domain "domain" --summary "summary"
#   Optional: --severity N --tags "tag1,tag2"

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$(dirname "$SCRIPT_DIR")"
MEMORY_DIR="$BASE_DIR/memory"
DB_PATH="$MEMORY_DIR/index.db"
FAILURES_DIR="$MEMORY_DIR/failures"
LOGS_DIR="$BASE_DIR/logs"

# Setup logging
LOG_FILE="$LOGS_DIR/$(date +%Y%m%d).log"
mkdir -p "$LOGS_DIR"

log() {
    local level="$1"
    shift
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [$level] [record-failure-v3] $*" >> "$LOG_FILE"
    if [ "$level" = "ERROR" ]; then
        echo "ERROR: $*" >&2
    fi
}

# Source concurrency library
CONCURRENCY_LIB="$SCRIPT_DIR/lib/concurrency.sh"
if [ -f "$CONCURRENCY_LIB" ]; then
    source "$CONCURRENCY_LIB"
else
    log "ERROR" "Concurrency library not found: $CONCURRENCY_LIB"
    echo "ERROR: Concurrency library not found"
    exit 1
fi

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

# Pre-flight validation
preflight_check() {
    log "INFO" "Starting pre-flight checks"

    if [ ! -f "$DB_PATH" ]; then
        log "ERROR" "Database not found: $DB_PATH"
        exit 1
    fi

    if ! command -v sqlite3 &> /dev/null; then
        log "ERROR" "sqlite3 command not found"
        exit 1
    fi

    if ! command -v awk &> /dev/null; then
        log "ERROR" "awk command not found (required for backoff)"
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
    severity=$(validate_severity "${severity:-3}")
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
    severity=$(validate_severity "${severity:-3}")

    read -p "Tags (comma-separated): " tags

    echo "Summary (press Enter twice when done):"
    summary=""
    while IFS= read -r line; do
        [ -z "$line" ] && break
        summary="${summary}${line}\n"
    done
fi

log "INFO" "Recording failure: $title (domain: $domain, severity: $severity)"

# Generate filename
date_prefix=$(date +%Y%m%d)
filename_title=$(echo "$title" | tr '[:upper:]' '[:lower:]' | tr ' ' '-' | tr -cd '[:alnum:]-')
filename="${date_prefix}_${filename_title}.md"
filepath="$FAILURES_DIR/$filename"
relative_path="memory/failures/$filename"

# Create markdown content
markdown_content=$(cat <<EOF
# $title

**Domain**: $domain
**Severity**: $severity
**Tags**: $tags
**Date**: $(date +%Y-%m-%d)

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
)

# Write markdown file atomically
if ! write_atomic "$filepath" "$markdown_content"; then
    log "ERROR" "Failed to write markdown file"
    exit 1
fi

echo "Created: $filepath"
log "INFO" "Created markdown file: $filepath"

# Escape for SQL
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
    cleanup_on_failure "$filepath" ""
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

# Git commit with improved locking
cd "$BASE_DIR"
if [ -d ".git" ]; then
    LOCK_FILE="$BASE_DIR/.git/claude-lock"

    if ! acquire_git_lock "$LOCK_FILE" 10; then
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
