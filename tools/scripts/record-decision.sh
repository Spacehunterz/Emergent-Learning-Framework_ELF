#!/bin/bash
# Record an Architecture Decision Record (ADR) in the Emergent Learning Framework
#
# Usage (interactive): ./record-decision.sh
# Usage (non-interactive):
#   DECISION_TITLE="title" DECISION_CONTEXT="context" DECISION_DECISION="decision" DECISION_RATIONALE="rationale" ./record-decision.sh
#   Or: ./record-decision.sh --title "title" --context "context" --decision "decision" --rationale "rationale"
#   Optional: --options "options considered" --domain "domain" --files "file1,file2" --tests "test1,test2"

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$(dirname "$SCRIPT_DIR")"
MEMORY_DIR="$BASE_DIR/memory"
DB_PATH="$MEMORY_DIR/index.db"
DECISIONS_DIR="$MEMORY_DIR/decisions"
LOGS_DIR="$BASE_DIR/logs"

# Setup logging
LOG_FILE="$LOGS_DIR/$(date +%Y%m%d).log"
mkdir -p "$LOGS_DIR"

log() {
    local level="$1"
    shift
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [$level] [record-decision] $*" >> "$LOG_FILE"
    if [ "$level" = "ERROR" ]; then
        echo "ERROR: $*" >&2
    fi
}

# Sanitize input: strip control chars, normalize whitespace
sanitize_input() {
    local input="$1"
    # Remove most control characters (keep printable + space/tab)
    # Use POSIX-compatible approach
    input=$(printf '%s' "$input" | tr -cd '[:print:][:space:]')
    # Normalize multiple spaces to single
    input=$(printf '%s' "$input" | tr -s ' ')
    # Trim leading/trailing whitespace
    input=$(echo "$input" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
    printf '%s' "$input"
}

# Check for symlink attacks (TOCTOU protection)
check_symlink_safe() {
    local filepath="$1"
    local dirpath=$(dirname "$filepath")

    if [ -L "$filepath" ]; then
        log "ERROR" "SECURITY: Target is a symlink: $filepath"
        return 1
    fi
    if [ -L "$dirpath" ]; then
        log "ERROR" "SECURITY: Parent directory is a symlink: $dirpath"
        return 1
    fi
    return 0
}

# Check for hardlink attacks
check_hardlink_safe() {
    local filepath="$1"
    [ ! -f "$filepath" ] && return 0

    local link_count
    if command -v stat &> /dev/null; then
        link_count=$(stat -c '%h' "$filepath" 2>/dev/null || stat -f '%l' "$filepath" 2>/dev/null)
    fi

    if [ -n "$link_count" ] && [ "$link_count" -gt 1 ]; then
        log "ERROR" "SECURITY: File has $link_count hardlinks: $filepath"
        return 1
    fi
    return 0
}

# Input length limits
MAX_TITLE_LENGTH=200
MAX_CONTEXT_LENGTH=5000
MAX_OPTIONS_LENGTH=5000
MAX_DECISION_LENGTH=5000
MAX_RATIONALE_LENGTH=5000
MAX_DOMAIN_LENGTH=100
MAX_FILES_LENGTH=1000
MAX_TESTS_LENGTH=1000

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

# Ensure decisions directory exists
mkdir -p "$DECISIONS_DIR"

log "INFO" "Script started"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --title) title="$2"; shift 2 ;;
        --context) context="$2"; shift 2 ;;
        --options) options="$2"; shift 2 ;;
        --decision) decision="$2"; shift 2 ;;
        --rationale) rationale="$2"; shift 2 ;;
        --domain) domain="$2"; shift 2 ;;
        --files) files="$2"; shift 2 ;;
        --tests) tests="$2"; shift 2 ;;
        *) shift ;;
    esac
done

# Check for environment variables
title="${title:-$DECISION_TITLE}"
context="${context:-$DECISION_CONTEXT}"
options="${options:-$DECISION_OPTIONS}"
decision="${decision:-$DECISION_DECISION}"
rationale="${rationale:-$DECISION_RATIONALE}"
domain="${domain:-$DECISION_DOMAIN}"
files="${files:-$DECISION_FILES}"
tests="${tests:-$DECISION_TESTS}"

