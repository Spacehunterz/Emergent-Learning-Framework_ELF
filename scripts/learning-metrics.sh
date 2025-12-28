#!/bin/bash
# Learning Metrics Script for Emergent Learning Framework
# Purpose: Track learning velocity and system efficiency over time
#
# Metrics tracked:
# - Learnings per day/week/month
# - Domain activity distribution
# - Heuristic promotion rate
# - Success/failure ratio
# - Learning acceleration trends

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$(dirname "$SCRIPT_DIR")"
MEMORY_DIR="$BASE_DIR/memory"
DB_PATH="$MEMORY_DIR/index.db"
LOGS_DIR="$BASE_DIR/logs"

# Create logs directory if it doesn't exist
mkdir -p "$LOGS_DIR"

# Output formatting
BOLD='\033[1m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

header() {
    echo -e "\n${BOLD}${BLUE}=== $* ===${NC}"
}

metric() {
    local label="$1"
    local value="$2"
    printf "  %-40s %s\n" "$label:" "$value"
}

# Check if database exists
if [ ! -f "$DB_PATH" ]; then
    echo "Error: Database not found at $DB_PATH"
    exit 1
fi

# Parse command line arguments
DETAILED=false
JSON_OUTPUT=false
TIME_RANGE="all"

while [[ $# -gt 0 ]]; do
    case $1 in
        --detailed|-d)
            DETAILED=true
            shift
            ;;
        --json|-j)
            JSON_OUTPUT=true
            shift
            ;;
        --range|-r)
            TIME_RANGE="$2"
            shift 2
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --detailed, -d     Show detailed metrics"
            echo "  --json, -j         Output in JSON format"
            echo "  --range, -r DAYS   Time range (7, 30, 90, all)"
            echo "  --help, -h         Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Calculate metrics
