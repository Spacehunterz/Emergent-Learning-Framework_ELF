#!/bin/bash
# Review and approve/reject proposals in the Emergent Learning Framework
#
# Usage: ./review-proposal.sh <proposal_file> <approve|reject> [notes]
#
# Examples:
#   ./review-proposal.sh pending/2025-12-11_heuristic_always-validate.md approve "Great insight"
#   ./review-proposal.sh pending/2025-12-11_failure_timeout.md reject "Duplicate of existing failure"

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$(dirname "$SCRIPT_DIR")"
PROPOSALS_DIR="$BASE_DIR/proposals"
PENDING_DIR="$PROPOSALS_DIR/pending"
APPROVED_DIR="$PROPOSALS_DIR/approved"
REJECTED_DIR="$PROPOSALS_DIR/rejected"
LOGS_DIR="$BASE_DIR/logs"
INTEGRATE_SCRIPT="$SCRIPT_DIR/integrate-proposal.py"

# Setup logging
EXECUTION_DATE=$(date +%Y%m%d)
LOG_FILE="$LOGS_DIR/${EXECUTION_DATE}.log"
mkdir -p "$LOGS_DIR"

log() {
    local level="$1"
    shift
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [$level] [review-proposal] $*" >> "$LOG_FILE"
    if [ "$level" = "ERROR" ]; then
        echo "ERROR: $*" >&2
    fi
}

# Color output helpers (cross-platform)
print_success() {
    if [ -t 1 ]; then
        echo -e "\033[32m$1\033[0m"
    else
        echo "$1"
    fi
}

print_error() {
    if [ -t 1 ]; then
        echo -e "\033[31m$1\033[0m" >&2
    else
        echo "$1" >&2
    fi
}

print_info() {
    if [ -t 1 ]; then
        echo -e "\033[34m$1\033[0m"
    else
        echo "$1"
    fi
}

# Show usage
show_usage() {
    echo "Usage: $0 <proposal_file> <approve|reject> [notes]"
    echo ""
    echo "Arguments:"
    echo "  proposal_file  Path to proposal (relative to proposals/ or absolute)"
    echo "  action         'approve' or 'reject'"
    echo "  notes          Optional notes explaining the decision"
    echo ""
    echo "Examples:"
    echo "  $0 pending/2025-12-11_heuristic_validate.md approve"
    echo "  $0 pending/my-proposal.md reject \"Needs more evidence\""
    exit 1
}

# Pre-flight checks
preflight_check() {
    log "INFO" "Starting pre-flight checks"

    if [ ! -d "$PROPOSALS_DIR" ]; then
        log "ERROR" "Proposals directory not found: $PROPOSALS_DIR"
        print_error "Proposals directory not found. Run init first."
        exit 1
    fi

    mkdir -p "$PENDING_DIR" "$APPROVED_DIR" "$REJECTED_DIR"

    log "INFO" "Pre-flight checks passed"
}

# Validate proposal file
validate_proposal_file() {
    local filepath="$1"

    # If relative path, resolve from proposals dir
    if [[ ! "$filepath" = /* ]]; then
        filepath="$PROPOSALS_DIR/$filepath"
    fi

    # Security: Check for path traversal
    local real_path=$(realpath "$filepath" 2>/dev/null || echo "")
    local real_pending=$(realpath "$PENDING_DIR" 2>/dev/null || echo "")

    if [ -z "$real_path" ] || [ ! -f "$filepath" ]; then
        log "ERROR" "Proposal file not found: $filepath"
        print_error "Proposal file not found: $filepath"
        exit 1
    fi

    # Must be in pending directory
    if [[ ! "$real_path" == "$real_pending"/* ]]; then
        log "ERROR" "SECURITY: Proposal not in pending directory: $filepath"
        print_error "Proposal must be in pending/ directory"
        exit 1
    fi

    # Must be a markdown file
    if [[ ! "$filepath" == *.md ]]; then
        log "ERROR" "Proposal must be a markdown file: $filepath"
        print_error "Proposal must be a .md file"
        exit 1
    fi

    # Security: Check for symlinks
    if [ -L "$filepath" ]; then
        log "ERROR" "SECURITY: Proposal is a symlink: $filepath"
        print_error "Symlinks not allowed for proposals"
        exit 1
    fi

    echo "$filepath"
}

# Append review decision to proposal
append_review_decision() {
    local filepath="$1"
    local decision="$2"
    local notes="${3:-}"
    local reviewer="CEO"
    local review_date=$(date '+%Y-%m-%d %H:%M:%S')

    cat >> "$filepath" <<EOF

---

## Review Decision

**Status:** $decision
**Reviewed by:** $reviewer
**Reviewed at:** $review_date
**Notes:** $notes
EOF
}

# Move proposal to destination
move_proposal() {
    local filepath="$1"
    local dest_dir="$2"
    local filename=$(basename "$filepath")
    local dest_path="$dest_dir/$filename"

    # Handle duplicate filenames
    if [ -f "$dest_path" ]; then
        local base="${filename%.md}"
        local counter=1
        while [ -f "$dest_dir/${base}_${counter}.md" ]; do
            ((counter++))
        done
        dest_path="$dest_dir/${base}_${counter}.md"
    fi

    mv "$filepath" "$dest_path"
    echo "$dest_path"
}

# Main logic
main() {
    preflight_check

    # Parse arguments
    if [ $# -lt 2 ]; then
        show_usage
    fi

    local proposal_path="$1"
    local action=$(echo "$2" | tr '[:upper:]' '[:lower:]')
    local notes="${3:-No notes provided}"

    # Validate action
    if [ "$action" != "approve" ] && [ "$action" != "reject" ]; then
        print_error "Invalid action: $action (must be 'approve' or 'reject')"
        show_usage
    fi

    # Validate and get full path
    local filepath=$(validate_proposal_file "$proposal_path")
    local filename=$(basename "$filepath")

    log "INFO" "Reviewing proposal: $filename (action: $action)"
    print_info "Reviewing: $filename"

    # Append review decision
    if [ "$action" = "approve" ]; then
        append_review_decision "$filepath" "APPROVED" "$notes"
        local dest_path=$(move_proposal "$filepath" "$APPROVED_DIR")

        log "INFO" "Proposal approved and moved to: $dest_path"
        print_success "Proposal APPROVED"
        print_info "Moved to: $dest_path"

        # Trigger integration if script exists
        if [ -f "$INTEGRATE_SCRIPT" ]; then
            print_info "Running integration..."
            if python3 "$INTEGRATE_SCRIPT" "$dest_path" 2>&1; then
                print_success "Integration successful"
                log "INFO" "Integration completed for: $filename"
            else
                print_error "Integration failed - check logs"
                log "ERROR" "Integration failed for: $filename"
            fi
        else
            print_info "Note: integrate-proposal.py not found, skipping auto-integration"
            log "WARN" "Integration script not found"
        fi

    else
        append_review_decision "$filepath" "REJECTED" "$notes"
        local dest_path=$(move_proposal "$filepath" "$REJECTED_DIR")

        log "INFO" "Proposal rejected and moved to: $dest_path"
        print_success "Proposal REJECTED"
        print_info "Moved to: $dest_path"
    fi

    echo ""
    log "INFO" "Review completed: $action for $filename"
}

main "$@"
