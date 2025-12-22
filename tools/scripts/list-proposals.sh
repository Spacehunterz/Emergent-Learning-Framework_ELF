#!/bin/bash
# List pending proposals in the Emergent Learning Framework
#
# Usage: ./list-proposals.sh [--all | --approved | --rejected]
#
# Options:
#   (no args)    List pending proposals only
#   --all        List proposals from all directories
#   --approved   List approved proposals only
#   --rejected   List rejected proposals only
#   --verbose    Show full frontmatter and summary

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$(dirname "$SCRIPT_DIR")"
PROPOSALS_DIR="$BASE_DIR/proposals"
PENDING_DIR="$PROPOSALS_DIR/pending"
APPROVED_DIR="$PROPOSALS_DIR/approved"
REJECTED_DIR="$PROPOSALS_DIR/rejected"

# Color output helpers (cross-platform)
if [ -t 1 ]; then
    BOLD='\033[1m'
    GREEN='\033[32m'
    YELLOW='\033[33m'
    RED='\033[31m'
    BLUE='\033[34m'
    CYAN='\033[36m'
    RESET='\033[0m'
else
    BOLD=''
    GREEN=''
    YELLOW=''
    RED=''
    BLUE=''
    CYAN=''
    RESET=''
fi

# Parse frontmatter from a markdown file
# Returns key=value pairs
parse_frontmatter() {
    local file="$1"
    local in_frontmatter=false

    while IFS= read -r line || [ -n "$line" ]; do
        # Strip carriage return (Windows line endings)
        line="${line%$'\r'}"

        if [ "$line" = "---" ]; then
            if $in_frontmatter; then
                break
            else
                in_frontmatter=true
                continue
            fi
        fi

        if $in_frontmatter; then
            # Extract key: value pairs using simple string ops
            if [[ "$line" == *":"* ]]; then
                local key="${line%%:*}"
                local value="${line#*:}"
                # Trim whitespace
                key=$(echo "$key" | tr -d ' ')
                value=$(echo "$value" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
                echo "${key}=${value}"
            fi
        fi
    done < "$file"
}

# Extract title from markdown (first # heading)
extract_title() {
    local file="$1"
    grep -m 1 '^# ' "$file" 2>/dev/null | sed 's/^# //' || echo "Untitled"
}

# Extract summary section
extract_summary() {
    local file="$1"
    local in_summary=false
    local summary=""
    local line_count=0

    while IFS= read -r line; do
        if [[ "$line" =~ ^##[[:space:]]+[Ss]ummary ]]; then
            in_summary=true
            continue
        elif $in_summary && [[ "$line" =~ ^## ]]; then
            break
        elif $in_summary && [ -n "$line" ]; then
            summary="${summary}${line} "
            line_count=$((line_count + 1))
            if [ $line_count -ge 3 ]; then
                break
            fi
        fi
    done < "$file"

    # Truncate to 150 chars
    echo "${summary:0:150}"
}

# Display a single proposal
display_proposal() {
    local file="$1"
    local status="$2"
    local verbose="$3"
    local num="$4"

    local filename=$(basename "$file")
    local title=$(extract_title "$file")

    # Parse frontmatter
    local fm=$(parse_frontmatter "$file")
    local type=$(echo "$fm" | grep '^type=' | cut -d= -f2)
    [ -z "$type" ] && type="unknown"
    local domain=$(echo "$fm" | grep '^domain=' | cut -d= -f2)
    [ -z "$domain" ] && domain="-"
    local confidence=$(echo "$fm" | grep '^confidence=' | cut -d= -f2)
    [ -z "$confidence" ] && confidence="-"
    local severity=$(echo "$fm" | grep '^severity=' | cut -d= -f2)
    [ -z "$severity" ] && severity="-"
    local submitted_at=$(echo "$fm" | grep '^submitted_at=' | cut -d= -f2)
    [ -z "$submitted_at" ] && submitted_at="-"

    # Status color
    local status_color=""
    case "$status" in
        pending) status_color="$YELLOW" ;;
        approved) status_color="$GREEN" ;;
        rejected) status_color="$RED" ;;
    esac

    # Type color
    local type_color=""
    case "$type" in
        heuristic) type_color="$CYAN" ;;
        failure) type_color="$RED" ;;
        pattern) type_color="$BLUE" ;;
        contradiction) type_color="$YELLOW" ;;
    esac

    echo -e "${BOLD}[$num] ${status_color}[$status]${RESET} ${type_color}[$type]${RESET} $title"
    echo -e "    ${BLUE}File:${RESET} $filename"
    echo -e "    ${BLUE}Domain:${RESET} $domain"

    if [ "$type" = "heuristic" ] && [ "$confidence" != "-" ]; then
        echo -e "    ${BLUE}Confidence:${RESET} $confidence"
    fi

    if [ "$type" = "failure" ] && [ "$severity" != "-" ]; then
        echo -e "    ${BLUE}Severity:${RESET} $severity"
    fi

    if [ "$submitted_at" != "-" ]; then
        echo -e "    ${BLUE}Submitted:${RESET} $submitted_at"
    fi

    if [ "$verbose" = "true" ]; then
        local summary=$(extract_summary "$file")
        if [ -n "$summary" ]; then
            echo -e "    ${BLUE}Summary:${RESET} ${summary}..."
        fi
    fi

    echo ""
}

