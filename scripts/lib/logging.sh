#!/bin/bash
# Structured logging library for Emergent Learning Framework
#
# Usage:
#   source "$(dirname "${BASH_SOURCE[0]}")/../lib/logging.sh"
#   log_init "my-script"
#   log_info "Starting operation" operation="create" record_id="123"
#   log_error "Failed to connect" error_code="500"
#   log_metric "operation_duration" 1.234
#
# Features:
# - Multiple output formats: text (default), json
# - Log levels: DEBUG, INFO, WARN, ERROR, FATAL
# - Correlation IDs for request tracing
# - Performance timing
# - Context fields (script, operation, record_id)
# - Automatic log rotation

# Configuration (can be overridden via environment variables)
LOG_LEVEL="${LOG_LEVEL:-INFO}"
LOG_FORMAT="${LOG_FORMAT:-text}"  # text or json
LOG_DIR="${LOG_DIR:-}"  # Set by log_init
LOG_FILE="${LOG_FILE:-}"  # Set by log_init
LOG_SCRIPT_NAME="${LOG_SCRIPT_NAME:-}"
LOG_CORRELATION_ID="${LOG_CORRELATION_ID:-}"

# Log level priorities (for filtering)
declare -A LOG_LEVELS=(
    [DEBUG]=0
    [INFO]=1
    [WARN]=2
    [ERROR]=3
    [FATAL]=4
)

# ANSI color codes for text output
declare -A LOG_COLORS=(
    [DEBUG]="\033[0;36m"    # Cyan
    [INFO]="\033[0;32m"     # Green
    [WARN]="\033[0;33m"     # Yellow
    [ERROR]="\033[0;31m"    # Red
    [FATAL]="\033[1;31m"    # Bold Red
    [RESET]="\033[0m"       # Reset
)

# Performance timing storage
declare -A LOG_TIMERS=()

#
# Initialize logging subsystem
#
# Args:
#   $1 - Script name (required)
#   $2 - Log directory (optional, defaults to ~/.claude/emergent-learning/logs)
#
log_init() {
    local script_name="$1"
    local log_dir="${2:-}"

    if [ -z "$script_name" ]; then
        echo "ERROR: log_init requires script name" >&2
        return 1
    fi

    LOG_SCRIPT_NAME="$script_name"

    # Set default log directory if not provided
    if [ -z "$log_dir" ]; then
        local home_dir="${HOME:-$USERPROFILE}"
        if [ -n "$home_dir" ]; then
            LOG_DIR="$home_dir/.claude/emergent-learning/logs"
        else
            LOG_DIR="/tmp/emergent-learning/logs"
        fi
    else
        LOG_DIR="$log_dir"
    fi

    # Create log directory
    mkdir -p "$LOG_DIR" 2>/dev/null || true

    # Set log file with date-based rotation
    LOG_FILE="$LOG_DIR/$(date +%Y%m%d).log"

    # Generate correlation ID if not already set
    if [ -z "$LOG_CORRELATION_ID" ]; then
        # Use process ID and timestamp for uniqueness
        LOG_CORRELATION_ID="$(printf "%08x-%04x" $$ $(date +%s | tail -c 5))"
    fi

    # Rotate old logs (keep last 30 days)
    _log_rotate_old_files

    return 0
}

#
# Rotate old log files
#
_log_rotate_old_files() {
    if [ -z "$LOG_DIR" ] || [ ! -d "$LOG_DIR" ]; then
        return 0
    fi

    # Find and remove log files older than 30 days
    # Using find with mtime is more portable than parsing dates
    find "$LOG_DIR" -name "*.log" -type f -mtime +30 -delete 2>/dev/null || true
}

#
# Check if a log level should be output
#
# Args:
#   $1 - Level to check
#
# Returns:
#   0 if should log, 1 if should skip
#
_log_should_output() {
    local level="$1"
    local configured_priority="${LOG_LEVELS[$LOG_LEVEL]:-1}"
    local current_priority="${LOG_LEVELS[$level]:-0}"

    [ "$current_priority" -ge "$configured_priority" ]
}

#
# Format log entry as JSON
#
# Args:
#   $1 - Level
#   $2 - Message
#   ${@:3} - Additional key=value pairs
#
_log_format_json() {
    local level="$1"
    local message="$2"
    shift 2

    local timestamp
    timestamp="$(date -u '+%Y-%m-%dT%H:%M:%S.%3NZ' 2>/dev/null || date -u '+%Y-%m-%dT%H:%M:%SZ')"

    # Start JSON object
    local json_parts=()
    json_parts+=("\"timestamp\":\"$timestamp\"")
    json_parts+=("\"level\":\"$level\"")
    json_parts+=("\"message\":\"$(echo "$message" | sed 's/"/\\"/g')\"")

    # Add script name if set
    [ -n "$LOG_SCRIPT_NAME" ] && json_parts+=("\"script\":\"$LOG_SCRIPT_NAME\"")

    # Add correlation ID if set
    [ -n "$LOG_CORRELATION_ID" ] && json_parts+=("\"correlation_id\":\"$LOG_CORRELATION_ID\"")

    # Add context fields
    local key value
    for arg in "$@"; do
        if [[ "$arg" =~ ^([^=]+)=(.*)$ ]]; then
            key="${BASH_REMATCH[1]}"
            value="${BASH_REMATCH[2]}"
            # Escape quotes in value
            value="$(echo "$value" | sed 's/"/\\"/g')"
            json_parts+=("\"$key\":\"$value\"")
        fi
    done

    # Join with commas
    local IFS=","
    echo "{${json_parts[*]}}"
}

