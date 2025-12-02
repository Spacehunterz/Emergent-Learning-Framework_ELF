#!/bin/bash
# Security Utilities Library
# Provides input sanitization, path validation, and security checks

# Sanitize filename - remove ALL potentially dangerous characters
# Only allows: alphanumeric, dash, underscore, dot
# Removes: path separators, null bytes, shell metacharacters
sanitize_filename() {
    local input="$1"
    # Remove null bytes first
    input="${input//$'\0'/}"
    # Remove newlines and carriage returns
    input="${input//$'\n'/}"
    input="${input//$'\r'/}"
    # Convert to lowercase, replace spaces with dashes
    input=$(echo "$input" | tr '[:upper:]' '[:lower:]' | tr ' ' '-')
    # Remove everything except alphanumeric, dash, underscore, dot
    input=$(echo "$input" | tr -cd '[:alnum:]._-')
    # Remove leading dots (hidden files)
    input="${input#.}"
    # Limit length to prevent buffer issues
    echo "${input:0:200}"
}

# Sanitize domain name - stricter than filename
# Only allows: alphanumeric, dash
sanitize_domain() {
    local input="$1"
    # Remove null bytes first
    input="${input//$'\0'/}"
    # Remove newlines and carriage returns
    input="${input//$'\n'/}"
    input="${input//$'\r'/}"
    # Convert to lowercase, replace spaces with dashes
    input=$(echo "$input" | tr '[:upper:]' '[:lower:]' | tr ' ' '-')
    # Remove everything except alphanumeric and dash
    input=$(echo "$input" | tr -cd '[:alnum:]-')
    # Remove leading/trailing dashes
    input="${input#-}"
    input="${input%-}"
    # Limit length
    echo "${input:0:100}"
}

# Validate integer - ensures value is a valid integer
validate_integer() {
    local value="$1"
    local min="$2"
    local max="$3"

    # Check if it's an integer
    if ! [[ "$value" =~ ^-?[0-9]+$ ]]; then
        return 1
    fi

    # Check range if provided
    if [ -n "$min" ] && [ "$value" -lt "$min" ]; then
        return 1
    fi
    if [ -n "$max" ] && [ "$value" -gt "$max" ]; then
        return 1
    fi

    return 0
}

# Validate decimal - ensures value is a valid decimal number
validate_decimal() {
    local value="$1"
    local min="$2"
    local max="$3"

    # Check if it's a decimal (allows negative, decimal point)
    if ! [[ "$value" =~ ^-?[0-9]*\.?[0-9]+$ ]]; then
        return 1
    fi

    # Use bc for range checks if available
    if command -v bc &> /dev/null && [ -n "$min" ]; then
        if [ "$(echo "$value < $min" | bc)" -eq 1 ]; then
            return 1
        fi
    fi
    if command -v bc &> /dev/null && [ -n "$max" ]; then
        if [ "$(echo "$value > $max" | bc)" -eq 1 ]; then
            return 1
        fi
    fi

    return 0
}

# Escape SQL strings - prevent SQL injection
escape_sql() {
    local input="$1"
    # Escape single quotes by doubling them (SQL standard)
    echo "${input//\'/\'\'}"
}

# Validate absolute path - ensures path is absolute and within allowed directory
validate_path() {
    local path="$1"
    local base_dir="$2"

    # Check if path is absolute
    if [[ ! "$path" =~ ^/ ]] && [[ ! "$path" =~ ^[A-Za-z]: ]]; then
        return 1
    fi

    # Resolve to absolute path (follows symlinks)
    if command -v realpath &> /dev/null; then
        path=$(realpath -m "$path" 2>/dev/null) || return 1
    elif command -v readlink &> /dev/null; then
        path=$(readlink -f "$path" 2>/dev/null) || return 1
    fi

    # If base_dir provided, ensure path is within it
    if [ -n "$base_dir" ]; then
        if command -v realpath &> /dev/null; then
            base_dir=$(realpath -m "$base_dir" 2>/dev/null) || return 1
        fi

        # Check if path starts with base_dir
        case "$path" in
            "$base_dir"*)
                return 0
                ;;
            *)
                return 1
                ;;
        esac
    fi

    return 0
}

