#!/usr/bin/env bash
#
# Record Golden Rule Violation
#
# Usage: record-violation.sh <rule_number> "description"
# Example: record-violation.sh 1 "Started investigation without querying building"
#
# ACCOUNTABILITY-001: This script tracks violations of golden rules for accountability.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
BASE_DIR="$(dirname "$SCRIPT_DIR")"
DB_PATH="$BASE_DIR/memory/index.db"
GOLDEN_RULES_PATH="$BASE_DIR/memory/golden-rules.md"

# Detect Python command
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
else
    echo "Error: Python not found. Install from https://python.org"
    exit 1
fi

# Color output
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Validate inputs
if [ $# -lt 2 ]; then
    echo "Usage: record-violation.sh <rule_number> \"description\""
    echo ""
    echo "Example:"
    echo "  record-violation.sh 1 \"Started investigation without querying building\""
    echo ""
    echo "Available Golden Rules:"
    if [ -f "$GOLDEN_RULES_PATH" ]; then
        grep "^## [0-9]" "$GOLDEN_RULES_PATH" | head -10
    fi
    exit 1
fi

RULE_NUMBER="$1"
DESCRIPTION="$2"
SESSION_ID="${3:-$(date +%Y%m%d-%H%M%S)}"

# Validate rule number is an integer
if ! [[ "$RULE_NUMBER" =~ ^[0-9]+$ ]]; then
    echo -e "${RED}ERROR: Rule number must be a positive integer${NC}" >&2
    exit 1
fi

# Validate description is not empty
if [ -z "$DESCRIPTION" ]; then
    echo -e "${RED}ERROR: Description cannot be empty${NC}" >&2
    exit 1
fi

# Extract rule name from golden-rules.md
RULE_NAME=$(grep -A1 "^## $RULE_NUMBER\." "$GOLDEN_RULES_PATH" | tail -1 | sed 's/^> //' || echo "Unknown Rule")

if [ "$RULE_NAME" = "Unknown Rule" ]; then
    echo -e "${YELLOW}WARNING: Could not find rule #$RULE_NUMBER in golden-rules.md${NC}" >&2
    echo -e "${YELLOW}Recording as 'Unknown Rule'${NC}" >&2
fi

# Check database exists
if [ ! -f "$DB_PATH" ]; then
    echo -e "${RED}ERROR: Database not found at $DB_PATH${NC}" >&2
    exit 1
fi

# Insert violation into database using Python for proper SQL escaping
$PYTHON_CMD -c "
import sqlite3
import sys

db_path = sys.argv[1]
rule_id = int(sys.argv[2])
rule_name = sys.argv[3]
description = sys.argv[4]
session_id = sys.argv[5]

conn = sqlite3.connect(db_path)
cursor = conn.cursor()
cursor.execute(
    'INSERT INTO violations (rule_id, rule_name, description, session_id, violation_date) '
    'VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)',
    (rule_id, rule_name, description, session_id)
)
conn.commit()
conn.close()
" "$DB_PATH" "$RULE_NUMBER" "$RULE_NAME" "$DESCRIPTION" "$SESSION_ID"

if [ $? -eq 0 ]; then
    echo -e "${RED}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${RED}                   VIOLATION RECORDED                          ${NC}"
    echo -e "${RED}═══════════════════════════════════════════════════════════════${NC}"
    echo ""
    echo -e "  Rule #$RULE_NUMBER: ${YELLOW}$RULE_NAME${NC}"
    echo -e "  Description: $DESCRIPTION"
    echo -e "  Session: $SESSION_ID"
    echo ""

    # Get violation count for last 7 days
    RECENT_COUNT=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM violations WHERE violation_date >= datetime('now', '-7 days');")

    echo -e "  Recent violations (7 days): ${RED}$RECENT_COUNT${NC}"

    # Show warnings based on count
    if [ "$RECENT_COUNT" -ge 10 ]; then
        echo ""
        echo -e "${RED}╔═══════════════════════════════════════════════════════════╗${NC}"
        echo -e "${RED}║                 ⚠️  CRITICAL THRESHOLD  ⚠️                ║${NC}"
        echo -e "${RED}║         10+ violations - CEO escalation required         ║${NC}"
        echo -e "${RED}╚═══════════════════════════════════════════════════════════╝${NC}"

        # Auto-create CEO escalation
        CEO_INBOX="$BASE_DIR/ceo-inbox"
        mkdir -p "$CEO_INBOX"

        CEO_FILE="$CEO_INBOX/VIOLATION_THRESHOLD_$(date +%Y%m%d_%H%M%S).md"
        cat > "$CEO_FILE" <<CEOEOF
# Golden Rule Violations - Threshold Exceeded

**Status:** Urgent Review Required
**Date:** $(date '+%Y-%m-%d %H:%M:%S')
**Total Violations (7 days):** $RECENT_COUNT

## Context

The system has recorded $RECENT_COUNT Golden Rule violations in the past 7 days, exceeding the critical threshold of 10. This indicates systematic issues with following established best practices.

## Recent Violations

\`\`\`
$(sqlite3 "$DB_PATH" "SELECT rule_id, rule_name, description, violation_date FROM violations WHERE violation_date >= datetime('now', '-7 days') ORDER BY violation_date DESC LIMIT 10;" -header -column)
\`\`\`

## Violations by Rule

\`\`\`
$(sqlite3 "$DB_PATH" "SELECT rule_id, rule_name, COUNT(*) as count FROM violations WHERE violation_date >= datetime('now', '-7 days') GROUP BY rule_id ORDER BY count DESC;" -header -column)
\`\`\`

## Options

1. **Review and Reset** - Acknowledge violations, reset counter, implement corrective measures
2. **System Adjustment** - Modify golden rules if they're not practical
3. **Enhanced Monitoring** - Add automated checks to prevent violations
4. **Training** - Additional context/examples for problematic rules

## Recommendation

Review violation patterns to identify if this is:
- A training issue (rules not clear)
- A workflow issue (rules not practical)
- An accountability issue (rules being ignored)

Take corrective action and reset acknowledgment status.
CEOEOF

        echo ""
        echo -e "  ${YELLOW}CEO escalation created: $CEO_FILE${NC}"

        # Insert into CEO reviews table
        sqlite3 "$DB_PATH" <<CEOSQL
INSERT INTO ceo_reviews (title, context, recommendation, status)
VALUES (
    'Golden Rule Violations Threshold Exceeded',
    'System recorded $RECENT_COUNT violations in 7 days, exceeding critical threshold.',
    'Review violation patterns and take corrective action. See $CEO_FILE for details.',
    'pending'
);
CEOSQL

    elif [ "$RECENT_COUNT" -ge 5 ]; then
        echo ""
        echo -e "${YELLOW}╔═══════════════════════════════════════════════════════════╗${NC}"
        echo -e "${YELLOW}║                    ⚠️  PROBATION MODE  ⚠️                 ║${NC}"
        echo -e "${YELLOW}║          5+ violations - Increased scrutiny              ║${NC}"
        echo -e "${YELLOW}╚═══════════════════════════════════════════════════════════╝${NC}"
    elif [ "$RECENT_COUNT" -ge 3 ]; then
        echo ""
        echo -e "${YELLOW}╔═══════════════════════════════════════════════════════════╗${NC}"
        echo -e "${YELLOW}║                      ⚠️  WARNING  ⚠️                       ║${NC}"
        echo -e "${YELLOW}║           3+ violations - Review adherence               ║${NC}"
        echo -e "${YELLOW}╚═══════════════════════════════════════════════════════════╝${NC}"
    fi

    echo ""
    echo -e "${RED}═══════════════════════════════════════════════════════════════${NC}"
else
    echo -e "${RED}ERROR: Failed to record violation${NC}" >&2
    exit 1
fi
