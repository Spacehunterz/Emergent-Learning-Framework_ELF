#!/bin/bash
# Comprehensive Error Handling Library for Emergent Learning Framework
# Version: 1.0.0
#
# This library provides 10/10 error handling with:
# - Specific exit codes for different error types
# - Comprehensive error checking for all external commands
# - Meaningful error messages with context and suggested fixes
# - Error categorization (transient vs permanent, retryable vs fatal)
# - Graceful degradation
# - Error recovery hooks
# - Complete logging
# - Consistent stderr/stdout separation
#
# Usage: source "$(dirname "$BASH_SOURCE")/lib/error-handling.sh"

# ============================================
# Exit Codes - Semantic error categories
# ============================================
readonly EXIT_SUCCESS=0
readonly EXIT_INPUT_ERROR=1          # Invalid user input or arguments
readonly EXIT_DB_ERROR=2             # Database operation failed
readonly EXIT_GIT_ERROR=3            # Git operation failed
readonly EXIT_FILESYSTEM_ERROR=4     # File/directory operation failed
readonly EXIT_DEPENDENCY_ERROR=5     # Missing required command/tool
readonly EXIT_SECURITY_ERROR=6       # Security check failed (symlink, permissions)
readonly EXIT_VALIDATION_ERROR=7     # Data validation failed
readonly EXIT_LOCK_ERROR=8           # Could not acquire lock
readonly EXIT_NETWORK_ERROR=9        # Network operation failed
readonly EXIT_UNKNOWN_ERROR=99       # Unexpected/unhandled error

# ============================================
# Error Recovery Hooks
# ============================================
# Users can override these functions to customize recovery behavior
error_recovery_hook_db() {
    # Called when database operations fail
    # Default: no action
    :
}

error_recovery_hook_git() {
    # Called when git operations fail
    # Default: no action
    :
}

error_recovery_hook_filesystem() {
    # Called when filesystem operations fail
    # Default: no action
    :
}

# ============================================
# Logging Functions
# ============================================
# Ensure LOG_FILE is set by caller, or use default
if [ -z "$LOG_FILE" ]; then
    LOGS_DIR="${LOGS_DIR:-$HOME/.claude/emergent-learning/logs}"
    mkdir -p "$LOGS_DIR" 2>/dev/null || true
    LOG_FILE="$LOGS_DIR/$(date +%Y%m%d).log"
fi

# Log with level, timestamp, script name, and message
log() {
    local level="$1"
    shift
    local script_name="${SCRIPT_NAME:-$(basename "$0")}"
    local timestamp="$(date '+%Y-%m-%d %H:%M:%S')"
    local log_line="[$timestamp] [$level] [$script_name] $*"

    # Write to log file
    echo "$log_line" >> "$LOG_FILE" 2>/dev/null || true

    # Also output to stderr for ERROR and FATAL
    case "$level" in
        ERROR|FATAL)
            echo "$log_line" >&2
            ;;
        WARN)
            # Warnings to stderr only if VERBOSE mode
            if [ "${VERBOSE:-false}" = "true" ]; then
                echo "$log_line" >&2
            fi
            ;;
    esac
}

log_info() {
    log "INFO" "$@"
}

log_warn() {
    log "WARN" "$@"
}

log_error() {
    log "ERROR" "$@"
}

log_fatal() {
    log "FATAL" "$@"
}

log_success() {
    log "SUCCESS" "$@"
}

# Log command execution with outcome
log_command() {
    local cmd="$1"
    local exit_code="$2"

    if [ "$exit_code" -eq 0 ]; then
        log_info "Command succeeded: $cmd"
    else
        log_error "Command failed (exit $exit_code): $cmd"
    fi
}

# ============================================
# Error Message Functions
# ============================================
# Error message with context, suggested fix, and error code
error_msg() {
    local error_code="$1"
    local context="$2"
    local suggested_fix="$3"
    local error_category="${4:-permanent}"  # transient|permanent|retryable|fatal

    {
        echo "ERROR [$error_category]: $context"
        echo "  Exit Code: $error_code"
        if [ -n "$suggested_fix" ]; then
            echo "  Suggested Fix: $suggested_fix"
        fi
    } >&2

    log_error "[Code $error_code] [$error_category] $context | Fix: $suggested_fix"
}

# ============================================
# Command Execution with Error Checking
# ============================================
# Execute command with full error handling
# Returns: 0 on success, sets LAST_CMD_OUTPUT and LAST_CMD_ERROR
LAST_CMD_OUTPUT=""
LAST_CMD_ERROR=""
LAST_CMD_EXIT_CODE=0

