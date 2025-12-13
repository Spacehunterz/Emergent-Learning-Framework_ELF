#!/bin/bash
# Record an Invariant in the Emergent Learning Framework
#
# Invariants are statements about what must ALWAYS be true, different from Golden Rules
# which say "don't do X". Invariants can be validated automatically.
#
# Usage (interactive): ./record-invariant.sh
# Usage (non-interactive):
#   INVARIANT_STATEMENT="statement" INVARIANT_RATIONALE="rationale" ./record-invariant.sh
#   Or: ./record-invariant.sh --statement "..." --rationale "..."
#   Optional: --domain "..." --scope "codebase" --severity "error" --validation-type "manual" --validation-code "..."

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
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [$level] [record-invariant] $*" >> "$LOG_FILE"
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
MAX_STATEMENT_LENGTH=1000
MAX_RATIONALE_LENGTH=5000
MAX_DOMAIN_LENGTH=100
MAX_SCOPE_LENGTH=50
MAX_SEVERITY_LENGTH=20
MAX_VALIDATION_TYPE_LENGTH=50
MAX_VALIDATION_CODE_LENGTH=10000

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

    log "INFO" "Pre-flight checks passed"
}

preflight_check

log "INFO" "Script started"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --statement) statement="$2"; shift 2 ;;
        --rationale) rationale="$2"; shift 2 ;;
        --domain) domain="$2"; shift 2 ;;
        --scope) scope="$2"; shift 2 ;;
        --severity) severity="$2"; shift 2 ;;
        --validation-type) validation_type="$2"; shift 2 ;;
        --validation-code) validation_code="$2"; shift 2 ;;
        *) shift ;;
    esac
done

# Check for environment variables
statement="${statement:-$INVARIANT_STATEMENT}"
rationale="${rationale:-$INVARIANT_RATIONALE}"
domain="${domain:-$INVARIANT_DOMAIN}"
scope="${scope:-$INVARIANT_SCOPE}"
severity="${severity:-$INVARIANT_SEVERITY}"
validation_type="${validation_type:-$INVARIANT_VALIDATION_TYPE}"
validation_code="${validation_code:-$INVARIANT_VALIDATION_CODE}"

# Non-interactive mode: if we have required fields, skip prompts
if [ -n "$statement" ] && [ -n "$rationale" ]; then
    log "INFO" "Running in non-interactive mode"
    domain="${domain:-}"
    scope="${scope:-codebase}"
    severity="${severity:-error}"
    validation_type="${validation_type:-manual}"
    validation_code="${validation_code:-}"
    echo "=== Record Invariant (non-interactive) ==="
elif [ ! -t 0 ]; then
    # Not a terminal and no args provided - show usage and exit gracefully
    log "INFO" "No terminal attached and no arguments provided - showing usage"
    echo "Usage (non-interactive):"
    echo "  $0 --statement \"What must always be true\" --rationale \"Why this must be true\""
    echo "  Optional: --domain \"domain\" --scope \"codebase|module|function|runtime\" --severity \"error|warning|info\""
    echo "            --validation-type \"manual|automated|test\" --validation-code \"code to validate\""
    echo ""
    echo "Or set environment variables:"
    echo "  INVARIANT_STATEMENT=\"...\" INVARIANT_RATIONALE=\"...\" $0"
    exit 0
else
    # Interactive mode (terminal attached)
    log "INFO" "Running in interactive mode"
    echo "=== Record Invariant ==="
    echo ""
    echo "Invariants are statements about what must ALWAYS be true."
    echo "Example: 'All API responses include request_id'"
    echo ""

    read -p "Statement (what must always be true): " statement
    if [ -z "$statement" ]; then
        log "ERROR" "Statement cannot be empty"
        exit 1
    fi

    read -p "Rationale (why this must be true): " rationale
    if [ -z "$rationale" ]; then
        log "ERROR" "Rationale cannot be empty"
        exit 1
    fi

    read -p "Domain (optional): " domain

    read -p "Scope (codebase/module/function/runtime, default: codebase): " scope
    if [ -z "$scope" ]; then
        scope="codebase"
    fi

    read -p "Severity (error/warning/info, default: error): " severity
    if [ -z "$severity" ]; then
        severity="error"
    fi

    read -p "Validation type (manual/automated/test, default: manual): " validation_type
    if [ -z "$validation_type" ]; then
        validation_type="manual"
    fi

    read -p "Validation code (optional, code/command to validate): " validation_code
