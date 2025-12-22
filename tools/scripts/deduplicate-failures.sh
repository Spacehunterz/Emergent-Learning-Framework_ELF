#!/bin/bash
# Failure Deduplication and Similarity Detection Script
# Purpose: Detect duplicate and similar failures to improve learning efficiency
#
# Features:
# - Exact duplicate detection
# - Similarity scoring based on domain, title, tags
# - Suggest merging similar failures
# - Improve deduplication in record scripts

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$(dirname "$SCRIPT_DIR")"
MEMORY_DIR="$BASE_DIR/memory"
DB_PATH="$MEMORY_DIR/index.db"
LOGS_DIR="$BASE_DIR/logs"

# Output formatting
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m' # No Color

header() {
    echo -e "\n${BOLD}${BLUE}=== $* ===${NC}"
}

pass() {
    echo -e "  ${GREEN}✓${NC} $*"
}

fail() {
    echo -e "  ${RED}✗${NC} $*"
}

warn() {
    echo -e "  ${YELLOW}⚠${NC} $*"
}

info() {
    echo -e "  ${BLUE}ℹ${NC} $*"
}

# Find exact duplicates
find_exact_duplicates() {
    header "Exact Duplicate Detection"

    # Find duplicate titles
    local duplicates=$(sqlite3 "$DB_PATH" "
        SELECT title, COUNT(*) as cnt, GROUP_CONCAT(id) as ids
        FROM learnings
        GROUP BY title
        HAVING cnt > 1
        ORDER BY cnt DESC
    ")

    if [ -z "$duplicates" ]; then
        pass "No exact duplicate titles found"
        return 0
    fi

    local duplicate_count=0
    echo "$duplicates" | while IFS='|' read -r title count ids; do
        warn "Duplicate: '$title' ($count instances, IDs: $ids)"
        ((duplicate_count++))
    done

    # Find duplicate content (same domain + same day)
    local same_day_duplicates=$(sqlite3 "$DB_PATH" "
        SELECT domain, date(created_at) as day, COUNT(*) as cnt
        FROM learnings
        WHERE type = 'failure'
        GROUP BY domain, day
        HAVING cnt > 3
        ORDER BY cnt DESC
        LIMIT 10
    ")

    if [ -n "$same_day_duplicates" ]; then
        echo ""
        info "High-frequency failures (potential duplicates):"
        echo "$same_day_duplicates" | while IFS='|' read -r domain day count; do
            info "  $domain on $day: $count failures"
        done
    fi
}

# Calculate similarity score between two learnings
calculate_similarity() {
    local id1="$1"
    local id2="$2"

    # Get learning details
    local learning1=$(sqlite3 "$DB_PATH" "SELECT domain, title, tags FROM learnings WHERE id=$id1")
    local learning2=$(sqlite3 "$DB_PATH" "SELECT domain, title, tags FROM learnings WHERE id=$id2")

    IFS='|' read -r domain1 title1 tags1 <<< "$learning1"
    IFS='|' read -r domain2 title2 tags2 <<< "$learning2"

    local score=0

    # Same domain: +40 points
    if [ "$domain1" = "$domain2" ]; then
        score=$((score + 40))
    fi

    # Similar title (using simple word matching)
    local common_words=$(comm -12 <(echo "$title1" | tr ' ' '\n' | sort) <(echo "$title2" | tr ' ' '\n' | sort) | wc -l)
    local title1_words=$(echo "$title1" | wc -w)
    local title2_words=$(echo "$title2" | wc -w)
    local max_words=$((title1_words > title2_words ? title1_words : title2_words))

    if [ "$max_words" -gt 0 ]; then
        local title_similarity=$((common_words * 40 / max_words))
        score=$((score + title_similarity))
    fi

    # Common tags: +20 points
    if [ -n "$tags1" ] && [ -n "$tags2" ]; then
        local common_tags=$(comm -12 <(echo "$tags1" | tr ',' '\n' | sort) <(echo "$tags2" | tr ',' '\n' | sort) | wc -l)
        if [ "$common_tags" -gt 0 ]; then
            score=$((score + 20))
        fi
    fi

    echo "$score"
}

# Find similar failures
find_similar_failures() {
    header "Similarity Detection"

    local threshold="${1:-60}"  # Similarity threshold (0-100)
    info "Similarity threshold: $threshold%"

    # Get all failure IDs
    local failure_ids=$(sqlite3 "$DB_PATH" "SELECT id FROM learnings WHERE type='failure' ORDER BY id")

    local similar_pairs=()
    local pair_count=0

    # Compare each pair (this is O(n²) but okay for small datasets)
    while IFS= read -r id1; do
        while IFS= read -r id2; do
            if [ "$id1" -lt "$id2" ]; then
                local similarity=$(calculate_similarity "$id1" "$id2")

                if [ "$similarity" -ge "$threshold" ]; then
                    local learning1=$(sqlite3 "$DB_PATH" "SELECT title, domain FROM learnings WHERE id=$id1")
                    local learning2=$(sqlite3 "$DB_PATH" "SELECT title, domain FROM learnings WHERE id=$id2")

                    IFS='|' read -r title1 domain1 <<< "$learning1"
                    IFS='|' read -r title2 domain2 <<< "$learning2"

                    warn "Similar ($similarity%): [$id1] $title1 <-> [$id2] $title2"
                    ((pair_count++))
                fi
            fi
        done <<< "$failure_ids"
    done <<< "$failure_ids"

    if [ "$pair_count" -eq 0 ]; then
        pass "No similar failures found above threshold"
    else
        info "Found $pair_count similar failure pairs"
    fi
}

# Enhanced deduplication check before recording
check_before_record() {
    local title="$1"
    local domain="$2"

    header "Pre-Record Deduplication Check"

    # Check for exact title match
    local exact_match=$(sqlite3 "$DB_PATH" "SELECT id, created_at FROM learnings WHERE title='$title' LIMIT 1")

    if [ -n "$exact_match" ]; then
        IFS='|' read -r id created_at <<< "$exact_match"
        fail "Exact duplicate found: ID $id created at $created_at"
        return 1
    fi

    # Check for similar titles in same domain
    local similar=$(sqlite3 "$DB_PATH" "
        SELECT id, title, created_at
        FROM learnings
        WHERE domain='$domain'
        AND type='failure'
        ORDER BY created_at DESC
        LIMIT 5
    ")

    if [ -n "$similar" ]; then
        info "Recent failures in domain '$domain':"
        echo "$similar" | while IFS='|' read -r id recent_title created_at; do
            info "  [$id] $recent_title ($created_at)"
        done
    fi

    pass "No exact duplicates found"
    return 0
}

# Generate deduplication report
generate_deduplication_report() {
    header "Deduplication Report"

    local report_file="$LOGS_DIR/deduplication-report-$(date +%Y%m%d-%H%M%S).txt"

    {
        echo "Emergent Learning Framework - Deduplication Report"
        echo "Generated: $(date)"
        echo ""
        echo "=== Exact Duplicates ==="
        sqlite3 "$DB_PATH" "
            SELECT title, COUNT(*) as cnt, GROUP_CONCAT(id) as ids
            FROM learnings
            GROUP BY title
            HAVING cnt > 1
            ORDER BY cnt DESC
        " | while IFS='|' read -r title count ids; do
            echo "  $title: $count instances (IDs: $ids)"
        done

        echo ""
        echo "=== High-Frequency Failures ==="
        sqlite3 "$DB_PATH" "
            SELECT domain, date(created_at) as day, COUNT(*) as cnt
            FROM learnings
            WHERE type = 'failure'
            GROUP BY domain, day
            HAVING cnt > 2
            ORDER BY cnt DESC
            LIMIT 20
        " | while IFS='|' read -r domain day count; do
            echo "  $domain on $day: $count failures"
        done

        echo ""
        echo "=== Recommendations ==="
        echo "  1. Review duplicate titles - they may indicate repeated issues"
        echo "  2. High-frequency failures in same domain may need consolidation"
        echo "  3. Consider extracting heuristics from repeated failures"
        echo "  4. Update record scripts to check for recent similar failures"

    } > "$report_file"

    info "Report saved to: $report_file"
    pass "Deduplication report generated"
}

# Suggest heuristics from duplicate patterns
suggest_heuristics_from_duplicates() {
    header "Heuristic Suggestions from Duplicates"

    # Find domains with many failures
    local high_failure_domains=$(sqlite3 "$DB_PATH" "
        SELECT domain, COUNT(*) as cnt
        FROM learnings
        WHERE type='failure'
        GROUP BY domain
        HAVING cnt >= 3
        ORDER BY cnt DESC
        LIMIT 5
    ")

    if [ -z "$high_failure_domains" ]; then
        info "Not enough failures to suggest heuristics"
        return
    fi

    echo ""
    echo "$high_failure_domains" | while IFS='|' read -r domain count; do
        info "Domain '$domain' has $count failures - consider extracting a heuristic"

        # Get common themes in that domain
        local common_words=$(sqlite3 "$DB_PATH" "
            SELECT title FROM learnings
            WHERE domain='$domain' AND type='failure'
        " | tr ' ' '\n' | tr '[:upper:]' '[:lower:]' | sort | uniq -c | sort -rn | head -5)

        if [ -n "$common_words" ]; then
            info "  Common themes: $(echo "$common_words" | awk '{print $2}' | tr '\n' ', ' | sed 's/,$//')"
        fi
    done

    pass "Heuristic suggestions generated"
}

# Add deduplication function to record scripts
improve_record_scripts() {
    header "Improving Record Scripts"

    # Check if record-failure.sh has deduplication
    if grep -q "duplicate" "$SCRIPT_DIR/record-failure.sh" 2>/dev/null; then
        pass "record-failure.sh already has deduplication checks"
    else
        warn "record-failure.sh could benefit from deduplication checks"
        info "Consider adding a check for similar recent failures"
    fi

    # Suggest improvement
    cat > "$LOGS_DIR/deduplication-improvement-suggestion.txt" <<'EOF'
# Suggested Deduplication Function for record-failure.sh

check_for_duplicates() {
    local title="$1"
    local domain="$2"

    # Check for exact match
    local exact=$(sqlite3 "$DB_PATH" "SELECT id FROM learnings WHERE title='$title' LIMIT 1")
    if [ -n "$exact" ]; then
        echo "Warning: Exact duplicate found (ID: $exact)"
        read -p "Continue anyway? (y/n) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 0
        fi
    fi

    # Check for similar recent failures in same domain
    local recent=$(sqlite3 "$DB_PATH" "
        SELECT title FROM learnings
        WHERE domain='$domain'
        AND type='failure'
        AND created_at >= datetime('now', '-1 day')
        LIMIT 5
    ")

    if [ -n "$recent" ]; then
        echo "Recent failures in domain '$domain':"
        echo "$recent"
        echo "Consider if this is a duplicate or related issue"
    fi
}

# Call before creating the failure record
check_for_duplicates "$FAILURE_TITLE" "$FAILURE_DOMAIN"
EOF

    info "Deduplication improvement suggestions saved to logs/"
}

# Statistics
show_deduplication_stats() {
    header "Deduplication Statistics"

    local total_learnings=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM learnings")
    local unique_titles=$(sqlite3 "$DB_PATH" "SELECT COUNT(DISTINCT title) FROM learnings")
    local duplicate_titles=$((total_learnings - unique_titles))

    metric "Total learnings" "$total_learnings"
    metric "Unique titles" "$unique_titles"
    metric "Duplicate titles" "$duplicate_titles"

    if [ "$total_learnings" -gt 0 ]; then
        local uniqueness=$(echo "scale=2; $unique_titles * 100 / $total_learnings" | bc 2>/dev/null || echo "0")
        metric "Uniqueness rate" "$uniqueness%"
    fi

    # Failures by domain
    local domain_concentration=$(sqlite3 "$DB_PATH" "
        SELECT domain, COUNT(*) as cnt
        FROM learnings
        WHERE type='failure'
        GROUP BY domain
        ORDER BY cnt DESC
        LIMIT 1
    ")

    if [ -n "$domain_concentration" ]; then
        IFS='|' read -r top_domain top_count <<< "$domain_concentration"
        metric "Top failure domain" "$top_domain ($top_count failures)"
    fi

    pass "Statistics calculated"
}

metric() {
    local label="$1"
    local value="$2"
    printf "  %-30s %s\n" "$label:" "$value"
}

# Main execution
main() {
    echo -e "${BOLD}Emergent Learning Framework - Deduplication Analysis${NC}"
    echo -e "Started: $(date)\n"

    # Parse arguments
    local mode="${1:-all}"
    local threshold="${2:-60}"

    case "$mode" in
        --exact)
            find_exact_duplicates
            ;;
        --similar)
            find_similar_failures "$threshold"
            ;;
        --check)
            if [ -z "$2" ] || [ -z "$3" ]; then
                echo "Usage: $0 --check \"title\" \"domain\""
                exit 1
            fi
            check_before_record "$2" "$3"
            ;;
        --report)
            generate_deduplication_report
            ;;
        --suggest)
            suggest_heuristics_from_duplicates
            ;;
        --improve)
            improve_record_scripts
            ;;
        --stats)
            show_deduplication_stats
            ;;
        --all|*)
            find_exact_duplicates
            find_similar_failures "$threshold"
            suggest_heuristics_from_duplicates
            show_deduplication_stats
            generate_deduplication_report
            improve_record_scripts
            ;;
    esac

    echo -e "\n${GREEN}Deduplication analysis completed${NC}"
}

main "$@"
