#!/bin/bash
# Record an Assumption in the Emergent Learning Framework
#
# Usage (interactive): ./record-assumption.sh
# Usage (non-interactive):
#   ASSUMPTION="..." ASSUMPTION_CONTEXT="..." ./record-assumption.sh
#   Or: ./record-assumption.sh --assumption "..." --context "..." --source "..." --confidence 0.8 --domain "..."
#
# Source types: file, api, user, inference, documentation, observation

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$(dirname "$SCRIPT_DIR")"
MEMORY_DIR="$BASE_DIR/memory"
DB_PATH="$MEMORY_DIR/index.db"
LOGS_DIR="$BASE_DIR/logs"

# Setup logging
LOG_FILE="$LOGS_DIR/$(date +%Y%m%d).log"
mkdir -p "$LOGS_DIR"

log() {
    local level="$1"
    shift
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [$level] [record-assumption] $*" >> "$LOG_FILE"
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

# Input length limits
MAX_ASSUMPTION_LENGTH=2000
MAX_CONTEXT_LENGTH=5000
MAX_SOURCE_LENGTH=200
MAX_DOMAIN_LENGTH=100

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

log "INFO" "Script started"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --assumption) assumption="$2"; shift 2 ;;
        --context) context="$2"; shift 2 ;;
        --source) source="$2"; shift 2 ;;
        --confidence) confidence="$2"; shift 2 ;;
        --domain) domain="$2"; shift 2 ;;
        --help)
            echo "Usage: ./record-assumption.sh [OPTIONS]"
            echo ""
            echo "Record an assumption in the Emergent Learning Framework."
            echo ""
            echo "Options:"
            echo "  --assumption TEXT    The assumption being made (required)"
            echo "  --context TEXT       What task/situation led to this assumption (required)"
            echo "  --source TEXT        Where this came from: file, api, user, inference, documentation, observation"
            echo "  --confidence FLOAT   Confidence level 0.0-1.0 (default: 0.5)"
            echo "  --domain TEXT        Domain tag for filtering (optional)"
            echo "  --help               Show this help message"
            echo ""
            echo "Environment variables:"
            echo "  ASSUMPTION           Same as --assumption"
            echo "  ASSUMPTION_CONTEXT   Same as --context"
            echo "  ASSUMPTION_SOURCE    Same as --source"
            echo "  ASSUMPTION_CONFIDENCE Same as --confidence"
            echo "  ASSUMPTION_DOMAIN    Same as --domain"
            echo ""
            echo "Examples:"
            echo "  ./record-assumption.sh --assumption 'API returns JSON' --context 'Building REST client' --source api"
            echo "  ./record-assumption.sh --assumption 'File exists at /etc/config' --context 'Configuration loading' --confidence 0.9"
            exit 0
            ;;
        *) shift ;;
    esac
done

# Check for environment variables
assumption="${assumption:-$ASSUMPTION}"
context="${context:-$ASSUMPTION_CONTEXT}"
source="${source:-$ASSUMPTION_SOURCE}"
confidence="${confidence:-$ASSUMPTION_CONFIDENCE}"
domain="${domain:-$ASSUMPTION_DOMAIN}"

# Non-interactive mode: if we have required fields, skip prompts
if [ -n "$assumption" ] && [ -n "$context" ]; then
    log "INFO" "Running in non-interactive mode"
    source="${source:-inference}"
    confidence="${confidence:-0.5}"
    domain="${domain:-}"
    echo "=== Record Assumption (non-interactive) ==="
elif [ ! -t 0 ]; then
    # Not a terminal and no args provided - show usage and exit gracefully
    log "INFO" "No terminal attached and no arguments provided - showing usage"
    echo "Usage (non-interactive):"
    echo "  $0 --assumption \"The assumption\" --context \"Why it was made\""
    echo "  Optional: --source \"file|api|user|inference\" --confidence 0.8 --domain \"domain\""
    echo ""
    echo "Or set environment variables:"
    echo "  ASSUMPTION=\"...\" ASSUMPTION_CONTEXT=\"...\" $0"
    exit 0
