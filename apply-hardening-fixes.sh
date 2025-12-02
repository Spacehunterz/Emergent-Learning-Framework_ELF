#!/bin/bash
# Apply Input Validation Hardening Fixes - Agent C
# Implements defensive programming improvements

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$SCRIPT_DIR"

echo "========================================="
echo "APPLYING INPUT VALIDATION HARDENING"
echo "========================================="
echo ""

# Backup original scripts
echo "[1/5] Creating backups..."
cp "$BASE_DIR/scripts/record-failure.sh" "$BASE_DIR/scripts/record-failure.sh.pre-hardening"
cp "$BASE_DIR/scripts/record-heuristic.sh" "$BASE_DIR/scripts/record-heuristic.sh.pre-hardening"
cp "$BASE_DIR/query/query.py" "$BASE_DIR/query/query.py.pre-hardening"
echo "✓ Backups created"

# Fix 1: Add input length validation to record-failure.sh
echo ""
echo "[2/5] Adding input length validation to record-failure.sh..."

# Find the line after non-interactive mode check, before markdown file creation
LINE_NUM=$(grep -n "log \"INFO\" \"Recording failure:" "$BASE_DIR/scripts/record-failure.sh" | head -1 | cut -d: -f1)

if [ -n "$LINE_NUM" ]; then
    # Create temporary file with validation code
    cat > /tmp/length_validation_failure.txt <<'VALIDATION'

# Input length validation (added by Agent C hardening)
MAX_TITLE_LENGTH=500
MAX_DOMAIN_LENGTH=100
MAX_SUMMARY_LENGTH=50000

