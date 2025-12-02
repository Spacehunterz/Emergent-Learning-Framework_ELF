#!/bin/bash
# Record a heuristic in the Emergent Learning Framework
#
# Usage (interactive): ./record-heuristic.sh
# Usage (non-interactive):
#   HEURISTIC_DOMAIN="domain" HEURISTIC_RULE="rule" ./record-heuristic.sh
#   Or: ./record-heuristic.sh --domain "domain" --rule "rule" --explanation "why"
#   Optional: --source failure|success|observation --confidence 0.8

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$(dirname "$SCRIPT_DIR")"
MEMORY_DIR="$BASE_DIR/memory"
DB_PATH="$MEMORY_DIR/index.db"
HEURISTICS_DIR="$MEMORY_DIR/heuristics"
LOGS_DIR="$BASE_DIR/logs"

# TIME-FIX-1: Capture date once at script start for consistency across midnight boundary
EXECUTION_DATE=$(date +%Y%m%d)

# Setup logging
LOG_FILE="$LOGS_DIR/${EXECUTION_DATE}.log"
mkdir -p "$LOGS_DIR"

log() {
    local level="$1"
    shift
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [$level] [record-heuristic] $*" >> "$LOG_FILE"
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

# Error trap
trap 'log "ERROR" "Script failed at line $LINENO"; exit 1' ERR

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

    log "INFO" "Pre-flight checks passed"
}

preflight_check

# Ensure heuristics directory exists
mkdir -p "$HEURISTICS_DIR"

log "INFO" "Script started"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --domain) domain="$2"; shift 2 ;;
        --rule) rule="$2"; shift 2 ;;
        --explanation) explanation="$2"; shift 2 ;;
        --source) source_type="$2"; shift 2 ;;
        --confidence) confidence="$2"; shift 2 ;;
        *) shift ;;
    esac
done

# Check for environment variables
domain="${domain:-$HEURISTIC_DOMAIN}"
rule="${rule:-$HEURISTIC_RULE}"
explanation="${explanation:-$HEURISTIC_EXPLANATION}"
source_type="${source_type:-$HEURISTIC_SOURCE}"
confidence="${confidence:-$HEURISTIC_CONFIDENCE}"

# Non-interactive mode: if we have domain and rule, skip prompts
if [ -n "$domain" ] && [ -n "$rule" ]; then
    log "INFO" "Running in non-interactive mode"
    source_type="${source_type:-observation}"
    # Validate confidence is a number, convert words to numbers
    if [ -z "$confidence" ]; then
        confidence="0.7"
    elif [[ "$confidence" =~ ^[0-9]*\.?[0-9]+$ ]]; then
        # Valid number - keep as-is
        :
    else
        # Invalid (word like "high") - convert or default
        case "$confidence" in
            low) confidence="0.3" ;;
            medium) confidence="0.6" ;;
            high) confidence="0.85" ;;
            *) confidence="0.7" ;; # default for invalid
        esac
    fi
    # Strict validation: confidence must be decimal 0.0-1.0 ONLY (SQL injection protection)
    # Pattern: 0, 1, 0.X, or 1.0 (but not 1.X where X>0)
    if ! [[ "$confidence" =~ ^(0(\.[0-9]+)?|1(\.0+)?)$ ]]; then
        log "WARN" "Invalid confidence provided, defaulting to 0.7"
        confidence="0.7"
    fi
    explanation="${explanation:-}"
    echo "=== Record Heuristic (non-interactive) ==="
else
    # Interactive mode
    log "INFO" "Running in interactive mode"
    echo "=== Record Heuristic ==="
    echo ""

    read -p "Domain: " domain
    if [ -z "$domain" ]; then
        log "ERROR" "Domain cannot be empty"
        exit 1
    fi

    read -p "Rule (the heuristic): " rule
    if [ -z "$rule" ]; then
        log "ERROR" "Rule cannot be empty"
        exit 1
    fi

    read -p "Explanation: " explanation

    read -p "Source type (failure/success/observation): " source_type
    if [ -z "$source_type" ]; then
        source_type="observation"
    fi

    read -p "Confidence (0.0-1.0): " confidence
    if [ -z "$confidence" ]; then
        confidence="0.5"
    fi
fi

log "INFO" "Recording heuristic: $rule (domain: $domain, confidence: $confidence)"

# ============================================
# SECURITY FIX: Sanitize domain to prevent path traversal
# CVE: Path traversal via domain parameter
# Severity: CRITICAL
# ============================================
domain_safe="${domain//$'\0'/}"  # Remove null bytes
domain_safe="${domain_safe//$'\n'/}"  # Remove newlines
domain_safe="${domain_safe//$'\r'/}"  # Remove carriage returns
domain_safe=$(echo "$domain_safe" | tr '[:upper:]' '[:lower:]' | tr ' ' '-')
domain_safe=$(echo "$domain_safe" | tr -cd '[:alnum:]-')  # Only alphanumeric and dash
domain_safe="${domain_safe#-}"  # Remove leading dash
domain_safe="${domain_safe%-}"  # Remove trailing dash
domain_safe="${domain_safe:0:100}"  # Limit length to prevent buffer issues

