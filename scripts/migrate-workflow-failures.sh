#!/bin/bash
# Migrate workflow_runs failures to learnings table
#
# Usage: ./migrate-workflow-failures.sh [--dry-run] [--all]
#
# Options:
#   --dry-run   Show what would be migrated without making changes
#   --all       Migrate all failures (default: only last 30 days)
#
# This script converts failed workflow_runs into learnings records,
# enabling failure analysis and heuristic extraction.

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
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [$level] [migrate-workflow-failures] $*" >> "$LOG_FILE"
    if [ "$level" = "ERROR" ]; then
        echo "ERROR: $*" >&2
    elif [ "$level" = "INFO" ]; then
        echo "$*"
    fi
}

# Parse command line args
DRY_RUN=false
MIGRATE_ALL=false
while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --all)
            MIGRATE_ALL=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--dry-run] [--all]"
            exit 1
            ;;
    esac
done

# Check prerequisites
if [ ! -f "$DB_PATH" ]; then
    log "ERROR" "Database not found at $DB_PATH"
    exit 1
fi

# SQLite retry function
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

# Main migration logic
main() {
    log "INFO" "Starting workflow failures migration"

    if [ "$DRY_RUN" = true ]; then
        echo "=== DRY RUN MODE - No changes will be made ==="
    fi

    # Build time filter
    local time_filter=""
    if [ "$MIGRATE_ALL" = false ]; then
        time_filter="AND wr.created_at > datetime('now', '-30 days')"
        log "INFO" "Migrating failures from last 30 days (use --all for all time)"
    else
        log "INFO" "Migrating ALL failures"
    fi

    # Count failures to migrate
    local query="SELECT COUNT(*) FROM workflow_runs wr
        WHERE wr.status IN ('failed', 'cancelled')
        $time_filter
        AND NOT EXISTS (
            SELECT 1 FROM learnings l
            WHERE l.filepath = 'workflow_runs/' || wr.id
            AND l.type = 'failure'
        );"

    local count_to_migrate
    count_to_migrate=$(sqlite_with_retry "$query")

    log "INFO" "Found $count_to_migrate failures to migrate"

    if [ "$count_to_migrate" -eq 0 ]; then
        echo "No new failures to migrate."
        return 0
    fi

    if [ "$DRY_RUN" = true ]; then
        echo "Would migrate $count_to_migrate failures."
        echo ""
        echo "Sample of failures to migrate:"
        sqlite_with_retry "SELECT wr.id, wr.workflow_name, substr(wr.error_message, 1, 80) as error_preview
            FROM workflow_runs wr
            WHERE wr.status IN ('failed', 'cancelled')
            $time_filter
            AND NOT EXISTS (
                SELECT 1 FROM learnings l
                WHERE l.filepath = 'workflow_runs/' || wr.id
            )
            LIMIT 5;"
        return 0
    fi

    # Perform migration
    local migrated=0
    local failed=0

    # Get failures to migrate
    local failures
    failures=$(sqlite_with_retry "SELECT wr.id, wr.workflow_name, wr.error_message, wr.created_at
        FROM workflow_runs wr
        WHERE wr.status IN ('failed', 'cancelled')
        $time_filter
        AND NOT EXISTS (
            SELECT 1 FROM learnings l
            WHERE l.filepath = 'workflow_runs/' || wr.id
        );")

    # Process each failure
    while IFS='|' read -r id workflow_name error_message created_at; do
        [ -z "$id" ] && continue

        local escaped_workflow=$(escape_sql "$workflow_name")
        local escaped_error=$(escape_sql "${error_message:-No error message}")
        local title="Workflow failed: $escaped_workflow [run:$id]"

        # Insert learning
        if sqlite_with_retry "INSERT INTO learnings (type, filepath, title, summary, domain, severity, created_at)
            VALUES ('failure', 'workflow_runs/$id', '$title', '$escaped_error', 'workflow', 3, '$created_at');"; then
            ((migrated++))
            log "INFO" "Migrated failure: run #$id ($workflow_name)"
        else
            ((failed++))
            log "ERROR" "Failed to migrate run #$id"
        fi
    done <<< "$failures"

    # Record migration metric
    if [ "$migrated" -gt 0 ]; then
        sqlite_with_retry "INSERT INTO metrics (metric_type, metric_name, metric_value, context)
            VALUES ('auto_failure_capture', 'workflow_migration', $migrated, 'batch migration via script');"
    fi

    # Summary
    log "INFO" "Migration complete: $migrated migrated, $failed failed"
    echo ""
    echo "Migration Summary:"
    echo "  Migrated: $migrated"
    echo "  Failed: $failed"

    # Show current counts
    local total_learnings
    total_learnings=$(sqlite_with_retry "SELECT COUNT(*) FROM learnings WHERE type='failure';")
    echo "  Total failure learnings: $total_learnings"
}

main "$@"
