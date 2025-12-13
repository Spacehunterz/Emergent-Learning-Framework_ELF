#!/bin/bash
# Record a Spike Report in the Emergent Learning Framework
#
# Spike Reports capture research/investigation knowledge that would otherwise die with the session.
#
# Usage (interactive): ./record-spike.sh
# Usage (non-interactive):
#   SPIKE_TITLE="title" SPIKE_TOPIC="topic" SPIKE_QUESTION="question" SPIKE_FINDINGS="findings" ./record-spike.sh
#   Or: ./record-spike.sh --title "title" --topic "topic" --question "question" --findings "findings"
#   Optional: --gotchas "gotchas" --resources "urls" --time 30 --domain "domain" --tags "tag1,tag2"

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$(dirname "$SCRIPT_DIR")"
MEMORY_DIR="$BASE_DIR/memory"
DB_PATH="$MEMORY_DIR/index.db"
SPIKES_DIR="$MEMORY_DIR/spikes"
LOGS_DIR="$BASE_DIR/logs"

# Setup logging
LOG_FILE="$LOGS_DIR/$(date +%Y%m%d).log"
mkdir -p "$LOGS_DIR"

log() {
    local level="$1"
    shift
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [$level] [record-spike] $*" >> "$LOG_FILE"
    if [ "$level" = "ERROR" ]; then
        echo "ERROR: $*" >&2
    fi
}

# Sanitize input: strip control chars, normalize whitespace
sanitize_input() {
    local input="$1"
    # Remove most control characters (keep printable + space/tab)
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

# Input length limits
MAX_TITLE_LENGTH=200
MAX_TOPIC_LENGTH=500
MAX_QUESTION_LENGTH=2000
MAX_FINDINGS_LENGTH=10000
MAX_GOTCHAS_LENGTH=5000
MAX_RESOURCES_LENGTH=2000
MAX_DOMAIN_LENGTH=100
MAX_TAGS_LENGTH=500

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

    log "INFO" "Pre-flight checks passed"
}

preflight_check

# Ensure spikes directory exists
mkdir -p "$SPIKES_DIR"

log "INFO" "Script started"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --title) title="$2"; shift 2 ;;
        --topic) topic="$2"; shift 2 ;;
        --question) question="$2"; shift 2 ;;
        --findings) findings="$2"; shift 2 ;;
        --gotchas) gotchas="$2"; shift 2 ;;
        --resources) resources="$2"; shift 2 ;;
        --time) time_invested="$2"; shift 2 ;;
        --domain) domain="$2"; shift 2 ;;
        --tags) tags="$2"; shift 2 ;;
        *) shift ;;
    esac
done

# Check for environment variables
title="${title:-$SPIKE_TITLE}"
topic="${topic:-$SPIKE_TOPIC}"
question="${question:-$SPIKE_QUESTION}"
findings="${findings:-$SPIKE_FINDINGS}"
gotchas="${gotchas:-$SPIKE_GOTCHAS}"
resources="${resources:-$SPIKE_RESOURCES}"
time_invested="${time_invested:-$SPIKE_TIME}"
domain="${domain:-$SPIKE_DOMAIN}"
tags="${tags:-$SPIKE_TAGS}"

# Non-interactive mode: if we have required fields, skip prompts
if [ -n "$title" ] && [ -n "$topic" ] && [ -n "$question" ] && [ -n "$findings" ]; then
    log "INFO" "Running in non-interactive mode"
    gotchas="${gotchas:-}"
    resources="${resources:-}"
    time_invested="${time_invested:-}"
    domain="${domain:-general}"
    tags="${tags:-}"
    echo "=== Record Spike Report (non-interactive) ==="