# Non-interactive mode: if we have required fields, skip prompts
if [ -n "$title" ] && [ -n "$context" ] && [ -n "$decision" ] && [ -n "$rationale" ]; then
    log "INFO" "Running in non-interactive mode"
    options="${options:-}"
    domain="${domain:-general}"
    files="${files:-}"
    tests="${tests:-}"
    echo "=== Record Decision (non-interactive) ==="
elif [ ! -t 0 ]; then
    # Not a terminal and no args provided - show usage and exit gracefully
    log "INFO" "No terminal attached and no arguments provided - showing usage"
    echo "Usage (non-interactive):"
    echo "  $0 --title \"Decision title\" --context \"Why needed\" --decision \"What was chosen\" --rationale \"Why chosen\""
    echo "  Optional: --options \"Options considered\" --domain \"domain\" --files \"file1,file2\" --tests \"test1,test2\""
    echo ""
    echo "Or set environment variables:"
    echo "  DECISION_TITLE=\"title\" DECISION_CONTEXT=\"context\" DECISION_DECISION=\"decision\" DECISION_RATIONALE=\"rationale\" $0"
    exit 0
else
    # Interactive mode (terminal attached)
    log "INFO" "Running in interactive mode"
    echo "=== Record Architecture Decision ==="
    echo ""

    read -p "Decision Title: " title
    if [ -z "$title" ]; then
        log "ERROR" "Title cannot be empty"
        exit 1
    fi

    read -p "Context (why was this decision needed?): " context
    if [ -z "$context" ]; then
        log "ERROR" "Context cannot be empty"
        exit 1
    fi

    read -p "Options Considered (optional): " options

    read -p "Decision (what was chosen): " decision
    if [ -z "$decision" ]; then
        log "ERROR" "Decision cannot be empty"
        exit 1
    fi

    read -p "Rationale (why was it chosen): " rationale
    if [ -z "$rationale" ]; then
        log "ERROR" "Rationale cannot be empty"
        exit 1
    fi

    read -p "Domain (optional, default: general): " domain
    if [ -z "$domain" ]; then
        domain="general"
    fi

    read -p "Files Touched (comma-separated, optional): " files
    read -p "Tests Added (comma-separated, optional): " tests
fi

# Sanitize domain to prevent path traversal
domain_safe=$(echo "$domain" | tr '[:upper:]' '[:lower:]' | tr ' ' '-' | tr -cd '[:alnum:]-')
domain_safe="${domain_safe#-}"
domain_safe="${domain_safe%-}"
domain_safe="${domain_safe:0:100}"
if [ -z "$domain_safe" ]; then
    log "ERROR" "Domain resulted in empty string after sanitization"
    exit 1
fi
domain="$domain_safe"