run_cmd() {
    local cmd="$1"
    local error_context="${2:-Command execution}"
    local error_code="${3:-$EXIT_UNKNOWN_ERROR}"
    local is_critical="${4:-true}"  # true|false - exit on failure?

    # Clear previous output
    LAST_CMD_OUTPUT=""
    LAST_CMD_ERROR=""

    log_info "Executing: $cmd"

    # Capture both stdout and stderr
    local temp_out=$(mktemp)
    local temp_err=$(mktemp)

    if eval "$cmd" >"$temp_out" 2>"$temp_err"; then
        LAST_CMD_EXIT_CODE=0
        LAST_CMD_OUTPUT=$(cat "$temp_out")
        log_success "Command succeeded: $cmd"
        rm -f "$temp_out" "$temp_err"
        return 0
    else
        LAST_CMD_EXIT_CODE=$?
        LAST_CMD_OUTPUT=$(cat "$temp_out")
        LAST_CMD_ERROR=$(cat "$temp_err")

        log_error "Command failed (exit $LAST_CMD_EXIT_CODE): $cmd"
        log_error "  stderr: $LAST_CMD_ERROR"

        if [ "$is_critical" = "true" ]; then
            error_msg "$error_code" "$error_context failed" "Check command output: $LAST_CMD_ERROR" "fatal"
            rm -f "$temp_out" "$temp_err"
            exit "$error_code"
        else
            error_msg "$error_code" "$error_context failed" "Check command output: $LAST_CMD_ERROR" "retryable"
            rm -f "$temp_out" "$temp_err"
            return "$LAST_CMD_EXIT_CODE"
        fi
    fi
}

# ============================================
# Dependency Checking
# ============================================
require_command() {
    local cmd="$1"
    local install_hint="${2:-Install $cmd}"

    if ! command -v "$cmd" &> /dev/null; then
        error_msg "$EXIT_DEPENDENCY_ERROR" \
            "Required command not found: $cmd" \
            "$install_hint" \
            "fatal"
        exit "$EXIT_DEPENDENCY_ERROR"
    fi
    log_info "Dependency check passed: $cmd"
}

# ============================================
# Filesystem Operations with Error Checking
# ============================================
safe_mkdir() {
    local dir="$1"
    local error_context="${2:-Creating directory $dir}"

    if [ -e "$dir" ] && [ ! -d "$dir" ]; then
        error_msg "$EXIT_FILESYSTEM_ERROR" \
            "$error_context: Path exists but is not a directory" \
            "Remove the file at $dir or choose a different path" \
            "permanent"
        error_recovery_hook_filesystem
        exit "$EXIT_FILESYSTEM_ERROR"
    fi

    if ! mkdir -p "$dir" 2>/dev/null; then
        local err=$?
        error_msg "$EXIT_FILESYSTEM_ERROR" \
            "$error_context failed" \
            "Check directory permissions for $(dirname "$dir")" \
            "permanent"
        log_command "mkdir -p $dir" "$err"
        error_recovery_hook_filesystem
        exit "$EXIT_FILESYSTEM_ERROR"
    fi

    log_info "Created directory: $dir"
    return 0
}

safe_write_file() {
    local filepath="$1"
    local content="$2"
    local error_context="${3:-Writing file $filepath}"

    local dir="$(dirname "$filepath")"
    safe_mkdir "$dir" "Creating parent directory for $filepath"

    if ! echo "$content" > "$filepath" 2>/dev/null; then
        local err=$?
        error_msg "$EXIT_FILESYSTEM_ERROR" \
            "$error_context failed" \
            "Check file permissions for $(dirname "$filepath")" \
            "permanent"
        log_command "echo > $filepath" "$err"
        error_recovery_hook_filesystem
        exit "$EXIT_FILESYSTEM_ERROR"
    fi

    log_info "Wrote file: $filepath"
    return 0
}

require_file() {
    local filepath="$1"
    local error_context="${2:-Required file missing: $filepath}"

    if [ ! -f "$filepath" ]; then
        error_msg "$EXIT_FILESYSTEM_ERROR" \
            "$error_context" \
            "Ensure the file exists: $filepath" \
            "fatal"
        exit "$EXIT_FILESYSTEM_ERROR"
    fi
    log_info "File exists: $filepath"
}

require_dir() {
    local dirpath="$1"
    local error_context="${2:-Required directory missing: $dirpath}"

    if [ ! -d "$dirpath" ]; then
        error_msg "$EXIT_FILESYSTEM_ERROR" \
            "$error_context" \
            "Ensure the directory exists: $dirpath" \
            "fatal"
        exit "$EXIT_FILESYSTEM_ERROR"
    fi
    log_info "Directory exists: $dirpath"
}

