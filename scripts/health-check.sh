#!/bin/bash
# Health check script for Emergent Learning Framework
#
# Exit codes:
#   0 - Healthy
#   1 - Degraded (warnings, but functional)
#   2 - Critical (service unavailable)
#
# Usage:
#   ./health-check.sh [--verbose] [--json]
#
# Checks:
#   - Database connectivity and integrity
#   - Disk space availability
#   - Git repository status
#   - Stale lock detection
#   - Recent errors in logs

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$(dirname "$SCRIPT_DIR")"
MEMORY_DIR="$BASE_DIR/memory"
DB_PATH="$MEMORY_DIR/index.db"
LOGS_DIR="$BASE_DIR/logs"

# Source logging library
source "$SCRIPT_DIR/lib/logging.sh"
log_init "health-check"

# Configuration
VERBOSE=false
JSON_OUTPUT=false
DISK_WARN_THRESHOLD_MB=1000
DISK_CRITICAL_THRESHOLD_MB=100
MAX_STALE_LOCK_AGE_MINUTES=30

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --verbose|-v)
            VERBOSE=true
            shift
            ;;
        --json)
            JSON_OUTPUT=true
            shift
            ;;
        *)
            shift
            ;;
    esac
done

# Health check results
declare -A HEALTH_RESULTS=(
    [status]="healthy"
    [db_connectivity]="pass"
    [db_integrity]="pass"
    [disk_space]="pass"
    [git_status]="pass"
    [stale_locks]="pass"
    [error_rate]="pass"
)

WARNINGS=()
ERRORS=()
DETAILS=()

#
# Database connectivity check
#
check_db_connectivity() {
    log_debug "Checking database connectivity"

    if [ ! -f "$DB_PATH" ]; then
        HEALTH_RESULTS[db_connectivity]="fail"
        ERRORS+=("Database file not found: $DB_PATH")
        log_error "Database file not found" path="$DB_PATH"
        return 1
    fi

    if ! command -v sqlite3 &> /dev/null; then
        HEALTH_RESULTS[db_connectivity]="fail"
        ERRORS+=("sqlite3 command not found")
        log_error "sqlite3 command not found"
        return 1
    fi

    # Test basic query
    if ! sqlite3 "$DB_PATH" "SELECT 1" &> /dev/null; then
        HEALTH_RESULTS[db_connectivity]="fail"
        ERRORS+=("Cannot query database")
        log_error "Cannot query database" path="$DB_PATH"
        return 1
    fi

    DETAILS+=("Database connectivity: OK")
    log_debug "Database connectivity check passed"
    return 0
}

#
# Database integrity check
#
check_db_integrity() {
    log_debug "Checking database integrity"

    local integrity_result
    integrity_result=$(sqlite3 "$DB_PATH" "PRAGMA integrity_check;" 2>&1)

    if [ "$integrity_result" != "ok" ]; then
        HEALTH_RESULTS[db_integrity]="fail"
        ERRORS+=("Database integrity check failed: $integrity_result")
        log_error "Database integrity check failed" result="$integrity_result"
        return 1
    fi

    # Get database size
    local db_size_bytes
    db_size_bytes=$(stat -f%z "$DB_PATH" 2>/dev/null || stat -c%s "$DB_PATH" 2>/dev/null || echo "0")
    local db_size_mb=$((db_size_bytes / 1024 / 1024))

    DETAILS+=("Database size: ${db_size_mb}MB")
    log_debug "Database integrity check passed" size_mb="$db_size_mb"

    # Record metric
    if [ -f "$SCRIPT_DIR/lib/metrics.sh" ]; then
        source "$SCRIPT_DIR/lib/metrics.sh"
        metrics_init "$DB_PATH"
        metrics_record "db_size_mb" "$db_size_mb"
    fi

    return 0
}

