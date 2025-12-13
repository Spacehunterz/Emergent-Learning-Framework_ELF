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

# Setup logging
LOG_FILE="$LOGS_DIR/$(date +%Y%m%d).log"
mkdir -p "$LOGS_DIR"

log() {
    local level="$1"
    shift
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [$level] [record-heuristic] $*" >> "$LOG_FILE"
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
MAX_RULE_LENGTH=500
MAX_DOMAIN_LENGTH=100
MAX_EXPLANATION_LENGTH=5000

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
elif [ ! -t 0 ]; then
    # Not a terminal and no args provided - show usage and exit gracefully
    log "INFO" "No terminal attached and no arguments provided - showing usage"
    echo "Usage (non-interactive):"
    echo "  $0 --domain \"domain\" --rule \"the heuristic rule\""
    echo "  Optional: --explanation \"why\" --source failure|success|observation --confidence 0.8"
    echo ""
    echo "Or set environment variables:"
    echo "  HEURISTIC_DOMAIN=\"domain\" HEURISTIC_RULE=\"rule\" $0"
    exit 0
else
    # Interactive mode (terminal attached)
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
if [ ${#rule} -gt $MAX_RULE_LENGTH ]; then
    log "ERROR" "Rule exceeds maximum length ($MAX_RULE_LENGTH chars)"
    echo "ERROR: Rule too long (max $MAX_RULE_LENGTH characters)" >&2
    exit 1
fi
if [ ${#explanation} -gt $MAX_EXPLANATION_LENGTH ]; then
    log "ERROR" "Explanation exceeds maximum length"
    echo "ERROR: Explanation too long (max $MAX_EXPLANATION_LENGTH characters)" >&2
    exit 1
fi

# Sanitize inputs (strip ANSI, control chars)
rule=$(sanitize_input "$rule")
explanation=$(sanitize_input "$explanation")

log "INFO" "Recording heuristic: $rule (domain: $domain, confidence: $confidence)"

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

# Security checks before file write
if ! check_symlink_safe "$domain_file"; then
    exit 6
fi
if ! check_hardlink_safe "$domain_file"; then
    exit 6
fi

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
**Created**: $(date +%Y-%m-%d)

$explanation

---

EOF

echo "Appended to: $domain_file"
log "INFO" "Appended heuristic to: $domain_file"

# NOTE: Auto-commit removed for safety (can grab unrelated staged files)
# User should commit manually if desired:
#   git add memory/heuristics/ memory/index.db && git commit -m "heuristic: <description>"

log "INFO" "Heuristic recorded successfully: $rule"
echo ""
echo "Heuristic recorded successfully!"
