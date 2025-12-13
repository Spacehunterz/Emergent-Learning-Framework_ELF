#!/bin/bash
# Check all invariants in the Emergent Learning Framework
#
# Usage: ./check-invariants.sh [--project /path/to/project]
#
# Exit codes:
#   0 = All invariants passed
#   1 = One or more invariants failed
#   2 = Script error

# Note: Not using set -e because we want to continue checking all invariants even if one fails

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$(dirname "$SCRIPT_DIR")"
MEMORY_DIR="$BASE_DIR/memory"
DB_PATH="$MEMORY_DIR/index.db"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default project path (current directory if not specified)
PROJECT_PATH="."

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --project) PROJECT_PATH="$2"; shift 2 ;;
        --help)
            echo "Usage: $0 [--project /path/to/project]"
            echo ""
            echo "Checks all active invariants against the specified project."
            echo "If no project is specified, uses current directory."
            exit 0
            ;;
        *) shift ;;
    esac
done

# Resolve project path
PROJECT_PATH="$(cd "$PROJECT_PATH" 2>/dev/null && pwd)" || {
    echo -e "${RED}ERROR: Project path does not exist: $PROJECT_PATH${NC}"
    exit 2
}

echo -e "${BLUE}=== Invariant Check ===${NC}"
echo "Project: $PROJECT_PATH"
echo ""

# Check database exists
if [ ! -f "$DB_PATH" ]; then
    echo -e "${RED}ERROR: Database not found: $DB_PATH${NC}"
    exit 2
fi

# Track results
PASSED=0
FAILED=0
SKIPPED=0
FAILED_INVARIANTS=""

# Built-in validators for known invariants (when validation_code is empty)
# These are keyed by invariant statement patterns
check_builtin() {
    local statement="$1"
    local domain="$2"

    case "$statement" in
        *"API responses"*"request_id"*)
            check_api_request_id
            return $?
            ;;
        *"WebSocket"*"one handler"*|*"exactly one handler"*)
            check_websocket_handlers
            return $?
            ;;
        *)
            # No built-in check available
            return 255
            ;;
    esac
}

# Check: All API responses must include request_id
check_api_request_id() {
    echo -n "  Checking API response patterns... "

    # Look for API response patterns without request_id
    # This is a heuristic check - looks for return statements in API handlers

    local api_files=$(find "$PROJECT_PATH" -type f \( -name "*.py" -o -name "*.ts" -o -name "*.js" \) \
        -path "*/api/*" -o -path "*/routes/*" -o -path "*/endpoints/*" 2>/dev/null | head -50)

    if [ -z "$api_files" ]; then
        # Also check for common API file patterns
        api_files=$(find "$PROJECT_PATH" -type f \( -name "*api*.py" -o -name "*route*.py" -o -name "main.py" \) 2>/dev/null | head -50)
    fi

    if [ -z "$api_files" ]; then
        echo -e "${YELLOW}no API files found${NC}"
        return 255  # Skip
    fi

    # Check if JSONResponse/jsonify calls include request_id
    local violations=""
    for file in $api_files; do
        # Python: Look for JSONResponse or return {...} without request_id
        if [[ "$file" == *.py ]]; then
            # Find JSON responses that might be missing request_id
            local responses=$(grep -n "JSONResponse\|return {" "$file" 2>/dev/null | grep -v "request_id" | head -5)
            if [ -n "$responses" ]; then
                violations="$violations\n  $file: possible missing request_id"
            fi
        fi
    done

    if [ -n "$violations" ]; then
        echo -e "${YELLOW}potential issues found${NC}"
        echo -e "$violations"
        return 1
    fi

    echo -e "${GREEN}OK${NC}"
    return 0
}

