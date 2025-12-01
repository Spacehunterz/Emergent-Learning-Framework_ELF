#!/bin/bash
# Record a failure in the Emergent Learning Framework - V2 with rollback
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$(dirname "$SCRIPT_DIR")"
MEMORY_DIR="$BASE_DIR/memory"
DB_PATH="$MEMORY_DIR/index.db"
FAILURES_DIR="$MEMORY_DIR/failures"
LOGS_DIR="$BASE_DIR/logs"

readonly SCRIPT_START_TIME=$(date +%Y%m%d)
LOG_FILE="$LOGS_DIR/${SCRIPT_START_TIME}.log"
mkdir -p "$LOGS_DIR"

readonly CORRELATION_ID="${HOSTNAME:-unknown}-$$-$(date +%s)"

log() {
    local level="$1"; shift
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [$level] [record-failure] [cid=$CORRELATION_ID] $*" >> "$LOG_FILE"
    [ "$level" = "ERROR" ] && echo "ERROR: $*" >&2
}

sqlite_atomic_insert() {
    local db="$1" sql="$2" max_attempts=5 attempt=1 result=""
    while [ $attempt -le $max_attempts ]; do
        result=$(sqlite3 "$db" "PRAGMA busy_timeout=5000; BEGIN IMMEDIATE; $sql COMMIT;" 2>&1) && { echo "$result"; return 0; }
        log "WARN" "SQLite busy, retry $attempt/$max_attempts"
        sleep 0.$((RANDOM % 5 + 1))
        ((attempt++))
    done
    log "ERROR" "SQLite failed: $result"; return 1
}

acquire_git_lock() {
    local lock_file="$1" timeout="${2:-30}" wait_time=0
    if command -v flock &>/dev/null; then
        exec 200>"$lock_file" && flock -w "$timeout" 200
    else
        local lock_dir="${lock_file}.dir"
        while [ $wait_time -lt $timeout ]; do
            mkdir "$lock_dir" 2>/dev/null && return 0
            sleep 1; ((wait_time++))
        done
        return 1
    fi
}

release_git_lock() {
    local lock_file="$1"
    command -v flock &>/dev/null && { flock -u 200 2>/dev/null || true; } || rmdir "${lock_file}.dir" 2>/dev/null || true
}

cleanup_on_failure() {
    [ -n "$1" ] && [ -f "$1" ] && { log "WARN" "Rolling back file: $1"; rm -f "$1"; }
    [ -n "$2" ] && [ "$2" != "0" ] && { log "WARN" "Rolling back DB ID: $2"; sqlite3 "$DB_PATH" "DELETE FROM learnings WHERE id=$2" 2>/dev/null || true; }
}

trap 'log "ERROR" "Failed at line $LINENO"; cleanup_on_failure "$filepath" "$LAST_ID"; exit 1' ERR

preflight_check() {
    log "INFO" "Pre-flight checks"
    [ ! -f "$DB_PATH" ] && { log "ERROR" "DB not found"; exit 1; }
    command -v sqlite3 &>/dev/null || { log "ERROR" "sqlite3 not found"; exit 1; }
    [ -L "$FAILURES_DIR" ] && { log "ERROR" "SECURITY: failures is symlink"; exit 1; }
    [ -L "$MEMORY_DIR" ] && { log "ERROR" "SECURITY: memory is symlink"; exit 1; }
    sqlite3 "$DB_PATH" "PRAGMA integrity_check" 2>/dev/null | grep -q "ok" || { log "ERROR" "DB integrity failed"; exit 1; }
    log "INFO" "Pre-flight passed"
}

preflight_check
mkdir -p "$FAILURES_DIR"
log "INFO" "Script started"

while [[ $# -gt 0 ]]; do
    case $1 in
        --title) title="$2"; shift 2 ;; --domain) domain="$2"; shift 2 ;;
        --severity) severity="$2"; shift 2 ;; --tags) tags="$2"; shift 2 ;;
        --summary) summary="$2"; shift 2 ;; *) shift ;;
    esac
done

title="${title:-$FAILURE_TITLE}"; domain="${domain:-$FAILURE_DOMAIN}"
severity="${severity:-$FAILURE_SEVERITY}"; tags="${tags:-$FAILURE_TAGS}"
summary="${summary:-$FAILURE_SUMMARY}"

