#!/bin/bash
# Sync golden rules from markdown to database
#
# Usage: ./sync-golden-rules.sh [--dry-run]
#
# This script parses memory/golden-rules.md and syncs rules to the heuristics table
# with is_golden=1. It is idempotent - safe to run multiple times.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$(dirname "$SCRIPT_DIR")"
MEMORY_DIR="$BASE_DIR/memory"
DB_PATH="$MEMORY_DIR/index.db"
GOLDEN_RULES_FILE="$MEMORY_DIR/golden-rules.md"
LOGS_DIR="$BASE_DIR/logs"

# Setup logging
LOG_FILE="$LOGS_DIR/$(date +%Y%m%d).log"
mkdir -p "$LOGS_DIR"

log() {
    local level="$1"
    shift
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [$level] [sync-golden-rules] $*" >> "$LOG_FILE"
    if [ "$level" = "ERROR" ]; then
        echo "ERROR: $*" >&2
    elif [ "$level" = "INFO" ] && [ "$VERBOSE" = "true" ]; then
        echo "$*"
    fi
}

# Parse command line args
DRY_RUN=false
VERBOSE=false
while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --verbose|-v)
            VERBOSE=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Check prerequisites
if [ ! -f "$DB_PATH" ]; then
    log "ERROR" "Database not found at $DB_PATH"
    exit 1
fi

if [ ! -f "$GOLDEN_RULES_FILE" ]; then
    log "INFO" "No golden-rules.md found at $GOLDEN_RULES_FILE, nothing to sync"
    exit 0
fi

# SQLite retry function for handling concurrent access
sqlite_with_retry() {
    local max_attempts=5
    local attempt=1
    while [ $attempt -le $max_attempts ]; do
        if sqlite3 "$DB_PATH" "$@" 2>/dev/null; then
            return 0
        fi
        log "WARN" "SQLite busy, retry $attempt/$max_attempts..."
        sleep 0.$((RANDOM % 5 + 1))
        ((attempt++))
    done
    log "ERROR" "SQLite failed after $max_attempts attempts"
    return 1
}

# Escape string for SQLite
escape_sql() {
    printf '%s' "$1" | sed "s/'/''/g"
}

# Parse golden rules from markdown
# Format expected:
# ## N. Rule Title
# > Rule statement here
# **Why:** Explanation here
parse_golden_rules() {
    local in_rule=false
    local rule_num=""
    local rule_title=""
    local rule_statement=""
    local rule_explanation=""
    local rules_found=0

    while IFS= read -r line || [[ -n "$line" ]]; do
        # Match rule header: ## N. Title or ## N Title
        if [[ "$line" =~ ^##[[:space:]]+([0-9]+)\.?[[:space:]]+(.+)$ ]]; then
            # Save previous rule if exists
            if [ -n "$rule_statement" ]; then
                process_rule "$rule_num" "$rule_title" "$rule_statement" "$rule_explanation"
                ((rules_found++))
            fi

            # Start new rule
            rule_num="${BASH_REMATCH[1]}"
            rule_title="${BASH_REMATCH[2]}"
            rule_statement=""
            rule_explanation=""
            in_rule=true
            continue
        fi

        if [ "$in_rule" = true ]; then
            # Match rule statement (> quote)
            if [[ "$line" =~ ^\>[[:space:]]*(.+)$ ]]; then
                rule_statement="${BASH_REMATCH[1]}"
                continue
            fi

            # Match explanation (**Why:** text)
            if [[ "$line" =~ ^\*\*Why:\*\*[[:space:]]*(.+)$ ]]; then
                rule_explanation="${BASH_REMATCH[1]}"
                continue
            fi
        fi
    done < "$GOLDEN_RULES_FILE"

    # Process last rule
    if [ -n "$rule_statement" ]; then
        process_rule "$rule_num" "$rule_title" "$rule_statement" "$rule_explanation"
        ((rules_found++))
    fi

    echo "$rules_found"
}

# Process a single golden rule - insert or update in database
process_rule() {
    local num="$1"
    local title="$2"
    local statement="$3"
    local explanation="$4"

    local escaped_title=$(escape_sql "$title")
    local escaped_statement=$(escape_sql "$statement")
    local escaped_explanation=$(escape_sql "$explanation")

    log "INFO" "Processing rule #$num: $title"

    if [ "$DRY_RUN" = true ]; then
        echo "[DRY-RUN] Would sync rule #$num: $title"
        echo "  Statement: $statement"
        echo "  Explanation: ${explanation:0:100}..."
        return
    fi

    # Check if rule already exists (by title similarity)
    local existing_id
    existing_id=$(sqlite_with_retry "SELECT id FROM heuristics WHERE domain='golden' AND rule LIKE '%$escaped_title%' LIMIT 1;")

    if [ -n "$existing_id" ]; then
        # Update existing rule
        sqlite_with_retry "UPDATE heuristics SET
            rule='$escaped_statement',
            explanation='$escaped_explanation',
            is_golden=1,
            confidence=1.0,
            updated_at=CURRENT_TIMESTAMP
            WHERE id=$existing_id;"
        log "INFO" "Updated existing golden rule #$existing_id: $title"
    else
        # Insert new rule
        sqlite_with_retry "INSERT INTO heuristics (domain, rule, explanation, is_golden, confidence, source_type)
            VALUES ('golden', '$escaped_statement', '$escaped_explanation', 1, 1.0, 'markdown');"
        log "INFO" "Inserted new golden rule: $title"
    fi
}

# Main execution
main() {
    log "INFO" "Starting golden rules sync from $GOLDEN_RULES_FILE"

    if [ "$DRY_RUN" = true ]; then
        echo "=== DRY RUN MODE - No changes will be made ==="
    fi

    # Get count before
    local count_before
    count_before=$(sqlite_with_retry "SELECT COUNT(*) FROM heuristics WHERE is_golden=1;")
    log "INFO" "Golden rules in database before sync: $count_before"

    # Parse and sync rules
    local rules_processed
    rules_processed=$(parse_golden_rules)

    # Get count after
    local count_after
    count_after=$(sqlite_with_retry "SELECT COUNT(*) FROM heuristics WHERE is_golden=1;")

    log "INFO" "Sync complete. Rules processed: $rules_processed, Golden rules in database: $count_after"

    if [ "$DRY_RUN" = false ]; then
        echo "Golden rules synced: $count_before -> $count_after (processed $rules_processed rules from markdown)"
    fi
}

main "$@"