# Check: WebSocket connections must have exactly one handler per event type
check_websocket_handlers() {
    echo -n "  Checking WebSocket handler patterns... "

    # Look for WebSocket files (exclude node_modules, dist, build)
    local ws_files=$(find "$PROJECT_PATH" -type f \( -name "*.ts" -o -name "*.tsx" -o -name "*.js" -o -name "*.jsx" \) \
        -not -path "*/node_modules/*" -not -path "*/dist/*" -not -path "*/build/*" -not -path "*/.git/*" \
        -exec grep -l "WebSocket\|useWebSocket\|onmessage\|addEventListener.*message" {} \; 2>/dev/null | head -20)

    if [ -z "$ws_files" ]; then
        echo -e "${YELLOW}no WebSocket files found${NC}"
        return 255  # Skip
    fi

    local violations=""
    for file in $ws_files; do
        # Check for multiple addEventListener('message') or onmessage assignments
        # Use head -1 to handle potential multi-line output from grep -c
        local message_handlers=$(grep -c "addEventListener.*['\"]message['\"]\\|onmessage.*=" "$file" 2>/dev/null | head -1 || echo "0")
        message_handlers=${message_handlers:-0}
        if [ "$message_handlers" -gt 1 ] 2>/dev/null; then
            violations="$violations\n  $file: $message_handlers message handlers found (should be 1)"
        fi

        # Check for useEffect with WebSocket that might cause reconnect loops
        # Look for useEffect dependencies that include callbacks
        local effect_issues=$(grep -A5 "useEffect.*WebSocket\|useEffect.*socket" "$file" 2>/dev/null | \
            grep -c "onMessage\|onError\|callback" 2>/dev/null | head -1 || echo "0")
        effect_issues=${effect_issues:-0}
        if [ "$effect_issues" -gt 0 ] 2>/dev/null; then
            violations="$violations\n  $file: useEffect may have callback dependencies (reconnect loop risk)"
        fi
    done

    if [ -n "$violations" ]; then
        echo -e "${RED}FAILED${NC}"
        echo -e "$violations"
        return 1
    fi

    echo -e "${GREEN}OK${NC}"
    return 0
}

# Run custom validation code
run_validation_code() {
    local code="$1"
    local statement="$2"

    echo -n "  Running validation... "

    # Execute the validation code
    # The code should exit 0 for pass, non-zero for fail
    cd "$PROJECT_PATH"
    if eval "$code" > /dev/null 2>&1; then
        echo -e "${GREEN}OK${NC}"
        return 0
    else
        echo -e "${RED}FAILED${NC}"
        return 1
    fi
}

# Query invariants into temp file (avoids stdin consumption by find/grep in validators)
INVARIANTS_FILE=$(mktemp)
trap "rm -f $INVARIANTS_FILE" EXIT
sqlite3 "$DB_PATH" "SELECT id, statement, domain, scope, validation_type, validation_code, severity FROM invariants WHERE status = 'active';" > "$INVARIANTS_FILE"

# Check each invariant
while IFS='|' read -r id statement domain scope validation_type validation_code severity; do
    echo -e "${BLUE}[$id]${NC} $statement"
    echo "    Domain: ${domain:-any} | Scope: $scope | Severity: $severity"

    result=0

    if [ -n "$validation_code" ] && [ "$validation_code" != "NULL" ]; then
        # Has custom validation code
        run_validation_code "$validation_code" "$statement"
        result=$?
    else
        # Try built-in check
        check_builtin "$statement" "$domain"
        result=$?
    fi

    if [ $result -eq 0 ]; then
        ((PASSED++))
        # Update last_validated_at
        sqlite3 "$DB_PATH" "UPDATE invariants SET last_validated_at = datetime('now') WHERE id = $id;"
    elif [ $result -eq 255 ]; then
        ((SKIPPED++))
        echo -e "    ${YELLOW}Skipped (no validator available)${NC}"
    else
        ((FAILED++))
        FAILED_INVARIANTS="$FAILED_INVARIANTS\n  - $statement"
        # Update violation tracking
        sqlite3 "$DB_PATH" "UPDATE invariants SET violation_count = violation_count + 1, last_violated_at = datetime('now') WHERE id = $id;"
    fi

    echo ""

done < "$INVARIANTS_FILE"

# Summary
echo -e "${BLUE}=== Summary ===${NC}"
echo -e "Passed:  ${GREEN}$PASSED${NC}"
echo -e "Failed:  ${RED}$FAILED${NC}"
echo -e "Skipped: ${YELLOW}$SKIPPED${NC}"

if [ $FAILED -gt 0 ]; then
    echo ""
    echo -e "${RED}Failed invariants:${NC}$FAILED_INVARIANTS"
    exit 1
fi

exit 0