elif [ ! -t 0 ]; then
    # Not a terminal and no args provided - show usage and exit gracefully
    log "INFO" "No terminal attached and no arguments provided - showing usage"
    echo "Usage (non-interactive):"
    echo "  $0 --title \"Title\" --topic \"What was investigated\" --question \"Question answered\" --findings \"What was learned\""
    echo "  Optional: --gotchas \"Pitfalls\" --resources \"URLs\" --time 30 --domain \"domain\" --tags \"tag1,tag2\""
    echo ""
    echo "Or set environment variables:"
    echo "  SPIKE_TITLE=\"title\" SPIKE_TOPIC=\"topic\" SPIKE_QUESTION=\"question\" SPIKE_FINDINGS=\"findings\" $0"
    exit 0
else
    # Interactive mode (terminal attached)
    log "INFO" "Running in interactive mode"
    echo "=== Record Spike Report ==="
    echo "Capture research/investigation knowledge for future sessions"
    echo ""

    read -p "Title (short description): " title
    if [ -z "$title" ]; then
        log "ERROR" "Title cannot be empty"
        exit 1
    fi

    read -p "Topic (what was being investigated): " topic
    if [ -z "$topic" ]; then
        log "ERROR" "Topic cannot be empty"
        exit 1
    fi

    read -p "Question (what question was being answered): " question
    if [ -z "$question" ]; then
        log "ERROR" "Question cannot be empty"
        exit 1
    fi

    echo "Findings (what was learned, press Ctrl+D when done):"
    findings=$(cat)
    if [ -z "$findings" ]; then
        log "ERROR" "Findings cannot be empty"
        exit 1
    fi

    echo ""
    echo "Gotchas (pitfalls, edge cases, surprises - press Ctrl+D when done, or enter empty):"
    gotchas=$(cat) || gotchas=""

    echo ""
    read -p "Resources (URLs, files, docs consulted - comma separated): " resources

    read -p "Time Invested (minutes, optional): " time_invested

    read -p "Domain (optional, default: general): " domain
    if [ -z "$domain" ]; then
        domain="general"
    fi

    read -p "Tags (comma-separated, optional): " tags
fi

# Validate time_invested is a number if provided
if [ -n "$time_invested" ]; then
    if ! [[ "$time_invested" =~ ^[0-9]+$ ]]; then
        log "ERROR" "Time invested must be a number"
        echo "ERROR: Time invested must be a number" >&2
        exit 1
    fi
