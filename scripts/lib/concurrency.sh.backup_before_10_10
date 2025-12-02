#!/bin/bash
# Concurrency library for Emergent Learning Framework
# Provides robust locking, retry logic, and atomic operations

# SQLite retry function with exponential backoff and jitter
sqlite_with_retry() {
    local max_attempts="${SQLITE_MAX_ATTEMPTS:-5}"
    local attempt=1
    local exit_code

    while [ $attempt -le $max_attempts ]; do
        if sqlite3 "$@" 2>/dev/null; then
            return 0
        fi
        exit_code=$?

        if [ $attempt -lt $max_attempts ]; then
            # Exponential backoff: 0.1s, 0.2s, 0.4s, 0.8s, 1.6s (base 0.1 * 2^(n-1))
            # Jitter: +/- 50% randomization to prevent thundering herd
            local base_sleep=$(awk "BEGIN {print 0.1 * (2^($attempt-1))}")
            local jitter=$(awk "BEGIN {srand(); print rand() * $base_sleep}")
            local sleep_time=$(awk "BEGIN {print $base_sleep + $jitter}")

            log "WARN" "SQLite busy, retry $attempt/$max_attempts (sleeping ${sleep_time}s)..."
            echo "SQLite busy, retry $attempt/$max_attempts (sleeping ${sleep_time}s)..." >&2

            sleep "$sleep_time"
        fi
        ((attempt++))
    done

    log "ERROR" "SQLite failed after $max_attempts attempts"
    echo "SQLite failed after $max_attempts attempts" >&2
    return $exit_code
}

# Detect and clean stale locks
detect_stale_lock() {
    local lock_dir="$1"
    local max_age_seconds="${2:-300}"  # 5 minutes default

    if [ ! -d "$lock_dir" ]; then
        return 1  # Not stale, doesn't exist
    fi

    # Get lock age (cross-platform stat)
    local lock_mtime
    if stat -c %Y "$lock_dir" &>/dev/null; then
        # GNU stat (Linux)
        lock_mtime=$(stat -c %Y "$lock_dir")
    elif stat -f %m "$lock_dir" &>/dev/null; then
        # BSD stat (macOS)
        lock_mtime=$(stat -f %m "$lock_dir")
    else
        # Fallback: assume recent if we can't determine age
        log "WARN" "Cannot determine lock age, assuming recent"
        return 1
    fi

    local current_time=$(date +%s)
    local lock_age=$((current_time - lock_mtime))

    if [ "$lock_age" -gt "$max_age_seconds" ]; then
        log "WARN" "Stale lock detected: $lock_dir (age: ${lock_age}s, max: ${max_age_seconds}s)"
        return 0  # Stale
    fi

    return 1  # Not stale
}

# Clean stale lock with safety checks
clean_stale_lock() {
    local lock_dir="$1"

    # Double-check it's actually stale before removing
    if detect_stale_lock "$lock_dir" 300; then
        log "INFO" "Cleaning stale lock: $lock_dir"

        # Safety: verify it's in our .git directory
        if [[ "$lock_dir" != *"/.git/"* ]]; then
            log "ERROR" "SECURITY: Refusing to remove lock outside .git: $lock_dir"
            return 1
        fi

        # Safety: verify it's a directory, not a file
        if [ ! -d "$lock_dir" ]; then
            log "ERROR" "SECURITY: Lock is not a directory: $lock_dir"
            return 1
        fi

        # Remove the stale lock
        if rmdir "$lock_dir" 2>/dev/null; then
            log "INFO" "Successfully cleaned stale lock: $lock_dir"
            return 0
        else
            log "WARN" "Failed to clean stale lock (may have been removed): $lock_dir"
            return 1
        fi
    fi

    return 1
}

# Acquire git lock with stale lock detection
acquire_git_lock() {
    local lock_file="$1"
    local timeout="${2:-10}"  # Reduced from 30s to 10s
    local wait_time=0
    local attempt=1

    # Check if flock is available (Linux/macOS with util-linux)
    if command -v flock &> /dev/null; then
        # Use flock for robust locking
        exec 200>"$lock_file"
        if flock -w "$timeout" 200; then
            log "DEBUG" "Acquired git lock (flock): $lock_file"
            return 0
        else
            log "ERROR" "Failed to acquire git lock (flock timeout): $lock_file"
            return 1
        fi
    else
        # Fallback for Windows/MSYS: directory-based locking with stale detection
        local lock_dir="${lock_file}.dir"

        # Check for and clean stale locks before acquiring
        clean_stale_lock "$lock_dir"

        # Retry with exponential backoff
        while [ $wait_time -lt $timeout ]; do
            if mkdir "$lock_dir" 2>/dev/null; then
                log "DEBUG" "Acquired git lock (mkdir): $lock_dir"
                return 0
            fi

            # Check if lock is stale on each retry
            if detect_stale_lock "$lock_dir" 60; then
                log "WARN" "Lock is stale during acquire attempt, cleaning..."
                clean_stale_lock "$lock_dir"
                # Immediately retry after cleaning stale lock
                continue
            fi

            # Exponential backoff with jitter
            local base_sleep=$(awk "BEGIN {print 0.1 * (2^($attempt-1))}")
            local jitter=$(awk "BEGIN {srand(); print rand() * 0.1}")
            local sleep_time=$(awk "BEGIN {print $base_sleep + $jitter}")

            # Cap sleep time at 2 seconds
            if (( $(awk "BEGIN {print ($sleep_time > 2.0)}") )); then
                sleep_time=2.0
            fi

            log "DEBUG" "Waiting for git lock: attempt $attempt (sleep ${sleep_time}s)"
            sleep "$sleep_time"

            wait_time=$((wait_time + ${sleep_time%.*} + 1))
            ((attempt++))
        done

        log "ERROR" "Failed to acquire git lock (timeout): $lock_dir"
        return 1
    fi
}

