#!/bin/bash
# Backup Helper Functions - Cross-platform utilities

# Calculate size in MB without bc (works on Windows/macOS/Linux)
bytes_to_mb() {
    local bytes=$1
    if [[ "$bytes" =~ ^[0-9]+$ ]]; then
        # Use awk instead of bc for better compatibility
        echo "$bytes" | awk '{printf "%.2f", $1/1024/1024}'
    else
        echo "unknown"
    fi
}

# Get file size in bytes (cross-platform)
get_file_size() {
    local file=$1
    if [[ -f "$file" ]]; then
        # Try different stat commands for cross-platform support
        stat -f%z "$file" 2>/dev/null || stat -c%s "$file" 2>/dev/null || echo "0"
    else
        echo "0"
    fi
}

# Calculate days between dates (cross-platform)
days_between() {
    local date1=$1  # YYYYMMDD format
    local date2=${2:-$(date +%Y%m%d)}

    # Convert to seconds and calculate difference
    local sec1=$(date -d "$date1" +%s 2>/dev/null || date -j -f "%Y%m%d" "$date1" +%s 2>/dev/null || echo "0")
    local sec2=$(date -d "$date2" +%s 2>/dev/null || date -j -f "%Y%m%d" "$date2" +%s 2>/dev/null || echo "0")

    if [[ "$sec1" -eq 0 ]] || [[ "$sec2" -eq 0 ]]; then
        echo "0"
    else
        echo $(( (sec2 - sec1) / 86400 ))
    fi
}

# Format date for display (cross-platform)
format_date() {
    local timestamp=$1  # YYYYMMDD_HHMMSS format

    # Extract date part
    local date_part=${timestamp:0:8}

    # Try different date command formats
    date -d "$date_part" "+%Y-%m-%d %H:%M:%S" 2>/dev/null || \
    date -j -f "%Y%m%d_%H%M%S" "$timestamp" "+%Y-%m-%d %H:%M:%S" 2>/dev/null || \
    echo "unknown date"
}

# Count lines in file (safe for large files)
safe_line_count() {
    local file=$1
    if [[ -f "$file" ]]; then
        wc -l < "$file" 2>/dev/null | tr -d ' ' || echo "0"
    else
        echo "0"
    fi
}

# Check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Verify SQLite database integrity
verify_sqlite_db() {
    local db=$1

    if [[ ! -f "$db" ]]; then
        echo "ERROR: Database not found: $db"
        return 1
    fi

    if ! command_exists sqlite3; then
        echo "SKIP: sqlite3 not available"
        return 0
    fi

    if sqlite3 "$db" "PRAGMA integrity_check;" | grep -q "ok"; then
        echo "OK"
        return 0
    else
        echo "FAILED"
        return 1
    fi
}

# Export these functions
export -f bytes_to_mb
export -f get_file_size
export -f days_between
export -f format_date
export -f safe_line_count
export -f command_exists
export -f verify_sqlite_db