#
# Disk space check
#
check_disk_space() {
    log_debug "Checking disk space"

    local disk_free_mb

    # Get free space in MB (cross-platform)
    if command -v df &> /dev/null; then
        # Try to get free space on the volume containing BASE_DIR
        local df_output
        df_output=$(df -m "$BASE_DIR" 2>/dev/null | tail -1)

        if [ -n "$df_output" ]; then
            # Extract available column (varies by platform)
            disk_free_mb=$(echo "$df_output" | awk '{print $4}')
        else
            disk_free_mb=0
        fi
    else
        disk_free_mb=0
    fi

    if [ "$disk_free_mb" -eq 0 ]; then
        WARNINGS+=("Could not determine disk space")
        HEALTH_RESULTS[disk_space]="warn"
        log_warn "Could not determine disk space"
        return 1
    fi

    DETAILS+=("Disk space available: ${disk_free_mb}MB")

    if [ "$disk_free_mb" -lt "$DISK_CRITICAL_THRESHOLD_MB" ]; then
        HEALTH_RESULTS[disk_space]="fail"
        ERRORS+=("Critical: Only ${disk_free_mb}MB disk space available")
        log_error "Critical disk space" available_mb="$disk_free_mb"
        return 1
    elif [ "$disk_free_mb" -lt "$DISK_WARN_THRESHOLD_MB" ]; then
        HEALTH_RESULTS[disk_space]="warn"
        WARNINGS+=("Low disk space: ${disk_free_mb}MB available")
        log_warn "Low disk space" available_mb="$disk_free_mb"
        return 1
    fi

    log_debug "Disk space check passed" available_mb="$disk_free_mb"

    # Record metric
    if [ -f "$SCRIPT_DIR/lib/metrics.sh" ]; then
        source "$SCRIPT_DIR/lib/metrics.sh"
        metrics_init "$DB_PATH"
        metrics_record "disk_free_mb" "$disk_free_mb"
    fi

    return 0
}

#
# Git status check
#
check_git_status() {
    log_debug "Checking git status"

    if [ ! -d "$BASE_DIR/.git" ]; then
        WARNINGS+=("Not a git repository")
        HEALTH_RESULTS[git_status]="warn"
        log_warn "Not a git repository"
        return 1
    fi

    cd "$BASE_DIR"

    # Check for uncommitted changes
    if ! git diff-index --quiet HEAD -- 2>/dev/null; then
        WARNINGS+=("Uncommitted changes in git")
        HEALTH_RESULTS[git_status]="warn"
        log_warn "Uncommitted changes detected"
        DETAILS+=("Git: Uncommitted changes present")
    else
        DETAILS+=("Git: Clean working directory")
        log_debug "Git working directory is clean"
    fi

    # Check if we can access the repo
    if ! git status &> /dev/null; then
        ERRORS+=("Cannot access git repository")
        HEALTH_RESULTS[git_status]="fail"
        log_error "Cannot access git repository"
        return 1
    fi

    return 0
}

#
# Stale lock detection
#
check_stale_locks() {
    log_debug "Checking for stale locks"

    local stale_count=0
    local lock_age_threshold=$((MAX_STALE_LOCK_AGE_MINUTES * 60))

    # Check for directory-based locks
    if [ -d "$BASE_DIR/.git" ]; then
        # Find .dir lock directories older than threshold
        local current_time
        current_time=$(date +%s)

        while IFS= read -r -d '' lock_dir; do
            local lock_time
            lock_time=$(stat -f%m "$lock_dir" 2>/dev/null || stat -c%Y "$lock_dir" 2>/dev/null || echo "0")

            if [ "$lock_time" -gt 0 ]; then
                local age=$((current_time - lock_time))
                if [ "$age" -gt "$lock_age_threshold" ]; then
                    ((stale_count++))
                    WARNINGS+=("Stale lock found: $lock_dir (age: $((age / 60)) minutes)")
                    log_warn "Stale lock detected" path="$lock_dir" age_minutes="$((age / 60))"
                fi
            fi
        done < <(find "$BASE_DIR/.git" -name "*.dir" -type d -print0 2>/dev/null)

        # Check for file-based locks (git index.lock, etc)
        if [ -f "$BASE_DIR/.git/index.lock" ]; then
            local lock_time
            lock_time=$(stat -f%m "$BASE_DIR/.git/index.lock" 2>/dev/null || stat -c%Y "$BASE_DIR/.git/index.lock" 2>/dev/null || echo "0")
            local age=$((current_time - lock_time))

            if [ "$age" -gt "$lock_age_threshold" ]; then
                ((stale_count++))
                WARNINGS+=("Stale git index.lock found (age: $((age / 60)) minutes)")
                log_warn "Stale git lock detected" path="index.lock" age_minutes="$((age / 60))"
            fi
        fi
    fi

    if [ "$stale_count" -gt 0 ]; then
        HEALTH_RESULTS[stale_locks]="warn"
        DETAILS+=("Stale locks: $stale_count found")
    else
        DETAILS+=("Stale locks: None found")
        log_debug "No stale locks detected"
    fi

    return 0
}

