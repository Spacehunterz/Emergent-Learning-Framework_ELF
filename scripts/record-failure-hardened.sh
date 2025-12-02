#!/bin/bash
# Agent D Hardened: Record a failure with robust SQLite handling
#
# Enhancements:
# - Longer timeout for database operations (60s)
# - Better retry logic with exponential backoff
# - Type validation for severity
# - Duplicate filepath detection
# - Transaction rollback on failure
# - Database integrity check

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
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [$level] [record-failure-hardened] $*" >> "$LOG_FILE"
    if [ "$level" = "ERROR" ]; then
        echo "ERROR: $*" >&2
    fi
}

# Enhanced SQLite retry with exponential backoff
sqlite_with_retry() {
    local max_attempts=10
    local attempt=1
    local base_delay=0.1

    while [ $attempt -le $max_attempts ]; do
        # Use longer timeout (60 seconds)
        if timeout 60 sqlite3 -cmd ".timeout 60000" "$@" 2>/dev/null; then
            return 0
        fi

        if [ $attempt -lt $max_attempts ]; then
            # Exponential backoff: 0.1, 0.2, 0.4, 0.8, 1.6, 3.2, 6.4...
            local delay=$(awk "BEGIN {print $base_delay * (2 ^ ($attempt - 1))}")
            # Cap at 10 seconds
            delay=$(awk "BEGIN {print ($delay > 10) ? 10 : $delay}")

            log "WARN" "SQLite busy, retry $attempt/$max_attempts after ${delay}s..."
            echo "SQLite busy, retry $attempt/$max_attempts after ${delay}s..." >&2
            sleep "$delay"
        fi

        ((attempt++))
    done

    log "ERROR" "SQLite failed after $max_attempts attempts"
    echo "SQLite failed after $max_attempts attempts" >&2
    return 1
}

# Validate severity input
validate_severity() {
    local sev="$1"

    # Check if numeric 1-5
    if [[ "$sev" =~ ^[1-5]$ ]]; then
        echo "$sev"
        return 0
    fi

    # Check if word
    case "${sev,,}" in  # Convert to lowercase
        low) echo 2 ;;
        medium) echo 3 ;;
        high) echo 4 ;;
        critical) echo 5 ;;
        *)
            log "ERROR" "Invalid severity: $sev (must be 1-5, low, medium, high, or critical)"
            echo "3"  # Default
            return 1
            ;;
    esac
}

# Check for duplicate filepath
check_duplicate_filepath() {
    local filepath="$1"

    local count
    count=$(sqlite_with_retry "$DB_PATH" "SELECT COUNT(*) FROM learnings WHERE filepath='$filepath';")

    if [ "$count" -gt 0 ]; then
        log "ERROR" "Duplicate filepath detected: $filepath"
        echo "ERROR: Filepath already exists in database: $filepath" >&2
        return 1
    fi

    return 0
}

# Pre-flight validation with integrity check
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

    # Database integrity check with timeout
    if ! timeout 30 sqlite3 "$DB_PATH" "PRAGMA integrity_check" 2>/dev/null | grep -q "ok"; then
        log "ERROR" "Database integrity check failed or timed out"
        exit 1
    fi

    # Check if database is in WAL mode (better concurrency)
    local journal_mode
    journal_mode=$(sqlite3 "$DB_PATH" "PRAGMA journal_mode" 2>/dev/null || echo "unknown")
    log "INFO" "Journal mode: $journal_mode"

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

    # Validate and normalize severity
    severity=$(validate_severity "${severity:-3}")

    tags="${tags:-}"
    summary="${summary:-No summary provided}"
    echo "=== Record Failure (non-interactive) ==="
else
    # Interactive mode
    log "INFO" "Running in interactive mode"
    echo "=== Record Failure (Hardened) ==="
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

    read -p "Severity (1-5 or low/medium/high/critical): " severity
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

# Check for duplicate before creating file
if ! check_duplicate_filepath "$relative_path"; then
    echo "ERROR: This failure already exists in the database"
    exit 1
fi

# Create markdown file
cat > "$filepath" <<EOF
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
relative_path_escaped=$(escape_sql "$relative_path")

# Insert into database with transaction and retry logic
if ! LAST_ID=$(sqlite_with_retry "$DB_PATH" <<SQL
BEGIN TRANSACTION;
INSERT INTO learnings (type, filepath, title, summary, tags, domain, severity)
VALUES (
    'failure',
    '$relative_path_escaped',
    '$title_escaped',
    '$summary_escaped',
    '$tags_escaped',
    '$domain_escaped',
    CAST($severity AS INTEGER)
);
SELECT last_insert_rowid();
COMMIT;
SQL
); then
    log "ERROR" "Failed to insert into database"
    # Clean up file
    rm -f "$filepath"
    exit 1
fi

# Validate the ID - must be positive integer
if [ -z "$LAST_ID" ] || [ "$LAST_ID" = "0" ] || ! [[ "$LAST_ID" =~ ^[0-9]+$ ]]; then
    log "ERROR" "Database insert failed - invalid ID: '$LAST_ID'"
    rm -f "$filepath"
    exit 1
fi

echo "Database record created (ID: $LAST_ID)"
log "INFO" "Database record created (ID: $LAST_ID)"

# Git commit (same as before)
cd "$BASE_DIR"
if [ -d ".git" ]; then
    git add "$filepath" "$DB_PATH"
    if git commit -m "failure: $title" -m "Domain: $domain | Severity: $severity" 2>/dev/null; then
        log "INFO" "Git commit created"
        echo "Git commit created"
    else
        log "WARN" "Git commit failed or no changes"
        echo "Note: Git commit skipped"
    fi
fi

log "INFO" "Failure recorded successfully: $title"
echo ""
echo "Failure recorded successfully!"
echo "Edit the full details at: $filepath"