if [ -n "$title" ] && [ -n "$domain" ]; then
    log "INFO" "Non-interactive mode"
    case "$severity" in 1|2|3|4|5) ;; low) severity=2 ;; medium) severity=3 ;; high) severity=4 ;; critical) severity=5 ;; *) severity=3 ;; esac
    [[ "$severity" =~ ^[1-5]$ ]] || severity=3
    summary="${summary:-No summary}"
    echo "=== Record Failure (non-interactive) ==="
else
    log "INFO" "Interactive mode"
    echo "=== Record Failure ===" && echo ""
    read -p "Title: " title; [ -z "$title" ] && { log "ERROR" "Empty title"; exit 1; }
    read -p "Domain: " domain; [ -z "$domain" ] && { log "ERROR" "Empty domain"; exit 1; }
    read -p "Severity (1-5): " severity; [ -z "$severity" ] && severity=3
    read -p "Tags: " tags
    echo "Summary (Enter twice when done):"; summary=""
    while IFS= read -r line; do [ -z "$line" ] && break; summary="${summary}${line}\n"; done
fi

log "INFO" "Recording: $title (domain: $domain, severity: $severity)"

title_sanitized=$(echo "$title" | tr '\n\r' '  ' | tr -d '\000-\037')
date_prefix=$(date +%Y%m%d)
filename_title=$(echo "$title_sanitized" | tr '[:upper:]' '[:lower:]' | tr ' ' '-' | tr -cd '[:alnum:]-' | head -c 100)
[ -z "$filename_title" ] && filename_title=$(echo "$title" | md5sum | cut -c1-12)

filename="${date_prefix}_${filename_title}.md"
filepath="$FAILURES_DIR/$filename"
relative_path="memory/failures/$filename"
[ -f "$filepath" ] && { filename="${date_prefix}_${filename_title}_$(date +%H%M%S).md"; filepath="$FAILURES_DIR/$filename"; relative_path="memory/failures/$filename"; log "WARN" "Collision, appended timestamp"; }

cat > "$filepath" <<EOF
# $title_sanitized

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
log "INFO" "Created markdown: $filepath"

escape_sql() { local s="$1"; echo "${s//''/''''}"; }
title_escaped=$(escape_sql "$title_sanitized")
summary_escaped=$(escape_sql "$(echo -e "$summary" | head -n 1)")
tags_escaped=$(escape_sql "$tags")
domain_escaped=$(escape_sql "$domain")

LAST_ID=$(sqlite_atomic_insert "$DB_PATH" "INSERT INTO learnings (type,filepath,title,summary,tags,domain,severity) VALUES('failure','$relative_path','$title_escaped','$summary_escaped','$tags_escaped','$domain_escaped',CAST($severity AS INTEGER)); SELECT last_insert_rowid();")

if [ -z "$LAST_ID" ] || [ "$LAST_ID" = "0" ] || ! [[ "$LAST_ID" =~ ^[0-9]+$ ]]; then
    log "ERROR" "Invalid ID: $LAST_ID"; cleanup_on_failure "$filepath" ""; exit 1
fi

echo "DB record created (ID: $LAST_ID)"
log "INFO" "DB record ID: $LAST_ID"

cd "$BASE_DIR"
if [ -d ".git" ]; then
    LOCK_FILE="$BASE_DIR/.git/claude-lock"
    acquire_git_lock "$LOCK_FILE" 30 || { log "ERROR" "Git lock failed - rolling back"; cleanup_on_failure "$filepath" "$LAST_ID"; exit 1; }
    git add "$filepath" "$DB_PATH"
    git commit -m "failure: $title_sanitized" -m "Domain: $domain | Severity: $severity" 2>/dev/null && { log "INFO" "Git committed"; echo "Git commit created"; } || { log "WARN" "Git commit skipped"; echo "Note: Git commit skipped"; }
    release_git_lock "$LOCK_FILE"
else
    log "WARN" "Not a git repo"
fi

log "INFO" "Success: $title_sanitized (ID: $LAST_ID)"
echo ""; echo "Failure recorded successfully!"
echo "Edit: $filepath"