# Release git lock
release_git_lock() {
    local lock_file="$1"

    if command -v flock &> /dev/null; then
        # Release flock
        if flock -u 200 2>/dev/null; then
            log "DEBUG" "Released git lock (flock): $lock_file"
        fi
    else
        # Remove directory lock
        local lock_dir="${lock_file}.dir"
        if rmdir "$lock_dir" 2>/dev/null; then
            log "DEBUG" "Released git lock (mkdir): $lock_dir"
        else
            log "WARN" "Failed to release git lock (already released?): $lock_dir"
        fi
    fi
}

# Atomic file write using rename pattern
write_atomic() {
    local target_file="$1"
    local content="$2"
    local temp_file="${target_file}.tmp.$$"

    # Ensure parent directory exists
    local parent_dir=$(dirname "$target_file")
    mkdir -p "$parent_dir"

    # Write to temp file
    if ! printf "%s" "$content" > "$temp_file"; then
        log "ERROR" "Failed to write temp file: $temp_file"
        rm -f "$temp_file"
        return 1
    fi

    # Sync to disk (best effort, not all platforms support sync on files)
    sync 2>/dev/null || true

    # Atomic rename
    if ! mv -f "$temp_file" "$target_file"; then
        log "ERROR" "Failed to atomic rename: $temp_file -> $target_file"
        rm -f "$temp_file"
        return 1
    fi

    log "DEBUG" "Atomic write successful: $target_file"
    return 0
}

# Atomic file append using rename pattern
append_atomic() {
    local target_file="$1"
    local content="$2"
    local temp_file="${target_file}.append.$$"

    # If target exists, copy to temp; otherwise create empty temp
    if [ -f "$target_file" ]; then
        cp "$target_file" "$temp_file"
    else
        touch "$temp_file"
    fi

    # Append to temp file
    if ! printf "%s" "$content" >> "$temp_file"; then
        log "ERROR" "Failed to append to temp file: $temp_file"
        rm -f "$temp_file"
        return 1
    fi

    # Sync to disk
    sync 2>/dev/null || true

    # Atomic rename
    if ! mv -f "$temp_file" "$target_file"; then
        log "ERROR" "Failed to atomic rename: $temp_file -> $target_file"
        rm -f "$temp_file"
        return 1
    fi

    log "DEBUG" "Atomic append successful: $target_file"
    return 0
}

# Escape single quotes for SQL injection protection
escape_sql() {
    echo "${1//\'/\'\'}"
}

# Validate severity is integer 1-5
validate_severity() {
    local severity="$1"

    # Convert word to number
    case "$severity" in
        1|2|3|4|5) echo "$severity"; return 0 ;;
        low) echo "2"; return 0 ;;
        medium) echo "3"; return 0 ;;
        high) echo "4"; return 0 ;;
        critical) echo "5"; return 0 ;;
        *) echo "3"; return 0 ;;  # default
    esac
}

# Validate confidence is decimal 0.0-1.0
validate_confidence() {
    local confidence="$1"

    # Convert word to number
    case "$confidence" in
        low) echo "0.3"; return 0 ;;
        medium) echo "0.6"; return 0 ;;
        high) echo "0.85"; return 0 ;;
    esac

    # Validate decimal
    if [[ "$confidence" =~ ^(0(\.[0-9]+)?|1(\.0+)?)$ ]]; then
        echo "$confidence"
        return 0
    else
        echo "0.7"  # default
        return 0
    fi
}

# Export functions for use in scripts
export -f sqlite_with_retry
export -f detect_stale_lock
export -f clean_stale_lock
export -f acquire_git_lock
export -f release_git_lock
export -f write_atomic
export -f append_atomic
export -f escape_sql
export -f validate_severity
export -f validate_confidence