#
# Error rate check (from logs)
#
check_error_rate() {
    log_debug "Checking error rate in logs"

    if [ ! -d "$LOGS_DIR" ]; then
        DETAILS+=("Error rate: No logs directory")
        log_debug "Logs directory not found"
        return 0
    fi

    # Check today's log file
    local today_log="$LOGS_DIR/$(date +%Y%m%d).log"

    if [ ! -f "$today_log" ]; then
        DETAILS+=("Error rate: No log file for today")
        log_debug "No log file for today"
        return 0
    fi

    # Count errors in last hour
    local hour_ago
    hour_ago=$(date -d '1 hour ago' '+%Y-%m-%d %H' 2>/dev/null || date -v-1H '+%Y-%m-%d %H' 2>/dev/null || echo "")

    if [ -n "$hour_ago" ]; then
        local error_count
        error_count=$(grep -c "\[ERROR\]\|\[FATAL\]" "$today_log" 2>/dev/null || echo "0")

        DETAILS+=("Error count (today): $error_count")

        if [ "$error_count" -gt 50 ]; then
            HEALTH_RESULTS[error_rate]="fail"
            ERRORS+=("High error rate: $error_count errors today")
            log_error "High error rate detected" count="$error_count"
        elif [ "$error_count" -gt 10 ]; then
            HEALTH_RESULTS[error_rate]="warn"
            WARNINGS+=("Elevated error rate: $error_count errors today")
            log_warn "Elevated error rate" count="$error_count"
        else
            log_debug "Error rate normal" count="$error_count"
        fi

        # Record metric
        if [ -f "$SCRIPT_DIR/lib/metrics.sh" ]; then
            source "$SCRIPT_DIR/lib/metrics.sh"
            metrics_init "$DB_PATH"
            metrics_record "error_count" "$error_count"
        fi
    fi

    return 0
}

#
# Determine overall health status
#
determine_overall_status() {
    local has_failures=false
    local has_warnings=false

    for check in "${!HEALTH_RESULTS[@]}"; do
        if [ "$check" != "status" ]; then
            if [ "${HEALTH_RESULTS[$check]}" = "fail" ]; then
                has_failures=true
            elif [ "${HEALTH_RESULTS[$check]}" = "warn" ]; then
                has_warnings=true
            fi
        fi
    done

    if [ "$has_failures" = true ]; then
        HEALTH_RESULTS[status]="critical"
        return 2
    elif [ "$has_warnings" = true ]; then
        HEALTH_RESULTS[status]="degraded"
        return 1
    else
        HEALTH_RESULTS[status]="healthy"
        return 0
    fi
}

