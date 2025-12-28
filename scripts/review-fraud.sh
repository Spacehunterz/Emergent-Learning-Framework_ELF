#!/usr/bin/env bash
#
# Fraud Review CLI
# Interactive CLI for reviewing pending fraud reports
#
# Usage:
#   ./review-fraud.sh list                   # List all pending reports
#   ./review-fraud.sh show <report-id>       # Show detailed report
#   ./review-fraud.sh confirm <report-id>    # Confirm as true fraud
#   ./review-fraud.sh reject <report-id>     # Mark as false positive
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ELF_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
FRAUD_REVIEW_PY="$ELF_ROOT/query/fraud_review.py"

# Detect Python command
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
else
    echo "Error: Python not found. Install from https://python.org"
    exit 1
fi

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

usage() {
    cat << EOF
Fraud Review CLI - Interactive fraud report review

Usage:
    $(basename "$0") list                    List all pending fraud reports
    $(basename "$0") show <report-id>        Show detailed report with signals
    $(basename "$0") confirm <report-id>     Confirm as true fraud (true positive)
    $(basename "$0") reject <report-id>      Mark as false positive (not fraud)
    $(basename "$0") dismiss <report-id>     Dismiss (alias for reject)

Examples:
    # List all pending reports
    $(basename "$0") list

    # View detailed report
    $(basename "$0") show 5

    # Confirm fraud
    $(basename "$0") confirm 5

    # Mark as safe
    $(basename "$0") reject 5

EOF
    exit 1
}

# Check if fraud_review.py exists
if [[ ! -f "$FRAUD_REVIEW_PY" ]]; then
    echo -e "${RED}Error: fraud_review.py not found at $FRAUD_REVIEW_PY${NC}"
    exit 1
fi

# Parse command
COMMAND="${1:-}"
REPORT_ID="${2:-}"

case "$COMMAND" in
    list)
        echo -e "${BLUE}=== Pending Fraud Reports ===${NC}\n"
        $PYTHON_CMD "$FRAUD_REVIEW_PY" list
        ;;

    show)
        if [[ -z "$REPORT_ID" ]]; then
            echo -e "${RED}Error: report-id required${NC}"
            echo "Usage: $(basename "$0") show <report-id>"
            exit 1
        fi
        echo -e "${BLUE}=== Fraud Report #$REPORT_ID ===${NC}\n"
        $PYTHON_CMD "$FRAUD_REVIEW_PY" show --report-id "$REPORT_ID"
        ;;

    confirm)
        if [[ -z "$REPORT_ID" ]]; then
            echo -e "${RED}Error: report-id required${NC}"
            echo "Usage: $(basename "$0") confirm <report-id>"
            exit 1
        fi

        echo -e "${YELLOW}Confirming fraud report #$REPORT_ID as TRUE POSITIVE${NC}"
        echo -e "${YELLOW}This will mark the heuristic as having confirmed fraud.${NC}"
        echo -n "Are you sure? (y/N): "
        read -r CONFIRM

        if [[ "$CONFIRM" =~ ^[Yy]$ ]]; then
            $PYTHON_CMD "$FRAUD_REVIEW_PY" confirm --report-id "$REPORT_ID"
            echo -e "${GREEN}Report #$REPORT_ID confirmed as fraud.${NC}"
        else
            echo -e "${BLUE}Cancelled.${NC}"
        fi
        ;;

    reject|dismiss)
        if [[ -z "$REPORT_ID" ]]; then
            echo -e "${RED}Error: report-id required${NC}"
            echo "Usage: $(basename "$0") reject <report-id>"
            exit 1
        fi

        echo -e "${GREEN}Marking fraud report #$REPORT_ID as FALSE POSITIVE${NC}"
        echo -e "${GREEN}This will dismiss the alert and mark the heuristic as safe.${NC}"
        echo -n "Are you sure? (y/N): "
        read -r CONFIRM

        if [[ "$CONFIRM" =~ ^[Yy]$ ]]; then
            $PYTHON_CMD "$FRAUD_REVIEW_PY" reject --report-id "$REPORT_ID"
            echo -e "${GREEN}Report #$REPORT_ID marked as false positive.${NC}"
        else
            echo -e "${BLUE}Cancelled.${NC}"
        fi
        ;;

    ""|help|--help|-h)
        usage
        ;;

    *)
        echo -e "${RED}Error: Unknown command '$COMMAND'${NC}\n"
        usage
        ;;
esac
