#!/bin/bash
# Lock Monitoring Dashboard - Agent E2

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$SCRIPT_DIR"
STATS_FILE="${BASE_DIR}/.lock-stats"

# Initialize stats file
init_stats() {
    if [ ! -f "$STATS_FILE" ]; then
        echo "timestamp,lock_type,operation,attempts,wait_time,status" > "$STATS_FILE"
    fi
}

# Get current lock state
get_lock_state() {
    echo "=== Current Lock State ==="
    echo ""
    
    # Check for active locks
    echo "Active Locks:"
    local lock_count=0
    
    # Check git locks
    for lock in "$BASE_DIR"/.git/*.dir; do
        if [ -d "$lock" ]; then
            ((lock_count++))
            local lock_age=$(( $(date +%s) - $(stat -c %Y "$lock" 2>/dev/null || stat -f %m "$lock" 2>/dev/null || echo $(date +%s)) ))
            local pid_file="$lock/pid"
            local owner_pid="unknown"
            
            if [ -f "$pid_file" ]; then
                owner_pid=$(cat "$pid_file")
                if ps -p "$owner_pid" >/dev/null 2>&1; then
                    echo "  $(basename "$lock"): PID $owner_pid (age: ${lock_age}s) [ACTIVE]"
                else
                    echo "  $(basename "$lock"): PID $owner_pid (age: ${lock_age}s) [STALE - process dead]"
                fi
            else
                echo "  $(basename "$lock"): no PID (age: ${lock_age}s) [UNKNOWN]"
            fi
        fi
    done
    
    if [ $lock_count -eq 0 ]; then
        echo "  No active locks"
    fi
    
    echo ""
}

# Get statistics
get_stats() {
    init_stats
    
    if [ ! -f "$STATS_FILE" ] || [ $(wc -l < "$STATS_FILE") -le 1 ]; then
        echo "No statistics available yet"
        return
    fi
    
    echo "=== Lock Statistics ==="
    echo ""
    
    # Total operations
    echo "Total Operations:"
    awk -F, 'NR>1 {count[$3]++} END {for (op in count) printf "  %s: %d\n", op, count[op]}' "$STATS_FILE"
    echo ""
    
    # Success rate by type
    echo "Success Rate by Lock Type:"
    awk -F, '
        NR>1 && $3=="acquire" {
            total[$2]++
            if ($6=="success") success[$2]++
        }
        END {
            for (type in total) {
                rate = (success[type] ? success[type] : 0) / total[type] * 100
                printf "  %s: %.1f%% (%d/%d)\n", type, rate, (success[type] ? success[type] : 0), total[type]
            }
        }
    ' "$STATS_FILE"
    echo ""
    
    # Average wait times
    echo "Average Wait Times:"
    awk -F, '
        NR>1 && $3=="acquire" && $6=="success" {
            sum[$2]+=$5
            count[$2]++
        }
        END {
            for (type in count) {
                printf "  %s: %.3fs\n", type, sum[type]/count[type]
            }
        }
    ' "$STATS_FILE"
    echo ""
    
    # Contention (attempts > 1)
    echo "Lock Contention (multi-attempt acquisitions):"
    awk -F, '
        NR>1 && $3=="acquire" && $4>1 {
            count[$2]++
            max_attempts[$2] = ($4 > max_attempts[$2] ? $4 : max_attempts[$2])
        }
        END {
            for (type in count) {
                printf "  %s: %d instances (max attempts: %d)\n", type, count[type], max_attempts[type]
            }
        }
    ' "$STATS_FILE"
    echo ""
    
    # Timeouts
    echo "Timeouts:"
    local timeout_count=$(awk -F, 'NR>1 && $6=="timeout" {count++} END {print count+0}' "$STATS_FILE")
    echo "  Total: $timeout_count"
    if [ "$timeout_count" -gt 0 ]; then
        awk -F, 'NR>1 && $6=="timeout" {print "  " $1 " - " $2}' "$STATS_FILE" | tail -5
    fi
    echo ""
    
    # Stale lock cleanups
    echo "Stale Lock Cleanups:"
    local cleanup_count=$(awk -F, 'NR>1 && $3=="stale_cleanup" {count++} END {print count+0}' "$STATS_FILE")
    echo "  Total: $cleanup_count"
    if [ "$cleanup_count" -gt 0 ]; then
        echo "  Recent cleanups:"
        awk -F, 'NR>1 && $3=="stale_cleanup" {print "    " $1}' "$STATS_FILE" | tail -3
    fi
    echo ""
}

# Watch mode
watch_mode() {
    while true; do
        clear
        echo "======================================"
        echo "  LOCK MONITORING DASHBOARD"
        echo "  $(date '+%Y-%m-%d %H:%M:%S')"
        echo "======================================"
        echo ""
        
        get_lock_state
        get_stats
        
        echo "======================================"
        echo "Press Ctrl+C to exit"
        echo "Refreshing in 2 seconds..."
        
        sleep 2
    done
}

# Main
case "${1:-summary}" in
    watch)
        watch_mode
        ;;
    state)
        get_lock_state
        ;;
    stats)
        get_stats
        ;;
    summary|*)
        get_lock_state
        get_stats
        ;;
esac