#
# Output results
#
output_results() {
    local exit_code="$1"

    if [ "$JSON_OUTPUT" = true ]; then
        # JSON output
        echo "{"
        echo "  \"status\": \"${HEALTH_RESULTS[status]}\","
        echo "  \"timestamp\": \"$(date -u '+%Y-%m-%dT%H:%M:%SZ')\","
        echo "  \"checks\": {"

        local first=true
        for check in db_connectivity db_integrity disk_space git_status stale_locks error_rate; do
            if [ "$first" = true ]; then
                first=false
            else
                echo ","
            fi
            echo -n "    \"$check\": \"${HEALTH_RESULTS[$check]}\""
        done

        echo ""
        echo "  },"

        # Errors
        echo "  \"errors\": ["
        if [ ${#ERRORS[@]} -gt 0 ]; then
            for i in "${!ERRORS[@]}"; do
                echo -n "    \"${ERRORS[$i]}\""
                [ $i -lt $((${#ERRORS[@]} - 1)) ] && echo "," || echo ""
            done
        fi
        echo "  ],"

        # Warnings
        echo "  \"warnings\": ["
        if [ ${#WARNINGS[@]} -gt 0 ]; then
            for i in "${!WARNINGS[@]}"; do
                echo -n "    \"${WARNINGS[$i]}\""
                [ $i -lt $((${#WARNINGS[@]} - 1)) ] && echo "," || echo ""
            done
        fi
        echo "  ],"

        # Details
        echo "  \"details\": ["
        if [ ${#DETAILS[@]} -gt 0 ]; then
            for i in "${!DETAILS[@]}"; do
                echo -n "    \"${DETAILS[$i]}\""
                [ $i -lt $((${#DETAILS[@]} - 1)) ] && echo "," || echo ""
            done
        fi
        echo "  ]"

        echo "}"
    else
        # Text output
        echo "=== Emergent Learning Framework - Health Check ==="
        echo ""
        echo "Status: ${HEALTH_RESULTS[status]^^}"
        echo "Timestamp: $(date '+%Y-%m-%d %H:%M:%S')"
        echo ""

        if [ "$VERBOSE" = true ] || [ "$exit_code" -ne 0 ]; then
            echo "Check Results:"
            for check in db_connectivity db_integrity disk_space git_status stale_locks error_rate; do
                local status="${HEALTH_RESULTS[$check]}"
                local indicator="✓"
                [ "$status" = "warn" ] && indicator="⚠"
                [ "$status" = "fail" ] && indicator="✗"
                printf "  %-20s %s\n" "$check:" "$indicator $status"
            done
            echo ""
        fi

        if [ ${#ERRORS[@]} -gt 0 ]; then
            echo "Errors:"
            for error in "${ERRORS[@]}"; do
                echo "  ✗ $error"
            done
            echo ""
        fi

        if [ ${#WARNINGS[@]} -gt 0 ]; then
            echo "Warnings:"
            for warning in "${WARNINGS[@]}"; do
                echo "  ⚠ $warning"
            done
            echo ""
        fi

        if [ "$VERBOSE" = true ] && [ ${#DETAILS[@]} -gt 0 ]; then
            echo "Details:"
            for detail in "${DETAILS[@]}"; do
                echo "  • $detail"
            done
            echo ""
        fi
    fi
}

#
# Record health check results to database
#
record_health_check() {
    local status="${HEALTH_RESULTS[status]}"
    local db_integrity="${HEALTH_RESULTS[db_integrity]}"

    # Get DB size
    local db_size_bytes
    db_size_bytes=$(stat -f%z "$DB_PATH" 2>/dev/null || stat -c%s "$DB_PATH" 2>/dev/null || echo "0")
    local db_size_mb=$(echo "scale=2; $db_size_bytes / 1024 / 1024" | bc 2>/dev/null || echo "0")

    # Get disk free
    local disk_free_mb=0
    if command -v df &> /dev/null; then
        local df_output
        df_output=$(df -m "$BASE_DIR" 2>/dev/null | tail -1)
        [ -n "$df_output" ] && disk_free_mb=$(echo "$df_output" | awk '{print $4}')
    fi

    # Git status
    local git_status="${HEALTH_RESULTS[git_status]}"

    # Stale locks count
    local stale_locks=0
    for warning in "${WARNINGS[@]}"; do
        [[ "$warning" =~ "Stale lock" ]] && ((stale_locks++))
    done

    # Build details JSON
    local details_json="{\"errors\": [$(printf '"%s",' "${ERRORS[@]}" | sed 's/,$//')],"
    details_json+="\"warnings\": [$(printf '"%s",' "${WARNINGS[@]}" | sed 's/,$//')]}"

    # Escape for SQL
    details_json="${details_json//\'/\'\'}"

    # Insert into database
    sqlite3 "$DB_PATH" <<SQL 2>/dev/null || true
INSERT INTO system_health (status, db_integrity, db_size_mb, disk_free_mb, git_status, stale_locks, details)
VALUES ('$status', '$db_integrity', $db_size_mb, $disk_free_mb, '$git_status', $stale_locks, '$details_json');
SQL
}

#
# Main execution
#

log_info "Starting health check"

# Run all checks
check_db_connectivity
check_db_integrity
check_disk_space
check_git_status
check_stale_locks
check_error_rate

# Determine overall status
determine_overall_status
exit_code=$?

# Record to database (if DB is accessible)
if [ "${HEALTH_RESULTS[db_connectivity]}" = "pass" ]; then
    record_health_check
fi

# Output results
output_results "$exit_code"

log_info "Health check completed" status="${HEALTH_RESULTS[status]}" exit_code="$exit_code"

exit "$exit_code"