#
# Format log entry as text
#
# Args:
#   $1 - Level
#   $2 - Message
#   ${@:3} - Additional key=value pairs
#
_log_format_text() {
    local level="$1"
    local message="$2"
    shift 2

    local timestamp
    timestamp="$(date '+%Y-%m-%d %H:%M:%S')"

    local color="${LOG_COLORS[$level]:-}"
    local reset="${LOG_COLORS[RESET]}"

    # Build context string
    local context=""
    [ -n "$LOG_SCRIPT_NAME" ] && context+="[$LOG_SCRIPT_NAME] "
    [ -n "$LOG_CORRELATION_ID" ] && context+="[corr:$LOG_CORRELATION_ID] "

    # Add key=value pairs
    for arg in "$@"; do
        context+="$arg "
    done

    # Format: [timestamp] [LEVEL] [context] message
    if [ -t 2 ]; then
        # Color output if terminal
        echo -e "${color}[$timestamp] [$level]${reset} $context$message"
    else
        # No color for pipes/files
        echo "[$timestamp] [$level] $context$message"
    fi
}

#
# Write log entry to file and stderr
#
# Args:
#   $1 - Level
#   $2 - Message
#   ${@:3} - Additional key=value pairs
#
_log_write() {
    local level="$1"
    local message="$2"
    shift 2

    # Check if we should output this level
    if ! _log_should_output "$level"; then
        return 0
    fi

    # Format based on LOG_FORMAT
    local output
    if [ "$LOG_FORMAT" = "json" ]; then
        output="$(_log_format_json "$level" "$message" "$@")"
    else
        output="$(_log_format_text "$level" "$message" "$@")"
    fi

    # Write to stderr (colored if terminal)
    echo "$output" >&2

    # Write to log file (always plain text)
    if [ -n "$LOG_FILE" ]; then
        if [ "$LOG_FORMAT" = "json" ]; then
            echo "$output" >> "$LOG_FILE"
        else
            # Remove ANSI codes for file output
            echo "$output" | sed 's/\x1b\[[0-9;]*m//g' >> "$LOG_FILE"
        fi
    fi
}

#
# Public logging functions
#

log_debug() {
    local message="$1"
    shift
    _log_write "DEBUG" "$message" "$@"
}

log_info() {
    local message="$1"
    shift
    _log_write "INFO" "$message" "$@"
}

log_warn() {
    local message="$1"
    shift
    _log_write "WARN" "$message" "$@"
}

log_error() {
    local message="$1"
    shift
    _log_write "ERROR" "$message" "$@"
}

log_fatal() {
    local message="$1"
    shift
    _log_write "FATAL" "$message" "$@"
}

#
# Performance timing functions
#

# Start a timer
# Args:
#   $1 - Timer name
log_timer_start() {
    local timer_name="$1"
    if [ -z "$timer_name" ]; then
        log_error "log_timer_start requires timer name"
        return 1
    fi
    LOG_TIMERS["$timer_name"]="$(date +%s%3N 2>/dev/null || date +%s)"
}

# Stop a timer and log duration
# Args:
#   $1 - Timer name
#   ${@:2} - Additional context fields
log_timer_stop() {
    local timer_name="$1"
    shift

    if [ -z "$timer_name" ]; then
        log_error "log_timer_stop requires timer name"
        return 1
    fi

    local start_time="${LOG_TIMERS[$timer_name]:-}"
    if [ -z "$start_time" ]; then
        log_warn "Timer not found" timer="$timer_name"
        return 1
    fi

    local end_time
    end_time="$(date +%s%3N 2>/dev/null || date +%s)"

    local duration=$((end_time - start_time))

    # Convert to seconds with decimals if we have milliseconds
    local duration_str
    if [[ "$end_time" =~ [0-9]{3}$ ]]; then
        # Has milliseconds
        duration_str="$(echo "scale=3; $duration / 1000" | bc 2>/dev/null || echo "$duration")"
    else
        duration_str="$duration"
    fi

    log_info "Timer completed" timer="$timer_name" duration_ms="$duration" duration_s="$duration_str" "$@"

    # Clean up
    unset LOG_TIMERS["$timer_name"]
}

#
# Metric logging (for metrics collection)
#
# Args:
#   $1 - Metric name
#   $2 - Metric value
#   ${@:3} - Additional tags
#
log_metric() {
    local metric_name="$1"
    local metric_value="$2"
    shift 2

    _log_write "INFO" "METRIC" metric="$metric_name" value="$metric_value" "$@"
}

#
# Set correlation ID for this session
#
# Args:
#   $1 - Correlation ID
#
log_set_correlation_id() {
    LOG_CORRELATION_ID="$1"
}

#
# Get current correlation ID
#
log_get_correlation_id() {
    echo "$LOG_CORRELATION_ID"
}

# Export functions for use in subshells
export -f log_debug log_info log_warn log_error log_fatal
export -f log_timer_start log_timer_stop log_metric
export -f log_set_correlation_id log_get_correlation_id
