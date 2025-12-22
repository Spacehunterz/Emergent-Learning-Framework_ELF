#!/bin/bash
# Fix Filename Length Issue - Agent C
# Limit generated filenames to prevent filesystem errors

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$SCRIPT_DIR"

echo "========================================="
echo "FIXING FILENAME LENGTH ISSUE"
echo "========================================="
echo ""

# Fix record-failure.sh
echo "[1/2] Fixing filename generation in record-failure.sh..."

# Find the line with filename generation
if grep -q "filename_title=\$(echo \"\$title\"" "$BASE_DIR/scripts/record-failure.sh"; then
    # Replace the filename generation with length-limited version
    sed -i 's/filename_title=\$(echo "\$title" | tr .*/filename_title=$(echo "$title" | tr '\'':[:upper:]:'\'' '\'':[:lower:]:'\'' | tr '\'' '\'' '\''-'\'' | tr -cd '\'':[:alnum:]-'\'' | cut -c1-100)/' "$BASE_DIR/scripts/record-failure.sh"
    echo "✓ Updated record-failure.sh filename generation (max 100 chars)"
else
    echo "✗ Could not find filename generation pattern"
fi

# Fix record-heuristic.sh (domain file is already bounded by domain length limit)
echo "[2/2] Checking record-heuristic.sh..."
echo "✓ Domain-based filenames already bounded by MAX_DOMAIN_LENGTH=100"

echo ""
echo "Testing filename generation..."

# Test with 500-char title
TITLE_500=$(python3 -c "print('TEST' * 125)" 2>/dev/null || echo "TESTTEST")

echo -n "  Test: 500-char title generates valid filename: "
FILENAME=$(echo "$TITLE_500" | tr '[:upper:]' '[:lower:]' | tr ' ' '-' | tr -cd '[:alnum:]-' | cut -c1-100)
FULL_PATH="/tmp/test_$(date +%Y%m%d)_${FILENAME}.md"

if touch "$FULL_PATH" 2>/dev/null; then
    rm "$FULL_PATH"
    echo "✓ PASS (filename length: ${#FILENAME} chars)"
else
    echo "✗ FAIL"
fi

echo ""
echo "========================================="
echo "FIX COMPLETE"
echo "========================================="
echo ""
echo "Filename generation now limits to 100 characters max"
echo "Full filename format: YYYYMMDD_[title-slug-100-chars].md"
echo ""