calculate_metrics() {
    # Total counts
    local total_learnings=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM learnings")
    local total_failures=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM learnings WHERE type='failure'")
    local total_successes=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM learnings WHERE type='success'")
    local total_heuristics=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM heuristics")
    local golden_heuristics=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM heuristics WHERE is_golden = 1")

    # Time-based calculations
    local learnings_today=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM learnings WHERE date(created_at) = date('now')")
    local learnings_7d=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM learnings WHERE created_at >= datetime('now', '-7 days')")
    local learnings_30d=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM learnings WHERE created_at >= datetime('now', '-30 days')")

    # Calculate rates
    local success_rate=0
    if [ "$total_learnings" -gt 0 ]; then
        success_rate=$(echo "scale=2; $total_successes * 100 / $total_learnings" | bc 2>/dev/null || echo "0")
    fi

    local promotion_rate=0
    if [ "$total_heuristics" -gt 0 ]; then
        promotion_rate=$(echo "scale=2; $golden_heuristics * 100 / $total_heuristics" | bc 2>/dev/null || echo "0")
    fi

    local avg_per_day=0
    if [ "$learnings_7d" -gt 0 ]; then
        avg_per_day=$(echo "scale=2; $learnings_7d / 7" | bc 2>/dev/null || echo "0")
    fi

    # First and last learning dates
    local first_learning=$(sqlite3 "$DB_PATH" "SELECT date(created_at) FROM learnings ORDER BY created_at ASC LIMIT 1")
    local last_learning=$(sqlite3 "$DB_PATH" "SELECT date(created_at) FROM learnings ORDER BY created_at DESC LIMIT 1")

    # Calculate days active
    local days_active=1
    if [ -n "$first_learning" ] && [ -n "$last_learning" ]; then
        local first_epoch=$(date -d "$first_learning" +%s 2>/dev/null || echo "0")
        local last_epoch=$(date -d "$last_learning" +%s 2>/dev/null || echo "0")
        if [ "$first_epoch" -gt 0 ] && [ "$last_epoch" -gt 0 ]; then
            days_active=$(( (last_epoch - first_epoch) / 86400 + 1 ))
        fi
    fi

    # Calculate overall average
    local overall_avg=0
    if [ "$days_active" -gt 0 ] && [ "$total_learnings" -gt 0 ]; then
        overall_avg=$(echo "scale=2; $total_learnings / $days_active" | bc 2>/dev/null || echo "0")
    fi

    # Most active domain
    local most_active_domain=$(sqlite3 "$DB_PATH" "SELECT domain, COUNT(*) as cnt FROM learnings GROUP BY domain ORDER BY cnt DESC LIMIT 1" | cut -d'|' -f1)
    local most_active_count=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM learnings WHERE domain='$most_active_domain'")

    if [ "$JSON_OUTPUT" = true ]; then
        # JSON output
        cat << EOF
{
  "summary": {
    "total_learnings": $total_learnings,
    "total_failures": $total_failures,
    "total_successes": $total_successes,
    "total_heuristics": $total_heuristics,
    "golden_heuristics": $golden_heuristics
  },
  "time_metrics": {
    "learnings_today": $learnings_today,
    "learnings_7_days": $learnings_7d,
    "learnings_30_days": $learnings_30d,
    "avg_per_day_7d": $avg_per_day,
    "overall_avg_per_day": $overall_avg,
    "days_active": $days_active,
    "first_learning": "$first_learning",
    "last_learning": "$last_learning"
  },
  "rates": {
    "success_rate": $success_rate,
    "promotion_rate": $promotion_rate
  },
  "activity": {
    "most_active_domain": "$most_active_domain",
    "most_active_count": $most_active_count
  }
}
EOF
    else
        # Human-readable output
        header "Learning Velocity Metrics"
        echo -e "${BOLD}Generated: $(date)${NC}"

        header "Overall Statistics"
        metric "Total learnings" "$total_learnings"
        metric "Total failures" "$total_failures"
        metric "Total successes" "$total_successes"
        metric "Total heuristics" "$total_heuristics"
        metric "Golden heuristics" "$golden_heuristics"
        metric "Success rate" "${success_rate}%"
        metric "Heuristic promotion rate" "${promotion_rate}%"

        header "Time-Based Metrics"
        metric "Learnings today" "$learnings_today"
        metric "Learnings (last 7 days)" "$learnings_7d"
        metric "Learnings (last 30 days)" "$learnings_30d"
        metric "Average per day (7d)" "$avg_per_day"
        metric "Overall average per day" "$overall_avg"
        metric "Days active" "$days_active"
        metric "First learning" "$first_learning"
        metric "Last learning" "$last_learning"

        header "Domain Activity"
        metric "Most active domain" "$most_active_domain ($most_active_count learnings)"

        if [ "$DETAILED" = true ]; then
            header "Detailed Domain Breakdown"
            sqlite3 "$DB_PATH" "SELECT domain, COUNT(*) as cnt FROM learnings GROUP BY domain ORDER BY cnt DESC" | \
                while IFS='|' read -r domain count; do
                    printf "  %-30s %5d learnings\n" "$domain" "$count"
                done

            header "Learning Type Distribution"
            sqlite3 "$DB_PATH" "SELECT type, COUNT(*) as cnt FROM learnings GROUP BY type ORDER BY cnt DESC" | \
                while IFS='|' read -r type count; do
                    printf "  %-30s %5d\n" "$type" "$count"
                done

            header "Recent Trends (Last 7 Days)"
            sqlite3 "$DB_PATH" "SELECT date(created_at) as day, COUNT(*) as cnt FROM learnings WHERE created_at >= datetime('now', '-7 days') GROUP BY date(created_at) ORDER BY day DESC" | \
                while IFS='|' read -r day count; do
                    printf "  %-30s %5d learnings\n" "$day" "$count"
                done

            header "Top Heuristic Domains"
            sqlite3 "$DB_PATH" "SELECT domain, COUNT(*) as cnt FROM heuristics GROUP BY domain ORDER BY cnt DESC LIMIT 10" | \
                while IFS='|' read -r domain count; do
                    printf "  %-30s %5d heuristics\n" "$domain" "$count"
                done

            header "Heuristic Validation Status"
            local validated=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM heuristics WHERE times_validated > 0")
            local violated=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM heuristics WHERE times_violated > 0")
            local avg_confidence=$(sqlite3 "$DB_PATH" "SELECT AVG(confidence) FROM heuristics" | xargs printf "%.2f")
            metric "Heuristics with validations" "$validated"
            metric "Heuristics with violations" "$violated"
            metric "Average confidence" "$avg_confidence"

            header "Learning Acceleration"
            # Compare recent week to previous week
            local prev_week=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM learnings WHERE created_at >= datetime('now', '-14 days') AND created_at < datetime('now', '-7 days')")
            local this_week=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM learnings WHERE created_at >= datetime('now', '-7 days')")

            if [ "$prev_week" -gt 0 ]; then
                local acceleration=$(echo "scale=2; ($this_week - $prev_week) * 100 / $prev_week" | bc 2>/dev/null || echo "0")
                metric "Previous week" "$prev_week learnings"
                metric "This week" "$this_week learnings"
                if (( $(echo "$acceleration > 0" | bc -l 2>/dev/null || echo "0") )); then
                    metric "Acceleration" "${GREEN}+${acceleration}%${NC} (growing)"
                elif (( $(echo "$acceleration < 0" | bc -l 2>/dev/null || echo "0") )); then
                    metric "Acceleration" "${YELLOW}${acceleration}%${NC} (slowing)"
                else
                    metric "Acceleration" "0% (stable)"
                fi
            else
                metric "Previous week" "$prev_week learnings (insufficient data)"
            fi
        fi

        # Learning efficiency insights
        header "System Health Indicators"

        # Check if system is being used
        if [ "$learnings_7d" -eq 0 ]; then
            echo -e "  ${YELLOW}⚠ Warning: No learnings in the last 7 days${NC}"
        else
            echo -e "  ${GREEN}✓ System is actively being used${NC}"
        fi

        # Check success/failure ratio
        if (( $(echo "$success_rate < 10" | bc -l 2>/dev/null || echo "0") )); then
            echo -e "  ${YELLOW}⚠ Warning: Low success rate ($success_rate%)${NC}"
        fi

        # Check if heuristics are being promoted
        if [ "$total_heuristics" -gt 10 ] && [ "$golden_heuristics" -eq 0 ]; then
            echo -e "  ${YELLOW}⚠ Warning: No golden heuristics despite having $total_heuristics heuristics${NC}"
        fi

        # Check if learnings are increasing
        if [ "$learnings_7d" -gt "$prev_week" ]; then
            echo -e "  ${GREEN}✓ Learning velocity is increasing${NC}"
        fi

        echo ""
    fi
}

# Export metrics to log file
export_metrics_to_log() {
    local metrics_log="$LOGS_DIR/learning-metrics.log"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')

    # Append to log file
    {
        echo "=== Metrics Snapshot: $timestamp ==="
        calculate_metrics
        echo ""
    } >> "$metrics_log"

    echo -e "\n${GREEN}Metrics exported to: $metrics_log${NC}"
}

# Main execution
main() {
    calculate_metrics

    # Optionally export to log
    if [ "$DETAILED" = true ]; then
        export_metrics_to_log
    fi
}

main
