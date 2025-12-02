#!/bin/bash
# Log rotation and cleanup for Emergent Learning Framework
#
# Compresses logs older than 7 days
# Deletes logs older than 90 days
# Tracks log storage usage
#
# Should be run daily via cron or scheduled task

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$(dirname "$SCRIPT_DIR")"
LOGS_DIR="$BASE_DIR/logs"
DB_PATH="$BASE_DIR/memory/index.db"

# Source libraries
source "$SCRIPT_DIR/lib/logging.sh"
source "$SCRIPT_DIR/lib/metrics.sh"

# Initialize
log_init "rotate-logs"
metrics_init "$DB_PATH"

log_info "Starting log rotation"

# Track log directory size before rotation
if [ -d "$LOGS_DIR" ]; then
    size_before=$(du -sm "$LOGS_DIR" 2>/dev/null | cut -f1 || echo "0")
    log_info "Log directory size before rotation" size_mb="$size_before"
else
    log_error "Logs directory not found" path="$LOGS_DIR"
    exit 1
fi

# Compress logs older than 7 days
log_info "Compressing logs older than 7 days"
compressed_count=0

find "$LOGS_DIR" -name "*.log" -type f -mtime +7 ! -name "*.gz" -print0 2>/dev/null | while IFS= read -r -d '' logfile; do
    log_debug "Compressing log file" file="$logfile"

    # Use gzip if available, otherwise skip compression
    if command -v gzip &> /dev/null; then
        if gzip -9 "$logfile" 2>/dev/null; then
            log_info "Compressed log file" file="$logfile"
            ((compressed_count++))
        else
            log_warn "Failed to compress log file" file="$logfile"
        fi
    else
        log_warn "gzip not available, skipping compression"
        break
    fi
done

log_info "Compression complete" compressed="$compressed_count"
metrics_record "logs_compressed_count" "$compressed_count"

# Delete logs older than 90 days
log_info "Deleting logs older than 90 days"
deleted_count=0

# Delete compressed logs older than 90 days
find "$LOGS_DIR" -name "*.log.gz" -type f -mtime +90 -print0 2>/dev/null | while IFS= read -r -d '' logfile; do
    log_debug "Deleting old log file" file="$logfile"
    if rm -f "$logfile" 2>/dev/null; then
        log_info "Deleted old log file" file="$logfile"
        ((deleted_count++))
    else
        log_warn "Failed to delete log file" file="$logfile"
    fi
done

# Delete uncompressed logs older than 90 days (shouldn't happen if rotation works)
find "$LOGS_DIR" -name "*.log" -type f -mtime +90 -print0 2>/dev/null | while IFS= read -r -d '' logfile; do
    log_warn "Found uncompressed log older than 90 days" file="$logfile"
    if rm -f "$logfile" 2>/dev/null; then
        log_info "Deleted old uncompressed log file" file="$logfile"
        ((deleted_count++))
    fi
done

log_info "Deletion complete" deleted="$deleted_count"
metrics_record "logs_deleted_count" "$deleted_count"

# Track log directory size after rotation
size_after=$(du -sm "$LOGS_DIR" 2>/dev/null | cut -f1 || echo "0")
size_saved=$((size_before - size_after))

log_info "Log directory size after rotation" size_mb="$size_after" saved_mb="$size_saved"
metrics_record "log_dir_size_mb" "$size_after"
metrics_record "log_space_saved_mb" "$size_saved"

# Count log files by type
log_file_count=$(find "$LOGS_DIR" -name "*.log" -type f 2>/dev/null | wc -l)
compressed_file_count=$(find "$LOGS_DIR" -name "*.log.gz" -type f 2>/dev/null | wc -l)
total_files=$((log_file_count + compressed_file_count))

log_info "Log file inventory" uncompressed="$log_file_count" compressed="$compressed_file_count" total="$total_files"

# Check if we're running low on space
if [ "$size_after" -gt 1000 ]; then
    log_warn "Log directory is large" size_mb="$size_after" threshold_mb="1000"
    if command -v "$SCRIPT_DIR/lib/alerts.sh" &> /dev/null; then
        source "$SCRIPT_DIR/lib/alerts.sh"
        alerts_init "$BASE_DIR"
        alert_trigger "warning" "Log directory size exceeded 1GB" size_mb="$size_after"
    fi
fi

log_info "Log rotation complete"

echo "Log rotation complete:"
echo "  Compressed: $compressed_count files"
echo "  Deleted: $deleted_count old files"
echo "  Space saved: ${size_saved} MB"
echo "  Current size: ${size_after} MB"
echo "  Total files: $total_files (${log_file_count} uncompressed, ${compressed_file_count} compressed)"