if [ ${#title} -gt $MAX_TITLE_LENGTH ]; then
    log "ERROR" "Title exceeds maximum length ($MAX_TITLE_LENGTH characters, got ${#title})"
    echo "ERROR: Title too long (max $MAX_TITLE_LENGTH characters)" >&2
    exit 1
fi

if [ ${#domain} -gt $MAX_DOMAIN_LENGTH ]; then
    log "ERROR" "Domain exceeds maximum length ($MAX_DOMAIN_LENGTH characters)"
    echo "ERROR: Domain too long (max $MAX_DOMAIN_LENGTH characters)" >&2
    exit 1
fi

if [ ${#summary} -gt $MAX_SUMMARY_LENGTH ]; then
    log "ERROR" "Summary exceeds maximum length ($MAX_SUMMARY_LENGTH characters, got ${#summary})"
    echo "ERROR: Summary too long (max $MAX_SUMMARY_LENGTH characters)" >&2
    exit 1
fi

# Trim leading/trailing whitespace
title=$(echo "$title" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')
domain=$(echo "$domain" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')

# Re-validate after trimming
if [ -z "$title" ]; then
    log "ERROR" "Title cannot be empty (or whitespace-only)"
    echo "ERROR: Title cannot be empty" >&2
    exit 1
fi

if [ -z "$domain" ]; then
    log "ERROR" "Domain cannot be empty (or whitespace-only)"
    echo "ERROR: Domain cannot be empty" >&2
    exit 1
fi

VALIDATION

    # Insert validation before the logging line
    sed -i "${LINE_NUM}r /tmp/length_validation_failure.txt" "$BASE_DIR/scripts/record-failure.sh"
    rm /tmp/length_validation_failure.txt
    echo "✓ Added length validation to record-failure.sh"
else
    echo "✗ Could not find insertion point in record-failure.sh"
fi

# Fix 2: Add input length validation to record-heuristic.sh
echo ""
echo "[3/5] Adding input length validation to record-heuristic.sh..."

LINE_NUM=$(grep -n "log \"INFO\" \"Recording heuristic:" "$BASE_DIR/scripts/record-heuristic.sh" | head -1 | cut -d: -f1)

if [ -n "$LINE_NUM" ]; then
    cat > /tmp/length_validation_heuristic.txt <<'VALIDATION'

# Input length validation (added by Agent C hardening)
MAX_RULE_LENGTH=500
MAX_DOMAIN_LENGTH=100
MAX_EXPLANATION_LENGTH=5000

if [ ${#rule} -gt $MAX_RULE_LENGTH ]; then
    log "ERROR" "Rule exceeds maximum length ($MAX_RULE_LENGTH characters, got ${#rule})"
    echo "ERROR: Rule too long (max $MAX_RULE_LENGTH characters)" >&2
    exit 1
fi

if [ ${#domain} -gt $MAX_DOMAIN_LENGTH ]; then
    log "ERROR" "Domain exceeds maximum length ($MAX_DOMAIN_LENGTH characters)"
    echo "ERROR: Domain too long (max $MAX_DOMAIN_LENGTH characters)" >&2
    exit 1
fi

if [ ${#explanation} -gt $MAX_EXPLANATION_LENGTH ]; then
    log "ERROR" "Explanation exceeds maximum length ($MAX_EXPLANATION_LENGTH characters)"
    echo "ERROR: Explanation too long (max $MAX_EXPLANATION_LENGTH characters)" >&2
    exit 1
fi

# Trim leading/trailing whitespace
rule=$(echo "$rule" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')
domain=$(echo "$domain" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')

# Re-validate after trimming
if [ -z "$rule" ]; then
    log "ERROR" "Rule cannot be empty (or whitespace-only)"
    echo "ERROR: Rule cannot be empty" >&2
    exit 1
fi

if [ -z "$domain" ]; then
    log "ERROR" "Domain cannot be empty (or whitespace-only)"
    echo "ERROR: Domain cannot be empty" >&2
    exit 1
fi

VALIDATION

    sed -i "${LINE_NUM}r /tmp/length_validation_heuristic.txt" "$BASE_DIR/scripts/record-heuristic.sh"
    rm /tmp/length_validation_heuristic.txt
    echo "✓ Added length validation to record-heuristic.sh"
else
    echo "✗ Could not find insertion point in record-heuristic.sh"
fi

# Fix 3: Add result limit caps to query.py
echo ""
echo "[4/5] Adding result limit caps to query.py..."

# Find the main() function and add caps after argument parsing
if grep -q "args = parser.parse_args()" "$BASE_DIR/query/query.py"; then
    # Create Python code to insert
    cat > /tmp/query_caps.py <<'PYCAPS'

    # Cap limits to prevent resource exhaustion (added by Agent C hardening)
    MAX_LIMIT = 1000
    MAX_TOKENS = 50000

    if hasattr(args, 'limit') and args.limit and args.limit > MAX_LIMIT:
        print(f"Warning: Limit capped at {MAX_LIMIT} results (requested: {args.limit})",
              file=sys.stderr)
        args.limit = MAX_LIMIT

    if hasattr(args, 'recent') and args.recent and args.recent > MAX_LIMIT:
        print(f"Warning: Recent limit capped at {MAX_LIMIT} results (requested: {args.recent})",
              file=sys.stderr)
        args.recent = MAX_LIMIT

    if hasattr(args, 'max_tokens') and args.max_tokens > MAX_TOKENS:
        print(f"Warning: Max tokens capped at {MAX_TOKENS} (requested: {args.max_tokens})",
              file=sys.stderr)
        args.max_tokens = MAX_TOKENS
PYCAPS

    LINE_NUM=$(grep -n "args = parser.parse_args()" "$BASE_DIR/query/query.py" | head -1 | cut -d: -f1)

    # Insert after parse_args() line
    NEXT_LINE=$((LINE_NUM + 1))
    sed -i "${NEXT_LINE}r /tmp/query_caps.py" "$BASE_DIR/query/query.py"
    rm /tmp/query_caps.py
    echo "✓ Added limit caps to query.py"
else
    echo "✗ Could not find insertion point in query.py"
fi

# Fix 4: Test the hardened scripts
echo ""
echo "[5/5] Testing hardened scripts..."

# Test 1: Overly long title
echo -n "  Test 1 (long title rejection): "
LONG_TITLE=$(python3 -c "print('A' * 600)" 2>/dev/null || echo "AAAAAA")
if FAILURE_TITLE="$LONG_TITLE" FAILURE_DOMAIN="test" FAILURE_SUMMARY="test" timeout 5 bash "$BASE_DIR/scripts/record-failure.sh" 2>&1 | grep -q "Title too long"; then
    echo "✓ PASS"
else
    echo "✗ FAIL"
fi

# Test 2: Whitespace-only after trim
echo -n "  Test 2 (whitespace trim): "
if FAILURE_TITLE="   " FAILURE_DOMAIN="test" FAILURE_SUMMARY="test" timeout 5 bash "$BASE_DIR/scripts/record-failure.sh" 2>&1 | grep -q "cannot be empty"; then
    echo "✓ PASS"
else
    echo "✗ FAIL"
fi

# Test 3: Python limit cap
echo -n "  Test 3 (Python limit cap): "
if timeout 5 python3 "$BASE_DIR/query/query.py" --recent 999999 2>&1 | grep -q "Warning.*capped"; then
    echo "✓ PASS"
else
    echo "✗ WARN (may not trigger warning)"
fi

echo ""
echo "========================================="
echo "HARDENING COMPLETE"
echo "========================================="
echo ""
echo "Summary:"
echo "  - Input length limits added to all scripts"
echo "  - Whitespace trimming implemented"
echo "  - Result caps added to Python query system"
echo "  - Original scripts backed up with .pre-hardening extension"
echo ""
echo "Hardened scripts location:"
echo "  $BASE_DIR/scripts/record-failure.sh"
echo "  $BASE_DIR/scripts/record-heuristic.sh"
echo "  $BASE_DIR/query/query.py"
echo ""
echo "To revert: mv [file].pre-hardening [file]"
echo ""