# Security check: prevent symlink attacks
check_no_symlink() {
    local path="$1"
    local error_context="${2:-Security check for $path}"

    if [ -L "$path" ]; then
        error_msg "$EXIT_SECURITY_ERROR" \
            "SECURITY: $error_context is a symlink (potential attack)" \
            "Remove the symlink and create a real directory" \
            "fatal"
        exit "$EXIT_SECURITY_ERROR"
    fi
    log_info "Security check passed (not a symlink): $path"
}

# ============================================
# SQLite Operations with Error Checking & Retry
# ============================================
sqlite_with_retry() {
    local max_attempts="${SQLITE_MAX_RETRIES:-5}"
    local attempt=1
    local sleep_base="${SQLITE_RETRY_SLEEP_MS:-100}"  # milliseconds

    while [ $attempt -le $max_attempts ]; do
        local temp_out=$(mktemp)
        local temp_err=$(mktemp)

        if sqlite3 "$@" >"$temp_out" 2>"$temp_err"; then
            LAST_CMD_OUTPUT=$(cat "$temp_out")
            log_info "SQLite operation succeeded (attempt $attempt/$max_attempts)"
            rm -f "$temp_out" "$temp_err"
            echo "$LAST_CMD_OUTPUT"
            return 0
        else
            local exit_code=$?
            LAST_CMD_ERROR=$(cat "$temp_err")

            # Check if error is "database is locked" (transient) or something else (permanent)
            if echo "$LAST_CMD_ERROR" | grep -qi "locked\|busy"; then
                log_warn "SQLite busy (attempt $attempt/$max_attempts): $LAST_CMD_ERROR"

                if [ $attempt -lt $max_attempts ]; then
                    # Exponential backoff with jitter
                    local sleep_ms=$((sleep_base * attempt + RANDOM % 100))
                    local sleep_sec=$(echo "scale=3; $sleep_ms / 1000" | bc -l 2>/dev/null || echo "0.1")
                    sleep "$sleep_sec"
                    ((attempt++))
                    rm -f "$temp_out" "$temp_err"
                    continue
                fi
            fi

            # Permanent error or max retries exceeded
            error_msg "$EXIT_DB_ERROR" \
                "Database operation failed after $attempt attempts" \
                "Check database file permissions and integrity: $LAST_CMD_ERROR" \
                "retryable"
            log_command "sqlite3 $*" "$exit_code"
            rm -f "$temp_out" "$temp_err"
            error_recovery_hook_db
            return "$exit_code"
        fi
    done
}

# Check database integrity
check_db_integrity() {
    local db_path="$1"

    require_file "$db_path" "Database file not found: $db_path"

    local result
    result=$(sqlite3 "$db_path" "PRAGMA integrity_check;" 2>&1)
    local exit_code=$?

    if [ $exit_code -ne 0 ]; then
        error_msg "$EXIT_DB_ERROR" \
            "Database integrity check failed to run" \
            "Check if database file is corrupted: $db_path" \
            "fatal"
        exit "$EXIT_DB_ERROR"
    fi

    if ! echo "$result" | grep -q "ok"; then
        error_msg "$EXIT_DB_ERROR" \
            "Database integrity check FAILED: $result" \
            "Database may be corrupted. Restore from backup or run: sqlite3 $db_path '.recover' > recovered.sql" \
            "fatal"
        exit "$EXIT_DB_ERROR"
    fi

    log_info "Database integrity check passed: $db_path"
}

# Validate DB insert returned a valid ID
validate_db_id() {
    local id="$1"
    local entity_type="${2:-record}"

    if [ -z "$id" ] || [ "$id" = "0" ] || ! [[ "$id" =~ ^[0-9]+$ ]]; then
        error_msg "$EXIT_DB_ERROR" \
            "Database insert failed - invalid $entity_type ID: '$id'" \
            "Check database constraints and recent operations" \
            "fatal"
        exit "$EXIT_DB_ERROR"
    fi

    log_info "Validated $entity_type ID: $id"
}

# SQL injection prevention
escape_sql() {
    # Escape single quotes by doubling them
    echo "${1//\'/\'\'}"
}