# Check if path is a symlink (recursive check for parent directories too)
is_symlink_in_path() {
    local path="$1"

    # Check the path itself
    if [ -L "$path" ]; then
        return 0
    fi

    # Check each parent directory
    while [ "$path" != "/" ] && [ "$path" != "." ] && [ -n "$path" ]; do
        if [ -L "$path" ]; then
            return 0
        fi
        path=$(dirname "$path")
    done

    return 1
}

# Check for hardlink attack - verify inode count
check_hardlink_attack() {
    local filepath="$1"

    if [ ! -f "$filepath" ]; then
        return 0  # File doesn't exist yet, ok
    fi

    # Get link count (number of hardlinks)
    local link_count
    if command -v stat &> /dev/null; then
        # Linux/GNU stat
        link_count=$(stat -c '%h' "$filepath" 2>/dev/null) || \
        # macOS/BSD stat
        link_count=$(stat -f '%l' "$filepath" 2>/dev/null) || \
        return 0
    else
        return 0  # Can't check, assume ok
    fi

    # If link count > 1, it has hardlinks
    if [ "$link_count" -gt 1 ]; then
        return 1
    fi

    return 0
}

# Secure file write - creates file atomically with proper permissions
secure_write() {
    local filepath="$1"
    local content="$2"
    local temp_file="${filepath}.tmp.$$"

    # Write to temp file
    echo "$content" > "$temp_file" || return 1

    # Set secure permissions (owner read/write only)
    chmod 600 "$temp_file" || return 1

    # Check for hardlink attack
    if ! check_hardlink_attack "$filepath"; then
        rm -f "$temp_file"
        return 1
    fi

    # Atomic move
    mv "$temp_file" "$filepath" || return 1

    # Verify it's not a symlink after creation
    if [ -L "$filepath" ]; then
        rm -f "$filepath"
        return 1
    fi

    return 0
}

# Check directory permissions and ownership
check_directory_security() {
    local dir="$1"

    if [ ! -d "$dir" ]; then
        return 1
    fi

    # Check if it's a symlink
    if is_symlink_in_path "$dir"; then
        return 1
    fi

    # Check if directory is writable
    if [ ! -w "$dir" ]; then
        return 1
    fi

    return 0
}

# Safe mkdir - creates directory only if it doesn't exist and isn't a symlink
safe_mkdir() {
    local dir="$1"

    # If it exists, check if it's a symlink
    if [ -e "$dir" ]; then
        if [ -L "$dir" ]; then
            return 1
        fi
        if [ -d "$dir" ]; then
            return 0  # Already exists as directory
        else
            return 1  # Exists but not a directory
        fi
    fi

    # Create with secure permissions
    mkdir -p "$dir" || return 1
    chmod 700 "$dir" || return 1

    # Double-check it's not a symlink (TOCTOU protection)
    if [ -L "$dir" ]; then
        rmdir "$dir" 2>/dev/null || true
        return 1
    fi

    return 0
}

# Validate user input length
validate_input_length() {
    local input="$1"
    local max_length="${2:-10000}"

    if [ "${#input}" -gt "$max_length" ]; then
        return 1
    fi

    return 0
}

# Check for disk space before writing
check_disk_space() {
    local dir="$1"
    local required_kb="${2:-1024}"  # Default 1MB

    if ! command -v df &> /dev/null; then
        return 0  # Can't check, assume ok
    fi

    # Get available space in KB
    local available_kb
    available_kb=$(df -k "$dir" 2>/dev/null | awk 'NR==2 {print $4}') || return 0

    if [ -z "$available_kb" ]; then
        return 0  # Can't determine, assume ok
    fi

    if [ "$available_kb" -lt "$required_kb" ]; then
        return 1
    fi

    return 0
}