# List proposals in a directory
list_proposals_in_dir() {
    local dir="$1"
    local status="$2"
    local verbose="$3"

    # Check if directory exists
    if [ ! -d "$dir" ]; then
        return 0
    fi

    # Get files
    local count=0
    for file in "$dir"/*.md; do
        # Skip if no files match (glob returns literal pattern)
        [ -e "$file" ] || continue

        count=$((count + 1))
        display_proposal "$file" "$status" "$verbose" "$count"
    done

    echo "$count"
}

# Main function
main() {
    local show_pending=true
    local show_approved=false
    local show_rejected=false
    local verbose=false

    # Parse arguments
    while [ $# -gt 0 ]; do
        case "$1" in
            --all)
                show_pending=true
                show_approved=true
                show_rejected=true
                shift
                ;;
            --approved)
                show_pending=false
                show_approved=true
                shift
                ;;
            --rejected)
                show_pending=false
                show_rejected=true
                shift
                ;;
            --pending)
                show_pending=true
                shift
                ;;
            --verbose|-v)
                verbose=true
                shift
                ;;
            --help|-h)
                echo "Usage: $0 [--all | --approved | --rejected] [--verbose]"
                echo ""
                echo "Options:"
                echo "  (no args)    List pending proposals only"
                echo "  --all        List proposals from all directories"
                echo "  --approved   List approved proposals only"
                echo "  --rejected   List rejected proposals only"
                echo "  --verbose    Show summary for each proposal"
                exit 0
                ;;
            *)
                echo "Unknown option: $1"
                exit 1
                ;;
        esac
    done

    # Check if proposals directory exists
    if [ ! -d "$PROPOSALS_DIR" ]; then
        echo -e "${YELLOW}Proposals directory not found.${RESET}"
        echo "Run the init script or create: $PROPOSALS_DIR"
        exit 1
    fi

    echo -e "${BOLD}========================================${RESET}"
    echo -e "${BOLD}    ELF Proposal Review Queue${RESET}"
    echo -e "${BOLD}========================================${RESET}"
    echo ""

    local pending_count=0
    local approved_count=0
    local rejected_count=0

    # List pending proposals
    if [ "$show_pending" = "true" ]; then
        echo -e "${BOLD}${YELLOW}PENDING PROPOSALS${RESET}"
        echo -e "${YELLOW}------------------${RESET}"

        # Count files first
        pending_count=0
        for f in "$PENDING_DIR"/*.md; do
            [ -e "$f" ] && pending_count=$((pending_count + 1))
        done

        if [ "$pending_count" -eq 0 ]; then
            echo -e "  ${GREEN}No pending proposals${RESET}"
            echo ""
        else
            list_proposals_in_dir "$PENDING_DIR" "pending" "$verbose" > /dev/null
            # Display them (list_proposals_in_dir already outputs)
            local num=0
            for file in "$PENDING_DIR"/*.md; do
                [ -e "$file" ] || continue
                num=$((num + 1))
                display_proposal "$file" "pending" "$verbose" "$num"
            done
        fi
    fi

    # List approved proposals
    if [ "$show_approved" = "true" ]; then
        echo -e "${BOLD}${GREEN}APPROVED PROPOSALS${RESET}"
        echo -e "${GREEN}-------------------${RESET}"

        approved_count=0
        for f in "$APPROVED_DIR"/*.md; do
            [ -e "$f" ] && approved_count=$((approved_count + 1))
        done

        if [ "$approved_count" -eq 0 ]; then
            echo -e "  No approved proposals"
            echo ""
        else
            local num=0
            for file in "$APPROVED_DIR"/*.md; do
                [ -e "$file" ] || continue
                num=$((num + 1))
                display_proposal "$file" "approved" "$verbose" "$num"
            done
        fi
    fi

    # List rejected proposals
    if [ "$show_rejected" = "true" ]; then
        echo -e "${BOLD}${RED}REJECTED PROPOSALS${RESET}"
        echo -e "${RED}-------------------${RESET}"

        rejected_count=0
        for f in "$REJECTED_DIR"/*.md; do
            [ -e "$f" ] && rejected_count=$((rejected_count + 1))
        done

        if [ "$rejected_count" -eq 0 ]; then
            echo -e "  No rejected proposals"
            echo ""
        else
            local num=0
            for file in "$REJECTED_DIR"/*.md; do
                [ -e "$file" ] || continue
                num=$((num + 1))
                display_proposal "$file" "rejected" "$verbose" "$num"
            done
        fi
    fi

    # Summary
    echo -e "${BOLD}========================================${RESET}"
    echo -e "${BOLD}SUMMARY${RESET}"
    echo -e "  Pending:  ${YELLOW}$pending_count${RESET}"
    if [ "$show_approved" = "true" ]; then
        echo -e "  Approved: ${GREEN}$approved_count${RESET}"
    fi
    if [ "$show_rejected" = "true" ]; then
        echo -e "  Rejected: ${RED}$rejected_count${RESET}"
    fi
    echo -e "${BOLD}========================================${RESET}"

    # Quick action hint
    if [ "$pending_count" -gt 0 ]; then
        echo ""
        echo -e "${CYAN}To review a proposal:${RESET}"
        echo "  ./scripts/review-proposal.sh pending/<filename> approve [notes]"
        echo "  ./scripts/review-proposal.sh pending/<filename> reject [notes]"
    fi
}

main "$@"