fi

# Validate scope
case "$scope" in
    codebase|module|function|runtime) ;;
    *)
        log "ERROR" "Invalid scope: $scope (must be codebase, module, function, or runtime)"
        echo "ERROR: Invalid scope. Must be one of: codebase, module, function, runtime" >&2
        exit 1
        ;;
esac

# Validate severity
case "$severity" in
    error|warning|info) ;;
    *)
        log "ERROR" "Invalid severity: $severity (must be error, warning, or info)"
        echo "ERROR: Invalid severity. Must be one of: error, warning, info" >&2
        exit 1
        ;;
esac

# Validate validation_type if provided
if [ -n "$validation_type" ]; then
    case "$validation_type" in
        manual|automated|test) ;;
        *)
            log "ERROR" "Invalid validation_type: $validation_type"
            echo "ERROR: Invalid validation type. Must be one of: manual, automated, test" >&2
            exit 1
            ;;
    esac
fi

# Sanitize domain to prevent path traversal
if [ -n "$domain" ]; then
    domain_safe=$(echo "$domain" | tr '[:upper:]' '[:lower:]' | tr ' ' '-' | tr -cd '[:alnum:]-')
    domain_safe="${domain_safe#-}"
    domain_safe="${domain_safe%-}"
    domain_safe="${domain_safe:0:100}"
    domain="$domain_safe"
fi

# Input length validation
if [ ${#statement} -gt $MAX_STATEMENT_LENGTH ]; then
    log "ERROR" "Statement exceeds maximum length ($MAX_STATEMENT_LENGTH chars)"
    echo "ERROR: Statement too long (max $MAX_STATEMENT_LENGTH characters)" >&2
    exit 1
fi
if [ ${#rationale} -gt $MAX_RATIONALE_LENGTH ]; then
    log "ERROR" "Rationale exceeds maximum length"
    echo "ERROR: Rationale too long (max $MAX_RATIONALE_LENGTH characters)" >&2
    exit 1
fi
if [ ${#validation_code} -gt $MAX_VALIDATION_CODE_LENGTH ]; then
    log "ERROR" "Validation code exceeds maximum length"
    echo "ERROR: Validation code too long (max $MAX_VALIDATION_CODE_LENGTH characters)" >&2
    exit 1
fi

# Sanitize inputs (strip ANSI, control chars)
statement=$(sanitize_input "$statement")
rationale=$(sanitize_input "$rationale")
validation_code=$(sanitize_input "$validation_code")

log "INFO" "Recording invariant: $statement (domain: $domain, scope: $scope, severity: $severity)"

# Escape single quotes for SQL
escape_sql() {
    echo "${1//\'/\'\'}"
}

statement_escaped=$(escape_sql "$statement")
rationale_escaped=$(escape_sql "$rationale")
domain_escaped=$(escape_sql "$domain")
scope_escaped=$(escape_sql "$scope")
severity_escaped=$(escape_sql "$severity")
validation_type_escaped=$(escape_sql "$validation_type")
validation_code_escaped=$(escape_sql "$validation_code")

# Insert into database with retry logic for concurrent access
if ! invariant_id=$(sqlite_with_retry "$DB_PATH" <<SQL
INSERT INTO invariants (statement, rationale, domain, scope, validation_type, validation_code, severity, status)
VALUES (
    '$statement_escaped',
    '$rationale_escaped',
    $([ -n "$domain" ] && echo "'$domain_escaped'" || echo "NULL"),
    '$scope_escaped',
    $([ -n "$validation_type" ] && echo "'$validation_type_escaped'" || echo "NULL"),
    $([ -n "$validation_code" ] && echo "'$validation_code_escaped'" || echo "NULL"),
    '$severity_escaped',
    'active'
);
SELECT last_insert_rowid();
SQL
); then
    log "ERROR" "Failed to insert into database"
    exit 1
fi

echo "Database record created (ID: $invariant_id)"
log "INFO" "Database record created (ID: $invariant_id)"

log "INFO" "Invariant recorded successfully: $statement"
echo ""
echo "Invariant recorded successfully!"
echo "ID: $invariant_id"
echo "Statement: $statement"
echo "Scope: $scope"
echo "Severity: $severity"
if [ -n "$domain" ]; then
    echo "Domain: $domain"
fi
if [ -n "$validation_type" ]; then
    echo "Validation: $validation_type"
fi
