#!/bin/bash
# Heuristic Auto-Suggestion Script
# Purpose: Automatically suggest heuristics from failure patterns
#
# Features:
# - Analyze failure patterns and suggest heuristics
# - Extract common themes from multiple failures
# - Suggest heuristic text based on failure context
# - Auto-generate heuristic drafts for review

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$(dirname "$SCRIPT_DIR")"
MEMORY_DIR="$BASE_DIR/memory"
DB_PATH="$MEMORY_DIR/index.db"
LOGS_DIR="$BASE_DIR/logs"
SUGGESTIONS_DIR="$BASE_DIR/heuristic-suggestions"

# Output formatting
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
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

suggest() {
    echo -e "  ${MAGENTA}→${NC} $*"
}

# Create suggestions directory
mkdir -p "$SUGGESTIONS_DIR"

# Analyze failures by domain
analyze_failures_by_domain() {
    header "Analyzing Failures by Domain"

    local min_failures="${1:-3}"  # Minimum failures to suggest heuristic

    # Get domains with multiple failures
    local domains=$(sqlite3 "$DB_PATH" "
        SELECT domain, COUNT(*) as cnt
        FROM learnings
        WHERE type='failure'
        GROUP BY domain
        HAVING cnt >= $min_failures
        ORDER BY cnt DESC
    ")

    if [ -z "$domains" ]; then
        info "No domains with $min_failures+ failures found"
        return
    fi

    echo "$domains" | while IFS='|' read -r domain count; do
        info "Domain: $domain ($count failures)"

        # Get all failure titles in this domain
        local titles=$(sqlite3 "$DB_PATH" "
            SELECT title FROM learnings
            WHERE domain='$domain' AND type='failure'
        ")

        # Extract common words (simple approach)
        local common_theme=$(echo "$titles" | tr ' ' '\n' | tr '[:upper:]' '[:lower:]' | \
            grep -v "^$" | sort | uniq -c | sort -rn | head -3 | awk '{print $2}' | tr '\n' ' ')

        if [ -n "$common_theme" ]; then
            suggest "Common themes: $common_theme"
            suggest "Consider creating a heuristic for domain '$domain'"
        fi
    done
}

# Suggest heuristic from failure pattern
suggest_heuristic_from_pattern() {
    local domain="$1"

    header "Generating Heuristic Suggestion for: $domain"

    # Get failures in this domain
    local failures=$(sqlite3 "$DB_PATH" "
        SELECT id, title, summary, severity
        FROM learnings
        WHERE domain='$domain' AND type='failure'
        ORDER BY created_at DESC
        LIMIT 10
    ")

    if [ -z "$failures" ]; then
        warn "No failures found in domain '$domain'"
        return
    fi

    local failure_count=$(echo "$failures" | wc -l)
    info "Found $failure_count failures in domain '$domain'"

    # Calculate average severity
    local avg_severity=$(sqlite3 "$DB_PATH" "
        SELECT AVG(severity) FROM learnings
        WHERE domain='$domain' AND type='failure'
    " | xargs printf "%.1f" 2>/dev/null || echo "2.0")

    # Extract common patterns
    local common_words=$(echo "$failures" | cut -d'|' -f2 | tr ' ' '\n' | tr '[:upper:]' '[:lower:]' | \
        grep -v "^$" | grep -v "^the$\|^a$\|^an$\|^to$\|^in$\|^of$\|^and$" | \
        sort | uniq -c | sort -rn | head -5)

    # Generate heuristic suggestion
    local timestamp=$(date +%Y%m%d-%H%M%S)
    local suggestion_file="$SUGGESTIONS_DIR/${domain}-${timestamp}.md"

    cat > "$suggestion_file" <<EOF
# Heuristic Suggestion for Domain: $domain

**Generated:** $(date)
**Based on:** $failure_count failures
**Average Severity:** $avg_severity

## Suggested Heuristic

### Rule

When working with $domain:
- [Extract the common pattern from failures]
- [State the preventive action]

### Why

Based on $failure_count failures in this domain, a pattern emerges around:
$(echo "$common_words" | head -3 | awk '{print "- " $2}')

### Evidence

The following failures informed this heuristic:

EOF

    # Add failure examples
    echo "$failures" | head -5 | while IFS='|' read -r id title summary severity; do
        cat >> "$suggestion_file" <<EOF
- **Failure #$id** (Severity: $severity)
  - $title
EOF
    done

    cat >> "$suggestion_file" <<EOF

## Recommended Action

1. Review the failures above to identify the core pattern
2. Draft a clear, actionable rule
3. Add explanation of why this rule helps
4. If validated, add to heuristics: \`./scripts/record-heuristic.sh\`

## Proposed Heuristic Text

\`\`\`
Domain: $domain
Rule: [TODO: Extract pattern and state preventive action]
Explanation: [TODO: Explain why this helps based on failures]
Confidence: 0.5 (starting confidence)
\`\`\`

---

*This is an auto-generated suggestion. Human review and refinement required.*
EOF

    pass "Heuristic suggestion saved to: $suggestion_file"
    echo ""
    cat "$suggestion_file"
}

# Auto-suggest from recent failures
suggest_from_recent_failures() {
    header "Analyzing Recent Failures for Heuristic Opportunities"

    local days="${1:-7}"
    info "Looking at failures from last $days days"

    # Get recent failures grouped by domain
    local recent_by_domain=$(sqlite3 "$DB_PATH" "
        SELECT domain, COUNT(*) as cnt
        FROM learnings
        WHERE type='failure'
        AND created_at >= datetime('now', '-$days days')
        GROUP BY domain
        HAVING cnt >= 2
        ORDER BY cnt DESC
    ")

    if [ -z "$recent_by_domain" ]; then
        info "No recent failure patterns found"
        return
    fi

    echo "$recent_by_domain" | while IFS='|' read -r domain count; do
        if [ "$count" -ge 3 ]; then
            warn "Domain '$domain' has $count failures in $days days - HIGH PRIORITY"
            suggest "Strongly recommend creating a heuristic for this domain"
        else
            info "Domain '$domain' has $count failures in $days days"
        fi
    done

    # Get the highest priority domain
    local top_domain=$(echo "$recent_by_domain" | head -1 | cut -d'|' -f1)
    echo ""
    suggest "Top priority for heuristic creation: $top_domain"
    echo ""
    read -p "Generate detailed suggestion for '$top_domain'? (y/n) " -n 1 -r
    echo ""

    if [[ $REPLY =~ ^[Yy]$ ]]; then
        suggest_heuristic_from_pattern "$top_domain"
    fi
}

# Identify failures without corresponding heuristics
find_uncovered_failures() {
    header "Finding Failures Without Heuristic Coverage"

    # Get domains with failures but no heuristics
    local uncovered=$(sqlite3 "$DB_PATH" "
        SELECT l.domain, COUNT(DISTINCT l.id) as failure_count
        FROM learnings l
        LEFT JOIN heuristics h ON l.domain = h.domain
        WHERE l.type='failure' AND h.id IS NULL
        GROUP BY l.domain
        ORDER BY failure_count DESC
    ")

    if [ -z "$uncovered" ]; then
        pass "All failure domains have corresponding heuristics"
        return
    fi

    echo "$uncovered" | while IFS='|' read -r domain count; do
        warn "Domain '$domain' has $count failures but NO heuristics"
        suggest "Create heuristic coverage for this domain"
    done
}

# Suggest heuristic promotion based on validation
suggest_promotion() {
    header "Heuristic Promotion Candidates"

    # Find heuristics ready for promotion
    local candidates=$(sqlite3 "$DB_PATH" "
        SELECT domain, rule, times_validated, times_violated, confidence
        FROM heuristics
        WHERE is_golden = 0
        AND times_validated >= 3
        AND confidence >= 0.7
        AND (times_violated = 0 OR times_validated / CAST(times_violated AS REAL) > 5)
        ORDER BY confidence DESC, times_validated DESC
        LIMIT 10
    ")

    if [ -z "$candidates" ]; then
        info "No heuristics ready for promotion to golden rules"
        return
    fi

    echo "$candidates" | while IFS='|' read -r domain rule validated violated confidence; do
        pass "Candidate: $domain - '$rule'"
        info "  Validated: $validated, Violated: $violated, Confidence: $confidence"
        suggest "Consider promoting to golden rule"
    done
}

# Generate weekly heuristic report
generate_heuristic_report() {
    header "Generating Heuristic Opportunities Report"

    local report_file="$LOGS_DIR/heuristic-opportunities-$(date +%Y%m%d).txt"

    {
        echo "Emergent Learning Framework - Heuristic Opportunities Report"
        echo "Generated: $(date)"
        echo ""
        echo "========================================="
        echo "DOMAINS NEEDING HEURISTICS (3+ failures)"
        echo "========================================="
        echo ""

        sqlite3 "$DB_PATH" "
            SELECT domain, COUNT(*) as cnt
            FROM learnings
            WHERE type='failure'
            GROUP BY domain
            HAVING cnt >= 3
            ORDER BY cnt DESC
        " | while IFS='|' read -r domain count; do
            echo "Domain: $domain"
            echo "  Failures: $count"

            # Check if heuristics exist
            local heuristic_count=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM heuristics WHERE domain='$domain'")
            echo "  Existing heuristics: $heuristic_count"

            if [ "$heuristic_count" -eq 0 ]; then
                echo "  ★ HIGH PRIORITY: No heuristics for this domain"
            fi

            echo ""
        done

        echo "========================================="
        echo "RECENT FAILURE SPIKES (Last 7 Days)"
        echo "========================================="
        echo ""

        sqlite3 "$DB_PATH" "
            SELECT domain, COUNT(*) as cnt
            FROM learnings
            WHERE type='failure'
            AND created_at >= datetime('now', '-7 days')
            GROUP BY domain
            HAVING cnt >= 2
            ORDER BY cnt DESC
        " | while IFS='|' read -r domain count; do
            echo "  $domain: $count failures"
        done

        echo ""
        echo "========================================="
        echo "PROMOTION CANDIDATES"
        echo "========================================="
        echo ""

        sqlite3 "$DB_PATH" "
            SELECT domain, rule, times_validated, confidence
            FROM heuristics
            WHERE is_golden = 0
            AND times_validated >= 2
            AND confidence >= 0.6
            ORDER BY confidence DESC, times_validated DESC
            LIMIT 5
        " | while IFS='|' read -r domain rule validated confidence; do
            echo "Domain: $domain"
            echo "  Rule: $rule"
            echo "  Validated: $validated times, Confidence: $confidence"
            echo ""
        done

        echo "========================================="
        echo "RECOMMENDATIONS"
        echo "========================================="
        echo ""
        echo "1. Review high-priority domains and create initial heuristics"
        echo "2. Monitor recent failure spikes for emerging patterns"
        echo "3. Consider promoting validated heuristics to golden rules"
        echo "4. Use: ./scripts/suggest-heuristics.sh --generate <domain>"

    } > "$report_file"

    info "Report saved to: $report_file"
    echo ""
    cat "$report_file"
}

# Interactive mode to generate heuristic
interactive_generate() {
    header "Interactive Heuristic Generation"

    # List domains with failures
    local domains=$(sqlite3 "$DB_PATH" "
        SELECT domain, COUNT(*) as cnt
        FROM learnings
        WHERE type='failure'
        GROUP BY domain
        ORDER BY cnt DESC
        LIMIT 10
    ")

    echo "Domains with failures:"
    echo "$domains" | nl | while read -r num line; do
        echo "  $num) $line"
    done

    echo ""
    read -p "Select domain number (or type domain name): " selection

    local domain=""
    if [[ "$selection" =~ ^[0-9]+$ ]]; then
        domain=$(echo "$domains" | sed -n "${selection}p" | cut -d'|' -f1)
    else
        domain="$selection"
    fi

    if [ -z "$domain" ]; then
        fail "Invalid selection"
        return 1
    fi

    suggest_heuristic_from_pattern "$domain"
}

# Show statistics
show_statistics() {
    header "Heuristic Generation Statistics"

    local total_failures=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM learnings WHERE type='failure'")
    local total_heuristics=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM heuristics")
    local domains_with_failures=$(sqlite3 "$DB_PATH" "SELECT COUNT(DISTINCT domain) FROM learnings WHERE type='failure'")
    local domains_with_heuristics=$(sqlite3 "$DB_PATH" "SELECT COUNT(DISTINCT domain) FROM heuristics")

    printf "  %-40s %s\n" "Total failures:" "$total_failures"
    printf "  %-40s %s\n" "Total heuristics:" "$total_heuristics"
    printf "  %-40s %s\n" "Domains with failures:" "$domains_with_failures"
    printf "  %-40s %s\n" "Domains with heuristics:" "$domains_with_heuristics"

    local coverage_gap=$((domains_with_failures - domains_with_heuristics))
    printf "  %-40s %s\n" "Domains needing heuristics:" "$coverage_gap"

    if [ "$total_failures" -gt 0 ]; then
        local heuristic_ratio=$(echo "scale=2; $total_heuristics / $total_failures" | bc 2>/dev/null || echo "0")
        printf "  %-40s %s\n" "Heuristics per failure:" "$heuristic_ratio"
    fi

    # Show suggestion files
    local suggestion_count=$(find "$SUGGESTIONS_DIR" -name "*.md" 2>/dev/null | wc -l)
    printf "  %-40s %s\n" "Auto-generated suggestions:" "$suggestion_count"
}

# Main execution
main() {
    echo -e "${BOLD}Emergent Learning Framework - Heuristic Auto-Suggestion${NC}"
    echo -e "Started: $(date)\n"

    case "${1}" in
        --analyze)
            analyze_failures_by_domain "${2:-3}"
            ;;
        --recent)
            suggest_from_recent_failures "${2:-7}"
            ;;
        --generate)
            if [ -z "$2" ]; then
                interactive_generate
            else
                suggest_heuristic_from_pattern "$2"
            fi
            ;;
        --uncovered)
            find_uncovered_failures
            ;;
        --promote)
            suggest_promotion
            ;;
        --report)
            generate_heuristic_report
            ;;
        --stats)
            show_statistics
            ;;
        --help|-h)
            cat <<EOF
Usage: $0 [COMMAND] [OPTIONS]

Commands:
  --analyze [N]       Analyze domains with N+ failures (default: 3)
  --recent [DAYS]     Suggest from recent failures (default: 7 days)
  --generate [DOMAIN] Generate heuristic for domain (interactive if no domain)
  --uncovered         Find failures without heuristic coverage
  --promote           Show heuristics ready for promotion
  --report            Generate comprehensive opportunities report
  --stats             Show heuristic generation statistics
  --help              Show this help message

Examples:
  $0 --analyze 5              # Analyze domains with 5+ failures
  $0 --recent 14              # Check failures from last 14 days
  $0 --generate coordination  # Generate heuristic for coordination domain
  $0 --report                 # Generate full report
EOF
            ;;
        *)
            # Default: run comprehensive analysis
            show_statistics
            analyze_failures_by_domain 3
            find_uncovered_failures
            suggest_from_recent_failures 7
            suggest_promotion
            ;;
    esac

    echo -e "\n${GREEN}Heuristic suggestion completed${NC}"
}

main "$@"