else
    # Interactive mode (terminal attached)
    log "INFO" "Running in interactive mode"
    echo "=== Record Assumption ==="
    echo ""

    read -p "Assumption (what are you assuming?): " assumption
    if [ -z "$assumption" ]; then
        log "ERROR" "Assumption cannot be empty"
        exit 1
    fi

    read -p "Context (what led to this assumption?): " context
    if [ -z "$context" ]; then
        log "ERROR" "Context cannot be empty"
        exit 1
    fi

    read -p "Source (file/api/user/inference/documentation/observation, default: inference): " source
    if [ -z "$source" ]; then
        source="inference"
    fi

    read -p "Confidence (0.0-1.0, default: 0.5): " confidence
    if [ -z "$confidence" ]; then
        confidence="0.5"
    fi

    read -p "Domain (optional): " domain
fi

# Validate confidence is a number between 0 and 1
if ! echo "$confidence" | grep -qE '^[0-9]*\.?[0-9]+$'; then
    log "ERROR" "Confidence must be a non-negative number between 0.0 and 1.0"
    echo "ERROR: Confidence must be a non-negative number between 0.0 and 1.0" >&2
    exit 1
fi

# Clamp confidence to valid range using awk
confidence=$(echo "$confidence" | awk '{if ($1 < 0) print 0; else if ($1 > 1) print 1; else print $1}')

# Sanitize domain to prevent path traversal
if [ -n "$domain" ]; then
    domain_safe=$(echo "$domain" | tr '[:upper:]' '[:lower:]' | tr ' ' '-' | tr -cd '[:alnum:]-')
    domain_safe="${domain_safe#-}"
    domain_safe="${domain_safe%-}"
    domain_safe="${domain_safe:0:100}"
    domain="$domain_safe"
fi

# Input length validation
if [ ${#assumption} -gt $MAX_ASSUMPTION_LENGTH ]; then
    log "ERROR" "Assumption exceeds maximum length ($MAX_ASSUMPTION_LENGTH chars)"
    echo "ERROR: Assumption too long (max $MAX_ASSUMPTION_LENGTH characters)" >&2
    exit 1
fi
if [ ${#context} -gt $MAX_CONTEXT_LENGTH ]; then
    log "ERROR" "Context exceeds maximum length"
    echo "ERROR: Context too long (max $MAX_CONTEXT_LENGTH characters)" >&2
    exit 1
fi
if [ ${#source} -gt $MAX_SOURCE_LENGTH ]; then
    log "ERROR" "Source exceeds maximum length"
    echo "ERROR: Source too long (max $MAX_SOURCE_LENGTH characters)" >&2
    exit 1
fi

# Sanitize inputs (strip ANSI, control chars)
assumption=$(sanitize_input "$assumption")
context=$(sanitize_input "$context")
source=$(sanitize_input "$source")
domain=$(sanitize_input "$domain")

log "INFO" "Recording assumption: ${assumption:0:50}... (confidence: $confidence)"

# Escape single quotes for SQL
escape_sql() {
    echo "${1//\'/\'\'}"
}

assumption_escaped=$(escape_sql "$assumption")
context_escaped=$(escape_sql "$context")
source_escaped=$(escape_sql "$source")
domain_escaped=$(escape_sql "$domain")

# Build SQL query
domain_sql="NULL"
if [ -n "$domain" ]; then
    domain_sql="'$domain_escaped'"
fi

sql_query="INSERT INTO assumptions (assumption, context, source, confidence, domain, status) VALUES ('$assumption_escaped', '$context_escaped', '$source_escaped', $confidence, $domain_sql, 'active'); SELECT last_insert_rowid();"

# Insert into database with retry logic for concurrent access
if ! assumption_id=$(sqlite_with_retry "$DB_PATH" "$sql_query"); then
    log "ERROR" "Failed to insert into database"
    exit 1
fi

echo ""
echo "Assumption recorded successfully!"
echo "ID: $assumption_id"
echo "Assumption: ${assumption:0:80}$([ ${#assumption} -gt 80 ] && echo '...')"
echo "Confidence: $confidence"
echo "Status: active"
[ -n "$domain" ] && echo "Domain: $domain"
echo ""
echo "Use the dashboard or API to verify/challenge this assumption:"
echo "  POST /api/assumptions/$assumption_id/verify   - Mark as verified"
echo "  POST /api/assumptions/$assumption_id/challenge - Mark as challenged"

log "INFO" "Assumption recorded successfully (ID: $assumption_id)"