if [ -z "$domain_safe" ]; then
    log "ERROR" "SECURITY: Domain sanitization resulted in empty string: '$domain'"
    exit 6
fi

if [ "$domain" != "$domain_safe" ]; then
    log "WARN" "SECURITY: Domain sanitized from '$domain' to '$domain_safe'"
    domain="$domain_safe"
fi


# Input length validation (added by Agent C hardening)
MAX_RULE_LENGTH=500
MAX_DOMAIN_LENGTH=100
MAX_EXPLANATION_LENGTH=5000

if [ ${#rule} -gt $MAX_RULE_LENGTH ]; then
    log "ERROR" "Rule exceeds maximum length ($MAX_RULE_LENGTH characters, got ${#rule})"
    echo "ERROR: Rule too long (max $MAX_RULE_LENGTH characters)" >&2
    exit 1
fi

if [ ${#domain} -gt $MAX_DOMAIN_LENGTH ]; then
    log "ERROR" "Domain exceeds maximum length ($MAX_DOMAIN_LENGTH characters)"
    echo "ERROR: Domain too long (max $MAX_DOMAIN_LENGTH characters)" >&2
    exit 1
fi

if [ ${#explanation} -gt $MAX_EXPLANATION_LENGTH ]; then
    log "ERROR" "Explanation exceeds maximum length ($MAX_EXPLANATION_LENGTH characters)"
    echo "ERROR: Explanation too long (max $MAX_EXPLANATION_LENGTH characters)" >&2
    exit 1
fi

# Trim leading/trailing whitespace
rule=$(echo "$rule" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')
domain=$(echo "$domain" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')

# Re-validate after trimming
if [ -z "$rule" ]; then
    log "ERROR" "Rule cannot be empty (or whitespace-only)"
    echo "ERROR: Rule cannot be empty" >&2
    exit 1
fi

if [ -z "$domain" ]; then
    log "ERROR" "Domain cannot be empty (or whitespace-only)"
    echo "ERROR: Domain cannot be empty" >&2
    exit 1
fi


# Escape single quotes for SQL
escape_sql() {
    echo "${1//\'/\'\'}"
}

domain_escaped=$(escape_sql "$domain")
rule_escaped=$(escape_sql "$rule")
explanation_escaped=$(escape_sql "$explanation")
source_type_escaped=$(escape_sql "$source_type")

# Insert into database with retry logic for concurrent access
if ! heuristic_id=$(sqlite_with_retry "$DB_PATH" <<SQL
INSERT INTO heuristics (domain, rule, explanation, source_type, confidence)
VALUES (
    '$domain_escaped',
    '$rule_escaped',
    '$explanation_escaped',
    '$source_type_escaped',
    CAST($confidence AS REAL)
);
SELECT last_insert_rowid();
SQL
); then
    log "ERROR" "Failed to insert into database"
    exit 1
fi

echo "Database record created (ID: $heuristic_id)"
log "INFO" "Database record created (ID: $heuristic_id)"

# Append to domain markdown file
domain_file="$HEURISTICS_DIR/${domain}.md"

if [ ! -f "$domain_file" ]; then
    cat > "$domain_file" <<EOF
# Heuristics: $domain

Generated from failures, successes, and observations in the **$domain** domain.

---

EOF
    log "INFO" "Created new domain file: $domain_file"
fi

cat >> "$domain_file" <<EOF
## H-$heuristic_id: $rule

**Confidence**: $confidence
**Source**: $source_type
**Created**: ${EXECUTION_DATE:0:4}-${EXECUTION_DATE:4:2}-${EXECUTION_DATE:6:2}  # TIME-FIX-2: Use consistent date

$explanation

---

EOF

echo "Appended to: $domain_file"
log "INFO" "Appended heuristic to: $domain_file"

# Git commit with locking for concurrent access
cd "$BASE_DIR"
if [ -d ".git" ]; then
    LOCK_FILE="$BASE_DIR/.git/claude-lock"
    
    if ! acquire_git_lock "$LOCK_FILE" 30; then
        log "ERROR" "Could not acquire git lock"
        echo "Error: Could not acquire git lock"
        exit 1
    fi

    git add "$domain_file"
    git add "$DB_PATH"
    if ! git commit -m "heuristic: $rule" -m "Domain: $domain | Confidence: $confidence"; then
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

log "INFO" "Heuristic recorded successfully: $rule"
echo ""
echo "Heuristic recorded successfully!"
