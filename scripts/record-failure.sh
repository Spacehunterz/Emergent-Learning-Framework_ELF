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

# Setup logging
LOG_FILE="$LOGS_DIR/$(date +%Y%m%d).log"
mkdir -p "$LOGS_DIR"

log() {
    local level="$1"
    shift
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [$level] [record-failure] $*" >> "$LOG_FILE"
    if [ "$level" = "ERROR" ]; then
        echo "ERROR: $*" >&2
    fi
}

# Error trap
trap 'log "ERROR" "Script failed at line $LINENO"; exit 1' ERR

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

    if [ ! -d "$BASE_DIR/.git" ]; then
        log "WARN" "Not a git repository: $BASE_DIR"
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

# Generate filename
date_prefix=$(date +%Y%m%d)
filename_title=$(echo "$title" | tr '[:upper:]' '[:lower:]' | tr ' ' '-' | tr -cd '[:alnum:]-')
filename="${date_prefix}_${filename_title}.md"
filepath="$FAILURES_DIR/$filename"
relative_path="memory/failures/$filename"

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

# Insert into database and get ID in same connection
if ! LAST_ID=$(sqlite3 "$DB_PATH" <<SQL
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

echo "Database record created (ID: $LAST_ID)"
log "INFO" "Database record created (ID: $LAST_ID)"

# Git commit
cd "$BASE_DIR"
if [ -d ".git" ]; then
    git add "$filepath"
    git add "$DB_PATH"
    if ! git commit -m "failure: $title" -m "Domain: $domain | Severity: $severity"; then
        log "WARN" "Git commit failed or no changes to commit"
        echo "Note: Git commit skipped (no changes or already committed)"
    else
        log "INFO" "Git commit created"
        echo "Git commit created"
    fi
else
    log "WARN" "Not a git repository. Skipping commit."
    echo "Warning: Not a git repository. Skipping commit."
fi

log "INFO" "Failure recorded successfully: $title"
echo ""
echo "Failure recorded successfully!"
echo "Edit the full details at: $filepath"
