#!/bin/bash
# Integrate structured logging and metrics into all main scripts
# This script patches record-failure.sh, record-heuristic.sh, start-experiment.sh, and sync-db-markdown.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=== Integrating Observability into Emergent Learning Scripts ==="
echo ""

# Function to add observability to a script
add_observability() {
    local script_file="$1"
    local script_name="$2"

    echo "Processing: $script_file"

    # Backup original
    cp "$script_file" "${script_file}.pre-observability"

    # Create temp file with observability integration
    local temp_file="${script_file}.tmp"

    # Read the script and inject observability after the initial setup
    awk -v script_name="$script_name" '
    BEGIN {
        setup_done = 0
        observability_added = 0
    }

    # Skip if already has observability
    /source.*lib\/logging\.sh/ {
        print "SKIP: Already has observability integration"
        exit 1
    }

    # Print header and initial setup
    { print }

    # After LOGS_DIR is set, add observability
    /^LOGS_DIR=/ && !observability_added {
        print ""
        print "# ========================================="
        print "# OBSERVABILITY INTEGRATION"
        print "# Source structured logging and metrics"
        print "# ========================================="
        print ""
        print "# Source observability libraries"
        print "source \"$SCRIPT_DIR/lib/logging.sh\""
        print "source \"$SCRIPT_DIR/lib/metrics.sh\""
        print ""
        print "# Initialize logging with correlation ID"
        print "log_init \"" script_name "\""
        print "metrics_init \"$DB_PATH\""
        print ""
        print "# Generate correlation ID for this execution"
        print "CORRELATION_ID=$(log_get_correlation_id)"
        print ""
        print "# Start overall operation timer"
        print "log_timer_start \"" script_name "_total\""
        print "operation_start=$(metrics_operation_start \"" script_name "\")"
        print ""
        print "log_info \"Script started\" user=\"$(whoami)\" correlation_id=\"$CORRELATION_ID\""
        print ""
        print "# ========================================="
        print ""
        observability_added = 1
    }

    # Replace simple log() calls with log_info/log_error
    /^log\(\)/ && !setup_done {
        print "# Legacy log function - replaced by structured logging"
        print "# Use log_info, log_error, log_warn, log_debug instead"
        setup_done = 1
        next
    }

    ' "$script_file" > "$temp_file"

    # Check if observability was added
    if [ $? -eq 1 ]; then
        echo "  SKIPPED: Already integrated"
        rm -f "$temp_file" "${script_file}.pre-observability"
        return 1
    fi

    # Now add completion logging at the end
    # Find the last meaningful line (not comments or empty) and add before it
    echo "" >> "$temp_file"
    echo "# Record completion metrics" >> "$temp_file"
    echo "log_timer_stop \"${script_name}_total\" status=\"success\"" >> "$temp_file"
    echo "metrics_operation_end \"$script_name\" \"\$operation_start\" \"success\" domain=\"\${domain:-unknown}\"" >> "$temp_file"
    echo "log_info \"Script completed successfully\" correlation_id=\"\$CORRELATION_ID\"" >> "$temp_file"

    # Replace original with enhanced version
    mv "$temp_file" "$script_file"
    chmod +x "$script_file"

    echo "  SUCCESS: Observability integrated"
    echo "  Backup: ${script_file}.pre-observability"
    return 0
}

# Process each main script
echo ""
echo "--- record-failure.sh ---"
if add_observability "$SCRIPT_DIR/record-failure.sh" "record-failure"; then
    echo ""
fi

echo "--- record-heuristic.sh ---"
if add_observability "$SCRIPT_DIR/record-heuristic.sh" "record-heuristic"; then
    echo ""
fi

echo "--- start-experiment.sh ---"
if add_observability "$SCRIPT_DIR/start-experiment.sh" "start-experiment"; then
    echo ""
fi

echo "--- sync-db-markdown.sh ---"
if add_observability "$SCRIPT_DIR/sync-db-markdown.sh" "sync-db-markdown"; then
    echo ""
fi

echo "=== Observability Integration Complete ==="
echo ""
echo "Next steps:"
echo "1. Test each script to ensure it still works"
echo "2. Update log() calls to use structured logging (log_info, log_error, etc.)"
echo "3. Add metrics_record() calls at key points"
echo "4. Run the dashboard to view metrics"