else
    time_invested="NULL"
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
if [ ${#topic} -gt $MAX_TOPIC_LENGTH ]; then
    log "ERROR" "Topic exceeds maximum length"
    echo "ERROR: Topic too long (max $MAX_TOPIC_LENGTH characters)" >&2
    exit 1
fi
if [ ${#question} -gt $MAX_QUESTION_LENGTH ]; then
    log "ERROR" "Question exceeds maximum length"
    echo "ERROR: Question too long (max $MAX_QUESTION_LENGTH characters)" >&2
    exit 1
fi
if [ ${#findings} -gt $MAX_FINDINGS_LENGTH ]; then
    log "ERROR" "Findings exceeds maximum length"
    echo "ERROR: Findings too long (max $MAX_FINDINGS_LENGTH characters)" >&2
    exit 1
fi
if [ ${#gotchas} -gt $MAX_GOTCHAS_LENGTH ]; then
    log "ERROR" "Gotchas exceeds maximum length"
    echo "ERROR: Gotchas too long (max $MAX_GOTCHAS_LENGTH characters)" >&2
    exit 1
fi
if [ ${#resources} -gt $MAX_RESOURCES_LENGTH ]; then
    log "ERROR" "Resources exceeds maximum length"
    echo "ERROR: Resources too long (max $MAX_RESOURCES_LENGTH characters)" >&2
    exit 1
fi
if [ ${#tags} -gt $MAX_TAGS_LENGTH ]; then
    log "ERROR" "Tags exceeds maximum length"
    echo "ERROR: Tags too long (max $MAX_TAGS_LENGTH characters)" >&2
    exit 1
fi

# Sanitize inputs (strip ANSI, control chars)
title=$(sanitize_input "$title")
topic=$(sanitize_input "$topic")
question=$(sanitize_input "$question")
findings=$(sanitize_input "$findings")
gotchas=$(sanitize_input "$gotchas")
resources=$(sanitize_input "$resources")
tags=$(sanitize_input "$tags")

log "INFO" "Recording spike report: $title (domain: $domain)"

# Escape single quotes for SQL
escape_sql() {
    echo "${1//\'/\'\'}"
}

title_escaped=$(escape_sql "$title")
topic_escaped=$(escape_sql "$topic")
question_escaped=$(escape_sql "$question")
findings_escaped=$(escape_sql "$findings")
gotchas_escaped=$(escape_sql "$gotchas")
resources_escaped=$(escape_sql "$resources")
domain_escaped=$(escape_sql "$domain")
tags_escaped=$(escape_sql "$tags")

# Build time_invested SQL value
if [ "$time_invested" = "NULL" ]; then
    time_sql="NULL"
else
    time_sql="$time_invested"
fi

# Insert into database with retry logic for concurrent access
if ! spike_id=$(sqlite_with_retry "$DB_PATH" <<SQL
INSERT INTO spike_reports (title, topic, question, findings, gotchas, resources, time_invested_minutes, domain, tags)
VALUES (
    '$title_escaped',
    '$topic_escaped',
    '$question_escaped',
    '$findings_escaped',
    '$gotchas_escaped',
    '$resources_escaped',
    $time_sql,
    '$domain_escaped',
    '$tags_escaped'
);
SELECT last_insert_rowid();
SQL
); then
    log "ERROR" "Failed to insert into database"
    exit 1
fi

echo "Database record created (ID: $spike_id)"
log "INFO" "Database record created (ID: $spike_id)"

# Create markdown file for the spike report
current_date=$(date +%Y-%m-%d)
title_slug=$(echo "$title" | tr '[:upper:]' '[:lower:]' | tr ' ' '-' | tr -cd '[:alnum:]-' | cut -c1-50)
spike_file="$SPIKES_DIR/${current_date}-${title_slug}.md"

# Security checks before file write
if ! check_symlink_safe "$spike_file"; then
    exit 6
fi

# Create the spike report markdown file
{
    echo "# Spike Report: ${title}"
    echo ""
    echo "**ID**: SPIKE-${spike_id}"
    echo "**Date**: ${current_date}"
    echo "**Domain**: ${domain}"
    if [ -n "$tags" ]; then
        echo "**Tags**: ${tags}"
    fi
    if [ "$time_invested" != "NULL" ]; then
        echo "**Time Invested**: ${time_invested} minutes"
    fi
    echo ""
    echo "---"
    echo ""
    echo "## Topic"
    echo ""
    echo "${topic}"
    echo ""
    echo "## Question"
    echo ""
    echo "${question}"
    echo ""
    echo "## Findings"
    echo ""
    echo "${findings}"
    echo ""

    if [ -n "$gotchas" ]; then
        echo "## Gotchas / Pitfalls"
        echo ""
        echo "${gotchas}"
        echo ""
    fi

    if [ -n "$resources" ]; then
        echo "## Resources Consulted"
        echo ""
        IFS=',' read -ra RES_ARRAY <<< "$resources"
        for res in "${RES_ARRAY[@]}"; do
            res_trimmed=$(echo "$res" | xargs)
            echo "- $res_trimmed"
        done
        echo ""
    fi

    echo "---"
    echo ""
    echo "*This spike report captures research knowledge for future sessions.*"
} > "$spike_file"

echo "Created spike file: $spike_file"
log "INFO" "Created spike file: $spike_file"

log "INFO" "Spike report recorded successfully: $title"
echo ""
echo "Spike report recorded successfully!"
echo "SPIKE-${spike_id}: ${title}"
echo "File: $spike_file"
if [ "$time_invested" != "NULL" ]; then
    echo "Time invested: ${time_invested} minutes (this knowledge is now preserved!)"
fi
