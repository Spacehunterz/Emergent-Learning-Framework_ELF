#!/bin/bash
# Demonstration of full observability features
#
# Shows:
# - Structured logging with correlation IDs
# - Metrics collection
# - Alert generation
# - Dashboard display

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$(dirname "$SCRIPT_DIR")"
LOGS_DIR="$BASE_DIR/logs"
DB_PATH="$BASE_DIR/memory/index.db"

# Source libraries
source "$SCRIPT_DIR/lib/logging.sh"
source "$SCRIPT_DIR/lib/metrics.sh"
source "$SCRIPT_DIR/lib/alerts.sh"

# Initialize with custom settings
export LOG_LEVEL=DEBUG
export LOG_FORMAT=text

log_init "observability-demo"
metrics_init "$DB_PATH"
alerts_init "$BASE_DIR"

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║     Emergent Learning Framework - Observability Demo        ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# Get correlation ID for this demo
CORRELATION_ID=$(log_get_correlation_id)
echo "Demo Correlation ID: $CORRELATION_ID"
echo ""

# 1. STRUCTURED LOGGING DEMO
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "1. Structured Logging Demo"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Writing structured log entries..."

log_debug "Debug message with context" operation="demo" step="1" correlation_id="$CORRELATION_ID"
log_info "Info message with tags" user="$(whoami)" action="demo" correlation_id="$CORRELATION_ID"
log_warn "Warning message" severity="low" correlation_id="$CORRELATION_ID"
log_error "Error simulation (not a real error)" error_type="simulated" correlation_id="$CORRELATION_ID"

echo "✓ Log entries written to: $LOGS_DIR/$(date +%Y%m%d).log"
echo ""
sleep 1

# 2. PERFORMANCE TIMING DEMO
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "2. Performance Timing Demo"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

log_timer_start "demo_operation"
echo "Simulating operation (500ms)..."
sleep 0.5
log_timer_stop "demo_operation" status="success" correlation_id="$CORRELATION_ID"

log_timer_start "demo_query"
echo "Simulating database query (200ms)..."
sleep 0.2
log_timer_stop "demo_query" status="success" query_type="SELECT" correlation_id="$CORRELATION_ID"

echo "✓ Performance timing logged"
echo ""
sleep 1

# 3. METRICS COLLECTION DEMO
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "3. Metrics Collection Demo"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

echo "Recording custom metrics..."
metrics_record "demo_counter" 1 type="demo" action="started"
metrics_record "demo_gauge" 42.5 type="demo" metric_type="gauge"
metrics_record "demo_latency_ms" 123.45 operation="demo" status="success"

echo "Recording operation metrics..."
op_start=$(metrics_operation_start "demo_api_call")
sleep 0.3
metrics_operation_end "demo_api_call" "$op_start" "success" endpoint="/demo"

echo "✓ Metrics recorded to database"
echo ""

# Show recent metrics
echo "Recent metrics:"
metrics_query recent "demo_%" 5
echo ""
sleep 1

# 4. ALERT SYSTEM DEMO
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "4. Alert System Demo"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

echo "Triggering test alerts..."
alert_trigger "info" "Demo info alert" correlation_id="$CORRELATION_ID"
alert_trigger "warning" "Demo warning - resource usage high" cpu="75%" correlation_id="$CORRELATION_ID"
alert_trigger "critical" "Demo critical alert - testing escalation" test="true" correlation_id="$CORRELATION_ID"

echo ""
echo "✓ Alerts triggered (check $BASE_DIR/alerts/)"
echo ""
sleep 1

# 5. CORRELATION TRACKING DEMO
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "5. End-to-End Trace Correlation Demo"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

echo "Simulating multi-step operation with correlation tracking..."
log_info "Step 1: Validate input" correlation_id="$CORRELATION_ID" step="validate"
sleep 0.1
log_info "Step 2: Process data" correlation_id="$CORRELATION_ID" step="process"
sleep 0.1
log_info "Step 3: Store results" correlation_id="$CORRELATION_ID" step="store"
sleep 0.1
log_info "Step 4: Complete" correlation_id="$CORRELATION_ID" step="complete"

echo "✓ All steps logged with correlation ID: $CORRELATION_ID"
echo ""

# Search logs for this correlation ID
echo "Searching logs for correlation ID..."
corr_count=$(grep -c "correlation_id=\"$CORRELATION_ID\"" "$LOGS_DIR/"*.log 2>/dev/null || echo "0")
echo "Found $corr_count log entries with correlation ID: $CORRELATION_ID"
echo ""
sleep 1

# 6. HEALTH CHECKS DEMO
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "6. Health Checks Demo"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

echo "Running system health checks..."
alert_health_check
echo ""

# 7. SUMMARY
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "7. Summary & Next Steps"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

echo "Demo complete! You now have full observability:"
echo ""
echo "  📊 View Dashboard:"
echo "     $SCRIPT_DIR/dashboard.sh"
echo ""
echo "  📝 View Logs:"
echo "     tail -f $LOGS_DIR/$(date +%Y%m%d).log"
echo ""
echo "  🔍 Search by Correlation ID:"
echo "     grep 'correlation_id=\"$CORRELATION_ID\"' $LOGS_DIR/*.log"
echo ""
echo "  📈 Query Metrics:"
echo "     sqlite3 $DB_PATH \"SELECT * FROM metrics ORDER BY timestamp DESC LIMIT 10\""
echo ""
echo "  🚨 List Alerts:"
echo "     ls -lh $BASE_DIR/alerts/"
echo ""
echo "  🗑️  Rotate Logs:"
echo "     $SCRIPT_DIR/rotate-logs.sh"
echo ""

log_info "Demo completed successfully" correlation_id="$CORRELATION_ID"
