#!/bin/bash
# Patch main scripts to add structured logging and correlation IDs
#
# This script adds observability imports and correlation tracking
# to the main framework scripts

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=== Patching Scripts for Full Observability ==="
echo ""

# Function to patch a script
patch_script() {
    local script_file="$1"
    local script_name=$(basename "$script_file" .sh)

    echo "Patching: $script_name"

    # Check if already patched
    if grep -q "CORRELATION_ID.*log_get_correlation_id" "$script_file" 2>/dev/null; then
        echo "  SKIP: Already patched"
        return 0
    fi

    # Backup
    cp "$script_file" "${script_file}.pre-observability-patch"

    # Insert after LOGS_DIR definition and log() function
    # Find line number of log() function or LOGS_DIR
    local insert_after=$(grep -n "^LOGS_DIR=" "$script_file" | head -1 | cut -d: -f1)

    if [ -z "$insert_after" ]; then
        echo "  ERROR: Could not find LOGS_DIR in $script_file"
        return 1
    fi

    # Calculate where to insert (after the simple log function, around line 35)
    insert_after=$((insert_after + 10))

    # Create patch content
    local patch_content="
# ========================================
# OBSERVABILITY INTEGRATION
# ========================================

# Source observability libraries
if [ -f \"\$SCRIPT_DIR/lib/logging.sh\" ]; then
    source \"\$SCRIPT_DIR/lib/logging.sh\"
    source \"\$SCRIPT_DIR/lib/metrics.sh\" 2>/dev/null || true
    source \"\$SCRIPT_DIR/lib/alerts.sh\" 2>/dev/null || true

    # Initialize observability
    log_init \"$script_name\" \"\$LOGS_DIR\"
    metrics_init \"\$DB_PATH\" 2>/dev/null || true
    alerts_init \"\$BASE_DIR\" 2>/dev/null || true

    # Generate correlation ID for this execution
    CORRELATION_ID=\$(log_get_correlation_id)
    export CORRELATION_ID

    log_info \"Script started\" user=\"\$(whoami)\" correlation_id=\"\$CORRELATION_ID\"

    # Start performance tracking
    log_timer_start \"${script_name}_total\"
    OPERATION_START=\$(metrics_operation_start \"$script_name\" 2>/dev/null || echo \"\")
else
    # Fallback if libraries not found
    CORRELATION_ID=\"\${script_name}_\$(date +%s)_\$\$\"
    OPERATION_START=\"\"
fi

# ========================================
"

    # Insert the patch
    {
        head -n "$insert_after" "$script_file"
        echo "$patch_content"
        tail -n +$((insert_after + 1)) "$script_file"
    } > "${script_file}.tmp"

    mv "${script_file}.tmp" "$script_file"
    chmod +x "$script_file"

    echo "  SUCCESS: Patched with correlation ID: correlation_id=\$CORRELATION_ID"
    echo "  Backup: ${script_file}.pre-observability-patch"
}

# Patch each main script
echo "1. record-failure.sh"
patch_script "$SCRIPT_DIR/record-failure.sh"
echo ""

echo "2. record-heuristic.sh"
patch_script "$SCRIPT_DIR/record-heuristic.sh"
echo ""

echo "3. start-experiment.sh"
patch_script "$SCRIPT_DIR/start-experiment.sh"
echo ""

echo "4. sync-db-markdown.sh"
if [ -f "$SCRIPT_DIR/sync-db-markdown.sh" ]; then
    patch_script "$SCRIPT_DIR/sync-db-markdown.sh"
else
    echo "  SKIP: File not found"
fi
echo ""

echo "=== Patching Complete ==="
echo ""
echo "All scripts now have:"
echo "  ✓ Structured logging integration"
echo "  ✓ Correlation ID tracking"
echo "  ✓ Performance metrics"
echo "  ✓ Alert capability"
echo ""
echo "Next: Replace log() calls with log_info(), log_error(), etc."
echo "      Add metrics_record() at key points"
echo "      Use alert_trigger() for critical events"
