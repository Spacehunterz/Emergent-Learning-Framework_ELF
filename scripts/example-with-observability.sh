#!/bin/bash
# Example script demonstrating observability integration
#
# This shows how to use the new logging and metrics libraries
# in the Emergent Learning Framework scripts

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$(dirname "$SCRIPT_DIR")"
MEMORY_DIR="$BASE_DIR/memory"
DB_PATH="$MEMORY_DIR/index.db"

# Source observability libraries
source "$SCRIPT_DIR/lib/logging.sh"
source "$SCRIPT_DIR/lib/metrics.sh"

# Initialize logging and metrics
log_init "example-script"
metrics_init "$DB_PATH"

# Log examples
log_info "Script started" user="$(whoami)"

# Start performance timer
log_timer_start "main_operation"
operation_start=$(metrics_operation_start "example_operation")

# Simulate some work
log_debug "Performing database operation" operation="insert"

sleep 1

# Example database operation with error handling
if sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM learnings;" > /dev/null 2>&1; then
    log_info "Database query successful" table="learnings"
    operation_status="success"
else
    log_error "Database query failed" table="learnings"
    operation_status="failure"
fi

# Stop timers and record metrics
log_timer_stop "main_operation" status="$operation_status"
metrics_operation_end "example_operation" "$operation_start" "$operation_status" domain="testing"

# Record custom metrics
db_size_bytes=$(stat -f%z "$DB_PATH" 2>/dev/null || stat -c%s "$DB_PATH" 2>/dev/null || echo "0")
db_size_mb=$((db_size_bytes / 1024 / 1024))

metrics_record "db_size_mb" "$db_size_mb"
metrics_record "custom_counter" 42 category="example" type="test"

log_info "Script completed successfully"

echo "Observability example completed!"
echo "Check logs at: $LOGS_DIR"
echo "View metrics: python $BASE_DIR/query/dashboard.py"