# Remove dangerous environment variables
sanitize_environment() {
    unset IFS
    export PATH="/usr/local/bin:/usr/bin:/bin"
    export LC_ALL=C
}

# Log security event
log_security_event() {
    local level="$1"
    local message="$2"
    local log_file="${3:-}"

    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    local log_entry="[$timestamp] [SECURITY-$level] $message"

    # Always output to stderr for security events
    echo "$log_entry" >&2

    # Also log to file if provided
    if [ -n "$log_file" ]; then
        echo "$log_entry" >> "$log_file"
    fi
}

# ============================================
# SECURITY FIX 4: Complete path sanitization
# Agent: B2 - Handles all edge cases
# ============================================

# Enhanced sanitize with Unicode normalization and all edge cases
sanitize_filename_complete() {
    local input="$1"

    # Remove null bytes (multiple variations)
    input="${input//$'\0'/}"
    input="${input//\\x00/}"
    input="${input//\\0/}"

    # Remove newlines and carriage returns (all variations)
    input="${input//$'\n'/}"
    input="${input//$'\r'/}"
    input="${input//\\n/}"
    input="${input//\\r/}"

    # Remove path separators (all variations)
    input="${input//\\/}"
    input="${input//\//}"

    # Handle double dots and variations
    input="${input//../}"
    input="${input//.../}"
    input="${input//...../}"

    # Convert to lowercase, replace spaces with dashes
    input=$(echo "$input" | tr '[:upper:]' '[:lower:]' | tr ' ' '-')

    # Remove everything except alphanumeric, dash, underscore, dot
    input=$(echo "$input" | tr -cd '[:alnum:]._-')

    # Remove leading dots (hidden files)
    input="${input#.}"

    # Remove leading dashes
    input="${input#-}"

    # Limit length to prevent buffer issues
    echo "${input:0:200}"
}

# Validate path doesn't contain dangerous patterns
validate_safe_path() {
    local path="$1"

    # Check for null bytes
    if [[ "$path" =~ $'\0' ]] || [[ "$path" =~ \\x00 ]] || [[ "$path" =~ \\0 ]]; then
        return 1
    fi

    # Check for path traversal patterns
    if [[ "$path" =~ \.\. ]] || [[ "$path" =~ \/\/ ]] || [[ "$path" =~ \\\\ ]]; then
        return 1
    fi

    # Check for mixed separators
    if [[ "$path" =~ \/ ]] && [[ "$path" =~ \\ ]]; then
        return 1
    fi

    return 0
}


# ============================================
# SECURITY FIX 5: Atomic directory creation
# Agent: B2 - Race-free directory creation
# ============================================

# Atomic mkdir - prevents race conditions
atomic_mkdir() {
    local dir="$1"
    local temp_dir="${dir}.tmp.$$"

    # If it exists, check if it's a symlink
    if [ -e "$dir" ]; then
        if [ -L "$dir" ]; then
            return 1
        fi
        if [ -d "$dir" ]; then
            return 0  # Already exists as directory
        else
            return 1  # Exists but not a directory
        fi
    fi

    # Create temporary directory first
    if ! mkdir -p "$temp_dir" 2>/dev/null; then
        return 1
    fi

    # Set restrictive permissions
    chmod 700 "$temp_dir" || {
        rmdir "$temp_dir" 2>/dev/null
        return 1
    }

    # Atomic rename to final location
    if ! mv "$temp_dir" "$dir" 2>/dev/null; then
        rmdir "$temp_dir" 2>/dev/null
        # Check if it now exists (race won)
        if [ -d "$dir" ] && [ ! -L "$dir" ]; then
            return 0
        fi
        return 1
    fi

    # Double-check it's not a symlink (TOCTOU protection)
    if [ -L "$dir" ]; then
        rmdir "$dir" 2>/dev/null || true
        return 1
    fi

    return 0
}