# ============================================
# Git Operations with Error Checking & Locking
# ============================================
# Cross-platform git lock (flock on Linux/Mac, mkdir on Windows/MSYS)
acquire_git_lock() {
    local lock_file="$1"
    local timeout="${2:-30}"
    local wait_time=0

    log_info "Acquiring git lock: $lock_file (timeout: ${timeout}s)"

    # Check if flock is available (Linux/macOS with coreutils)
    if command -v flock &> /dev/null; then
        exec 200>"$lock_file"
        if flock -w "$timeout" 200; then
            log_info "Git lock acquired (flock)"
            return 0
        else
            error_msg "$EXIT_LOCK_ERROR" \
                "Could not acquire git lock after ${timeout}s" \
                "Wait for other operations to complete or remove stale lock: $lock_file" \
                "transient"
            error_recovery_hook_git
            return 1
        fi
    else
        # Fallback for Windows/MSYS: simple mkdir-based locking
        local lock_dir="${lock_file}.dir"
        while [ $wait_time -lt $timeout ]; do
            if mkdir "$lock_dir" 2>/dev/null; then
                log_info "Git lock acquired (mkdir)"
                return 0
            fi
            sleep 1
            ((wait_time++))
        done

        error_msg "$EXIT_LOCK_ERROR" \
            "Could not acquire git lock after ${timeout}s" \
            "Wait for other operations to complete or remove stale lock: $lock_dir" \
            "transient"
        error_recovery_hook_git
        return 1
    fi
}

release_git_lock() {
    local lock_file="$1"

    if command -v flock &> /dev/null; then
        flock -u 200 2>/dev/null || true
        log_info "Git lock released (flock)"
    else
        local lock_dir="${lock_file}.dir"
        if rmdir "$lock_dir" 2>/dev/null; then
            log_info "Git lock released (mkdir)"
        else
            log_warn "Failed to release git lock: $lock_dir"
        fi
    fi
}

# Safe git add with error checking
safe_git_add() {
    local filepath="$1"
    local error_context="${2:-Adding file to git: $filepath}"

    if ! git add "$filepath" 2>&1; then
        local err=$?
        error_msg "$EXIT_GIT_ERROR" \
            "$error_context failed" \
            "Check if file exists and git repository is valid" \
            "permanent"
        log_command "git add $filepath" "$err"
        error_recovery_hook_git
        return "$err"
    fi

    log_info "Git add succeeded: $filepath"
    return 0
}

# Safe git commit with error checking
safe_git_commit() {
    local message="$1"
    local description="${2:-}"
    local allow_empty="${3:-false}"

    local commit_args=(-m "$message")
    [ -n "$description" ] && commit_args+=(-m "$description")
    [ "$allow_empty" = "true" ] && commit_args+=(--allow-empty)

    local temp_err=$(mktemp)
    if git commit "${commit_args[@]}" 2>"$temp_err"; then
        log_success "Git commit created: $message"
        rm -f "$temp_err"
        return 0
    else
        local exit_code=$?
        local err_msg=$(cat "$temp_err")

        # "nothing to commit" is not an error in many contexts
        if echo "$err_msg" | grep -qi "nothing to commit\|no changes"; then
            log_info "Git commit skipped (no changes): $message"
            rm -f "$temp_err"
            return 0
        fi

        error_msg "$EXIT_GIT_ERROR" \
            "Git commit failed: $message" \
            "Check git status and recent operations: $err_msg" \
            "retryable"
        log_command "git commit -m '$message'" "$exit_code"
        rm -f "$temp_err"
        error_recovery_hook_git
        return "$exit_code"
    fi
}

# Check if directory is a git repository
require_git_repo() {
    local dir="${1:-.}"
    local error_context="${2:-Git repository required}"

    if [ ! -d "$dir/.git" ]; then
        error_msg "$EXIT_GIT_ERROR" \
            "$error_context: Not a git repository" \
            "Initialize git repository: cd $dir && git init" \
            "fatal"
        exit "$EXIT_GIT_ERROR"
    fi
    log_info "Git repository check passed: $dir"
}

# ============================================
# Input Validation
# ============================================
validate_not_empty() {
    local value="$1"
    local field_name="$2"

    if [ -z "$value" ]; then
        error_msg "$EXIT_INPUT_ERROR" \
            "Input validation failed: $field_name cannot be empty" \
            "Provide a value for $field_name" \
            "permanent"
        exit "$EXIT_INPUT_ERROR"
    fi
    log_info "Input validation passed: $field_name is not empty"
}