# Input length validation
if [ ${#title} -gt $MAX_TITLE_LENGTH ]; then
    log "ERROR" "Title exceeds maximum length ($MAX_TITLE_LENGTH chars)"
    echo "ERROR: Title too long (max $MAX_TITLE_LENGTH characters)" >&2
    exit 1
fi
if [ ${#context} -gt $MAX_CONTEXT_LENGTH ]; then
    log "ERROR" "Context exceeds maximum length"
    echo "ERROR: Context too long (max $MAX_CONTEXT_LENGTH characters)" >&2
    exit 1
fi
if [ ${#options} -gt $MAX_OPTIONS_LENGTH ]; then
    log "ERROR" "Options exceeds maximum length"
    echo "ERROR: Options too long (max $MAX_OPTIONS_LENGTH characters)" >&2
    exit 1
fi
if [ ${#decision} -gt $MAX_DECISION_LENGTH ]; then
    log "ERROR" "Decision exceeds maximum length"
    echo "ERROR: Decision too long (max $MAX_DECISION_LENGTH characters)" >&2
    exit 1
fi
if [ ${#rationale} -gt $MAX_RATIONALE_LENGTH ]; then
    log "ERROR" "Rationale exceeds maximum length"
    echo "ERROR: Rationale too long (max $MAX_RATIONALE_LENGTH characters)" >&2
    exit 1
fi
if [ ${#files} -gt $MAX_FILES_LENGTH ]; then
    log "ERROR" "Files list exceeds maximum length"
    echo "ERROR: Files list too long (max $MAX_FILES_LENGTH characters)" >&2
    exit 1
fi
if [ ${#tests} -gt $MAX_TESTS_LENGTH ]; then
    log "ERROR" "Tests list exceeds maximum length"
    echo "ERROR: Tests list too long (max $MAX_TESTS_LENGTH characters)" >&2
    exit 1
fi

# Sanitize inputs (strip ANSI, control chars)
title=$(sanitize_input "$title")
context=$(sanitize_input "$context")
options=$(sanitize_input "$options")
decision=$(sanitize_input "$decision")
rationale=$(sanitize_input "$rationale")
files=$(sanitize_input "$files")
tests=$(sanitize_input "$tests")

log "INFO" "Recording decision: $title (domain: $domain)"

# Escape single quotes for SQL
escape_sql() {
    echo "${1//\'/\'\'}"
}

title_escaped=$(escape_sql "$title")
context_escaped=$(escape_sql "$context")
options_escaped=$(escape_sql "$options")
decision_escaped=$(escape_sql "$decision")
rationale_escaped=$(escape_sql "$rationale")
domain_escaped=$(escape_sql "$domain")
files_escaped=$(escape_sql "$files")
tests_escaped=$(escape_sql "$tests")

# Insert into database with retry logic for concurrent access
if ! decision_id=$(sqlite_with_retry "$DB_PATH" <<SQL
INSERT INTO decisions (title, context, options_considered, decision, rationale, domain, files_touched, tests_added)
VALUES (
    '$title_escaped',
    '$context_escaped',
    '$options_escaped',
    '$decision_escaped',
    '$rationale_escaped',
    '$domain_escaped',
    '$files_escaped',
    '$tests_escaped'
);
SELECT last_insert_rowid();
SQL
); then
    log "ERROR" "Failed to insert into database"
    exit 1
fi

echo "Database record created (ID: $decision_id)"
log "INFO" "Database record created (ID: $decision_id)"

# Create markdown file with ADR format
current_date=$(date +%Y-%m-%d)
title_slug=$(echo "$title" | tr '[:upper:]' '[:lower:]' | tr ' ' '-' | tr -cd '[:alnum:]-' | cut -c1-50)
decision_file="$DECISIONS_DIR/${current_date}-${title_slug}.md"

# Security checks before file write
if ! check_symlink_safe "$decision_file"; then
    exit 6
fi
if ! check_hardlink_safe "$decision_file"; then
    exit 6
fi

# Create the ADR markdown file
# Build the markdown content programmatically to handle arrays correctly
{
    echo "# ADR-${decision_id}: ${title}"
    echo ""
    echo "**Date**: ${current_date}"
    echo "**Domain**: ${domain}"
    echo "**Status**: Accepted"
    echo ""
    echo "---"
    echo ""
    echo "## Context"
    echo ""
    echo "${context}"
    echo ""

    if [ -n "$options" ]; then
        echo "## Options Considered"
        echo ""
        echo "$options"
        echo ""
    fi

    echo "## Decision"
    echo ""
    echo "${decision}"
    echo ""
    echo "## Rationale"
    echo ""
    echo "${rationale}"
    echo ""

    if [ -n "$files" ]; then
        echo "## Files Touched"
        echo ""
        IFS=',' read -ra FILE_ARRAY <<< "$files"
        for file in "${FILE_ARRAY[@]}"; do
            file_trimmed=$(echo "$file" | xargs)
            echo "- $file_trimmed"
        done
        echo ""
    fi

    if [ -n "$tests" ]; then
        echo "## Tests Added"
        echo ""
        IFS=',' read -ra TEST_ARRAY <<< "$tests"
        for test in "${TEST_ARRAY[@]}"; do
            test_trimmed=$(echo "$test" | xargs)
            echo "- $test_trimmed"
        done
        echo ""
    fi

    echo "## Consequences"
    echo ""
    echo "- This decision establishes a pattern for future similar situations"
    echo "- Related architectural decisions should reference this ADR"
    echo "- If context changes, this decision should be revisited"
    echo ""
    echo "---"
    echo ""
    echo "**ID**: ADR-${decision_id}"
    echo "**Created**: ${current_date}"
} > "$decision_file"

echo "Created decision file: $decision_file"
log "INFO" "Created decision file: $decision_file"

# NOTE: Auto-commit removed for safety (can grab unrelated staged files)
# User should commit manually if desired:
#   git add memory/decisions/ memory/index.db && git commit -m "decision: <description>"

log "INFO" "Decision recorded successfully: $title"
echo ""
echo "Decision recorded successfully!"
echo "ADR-${decision_id}: ${title}"
echo "File: $decision_file"