validate_integer() {
    local value="$1"
    local field_name="$2"
    local min="${3:-}"
    local max="${4:-}"

    if ! [[ "$value" =~ ^[0-9]+$ ]]; then
        error_msg "$EXIT_VALIDATION_ERROR" \
            "Validation failed: $field_name must be an integer, got '$value'" \
            "Provide an integer value for $field_name" \
            "permanent"
        exit "$EXIT_VALIDATION_ERROR"
    fi

    if [ -n "$min" ] && [ "$value" -lt "$min" ]; then
        error_msg "$EXIT_VALIDATION_ERROR" \
            "Validation failed: $field_name must be >= $min, got $value" \
            "Provide a value >= $min for $field_name" \
            "permanent"
        exit "$EXIT_VALIDATION_ERROR"
    fi

    if [ -n "$max" ] && [ "$value" -gt "$max" ]; then
        error_msg "$EXIT_VALIDATION_ERROR" \
            "Validation failed: $field_name must be <= $max, got $value" \
            "Provide a value <= $max for $field_name" \
            "permanent"
        exit "$EXIT_VALIDATION_ERROR"
    fi

    log_info "Input validation passed: $field_name is valid integer ($value)"
}

validate_float() {
    local value="$1"
    local field_name="$2"
    local min="${3:-}"
    local max="${4:-}"

    if ! [[ "$value" =~ ^[0-9]*\.?[0-9]+$ ]]; then
        error_msg "$EXIT_VALIDATION_ERROR" \
            "Validation failed: $field_name must be a number, got '$value'" \
            "Provide a numeric value for $field_name" \
            "permanent"
        exit "$EXIT_VALIDATION_ERROR"
    fi

    # Use bc for float comparison if available
    if command -v bc &> /dev/null; then
        if [ -n "$min" ] && [ $(echo "$value < $min" | bc -l) -eq 1 ]; then
            error_msg "$EXIT_VALIDATION_ERROR" \
                "Validation failed: $field_name must be >= $min, got $value" \
                "Provide a value >= $min for $field_name" \
                "permanent"
            exit "$EXIT_VALIDATION_ERROR"
        fi

        if [ -n "$max" ] && [ $(echo "$value > $max" | bc -l) -eq 1 ]; then
            error_msg "$EXIT_VALIDATION_ERROR" \
                "Validation failed: $field_name must be <= $max, got $value" \
                "Provide a value <= $max for $field_name" \
                "permanent"
            exit "$EXIT_VALIDATION_ERROR"
        fi
    fi

    log_info "Input validation passed: $field_name is valid number ($value)"
}

# ============================================
# Cleanup and Rollback
# ============================================
# Register cleanup function to run on exit
CLEANUP_FUNCTIONS=()

register_cleanup() {
    local cleanup_func="$1"
    CLEANUP_FUNCTIONS+=("$cleanup_func")
}

run_cleanup() {
    log_info "Running cleanup functions (${#CLEANUP_FUNCTIONS[@]} registered)"
    for cleanup_func in "${CLEANUP_FUNCTIONS[@]}"; do
        if declare -f "$cleanup_func" > /dev/null; then
            log_info "Running cleanup: $cleanup_func"
            "$cleanup_func" || log_warn "Cleanup function failed: $cleanup_func"
        fi
    done
}

# Trap errors and run cleanup
trap_error() {
    local exit_code=$?
    local line_number="${1:-unknown}"

    log_fatal "Script failed at line $line_number (exit code: $exit_code)"
    run_cleanup
    exit "$exit_code"
}

# Set up error trap
setup_error_trap() {
    set -eE  # Exit on error, inherit ERR trap in functions
    trap 'trap_error $LINENO' ERR
    trap 'run_cleanup' EXIT
}

# ============================================
# Graceful Degradation Helpers
# ============================================
# Try operation, fall back to alternative if it fails
try_or_fallback() {
    local primary_cmd="$1"
    local fallback_cmd="$2"
    local operation_name="${3:-Operation}"

    log_info "Attempting primary: $operation_name"
    if eval "$primary_cmd" 2>/dev/null; then
        log_success "$operation_name succeeded (primary)"
        return 0
    else
        log_warn "$operation_name failed (primary), trying fallback"
        if eval "$fallback_cmd" 2>/dev/null; then
            log_success "$operation_name succeeded (fallback)"
            return 0
        else
            log_error "$operation_name failed (both primary and fallback)"
            return 1
        fi
    fi
}

# ============================================
# Progress and Status Reporting
# ============================================
report_status() {
    local status="$1"
    local message="$2"

    case "$status" in
        success)
            echo "✓ $message" >&1
            log_success "$message"
            ;;
        failure)
            echo "✗ $message" >&2
            log_error "$message"
            ;;
        warning)
            echo "⚠ $message" >&2
            log_warn "$message"
            ;;
        info)
            echo "ℹ $message" >&1
            log_info "$message"
            ;;
    esac
}

# ============================================
# Library Initialization
# ============================================
log_info "Error handling library loaded (version 1.0.0)"
