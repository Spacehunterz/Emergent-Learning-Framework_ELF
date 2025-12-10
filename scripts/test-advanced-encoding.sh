#!/bin/bash
# Advanced encoding tests for specific attack vectors

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DB_PATH="$SCRIPT_DIR/memory/index.db"
FAILURES_DIR="$SCRIPT_DIR/memory/failures"

echo "==================================="
echo "ADVANCED ENCODING ATTACK TESTS"
echo "==================================="
echo ""

# Test: Terminal title injection
echo "[TEST A] Terminal title injection"
export FAILURE_TITLE=$'\033]0;Hacked Terminal\007'Normal
export FAILURE_DOMAIN="encoding-test"
export FAILURE_SUMMARY="Terminal control sequence"
export FAILURE_SEVERITY="3"

timeout 10 bash ~/.claude/emergent-learning/scripts/record-failure.sh >/dev/null 2>&1
if sqlite3 "$DB_PATH" "SELECT hex(title) FROM learnings WHERE domain='encoding-test' ORDER BY id DESC LIMIT 1;" 2>/dev/null | grep -q "1B"; then
    echo "✗ CRITICAL: Terminal control sequences stored in DB"
    echo "  Hex contains ESC character (0x1B)"
else
    echo "✓ Terminal sequences filtered"
fi
echo ""

# Test: SQL with newlines
echo "[TEST B] Multiline SQL injection"
export FAILURE_TITLE=$'TestTitle\'; \nDROP TABLE learnings;\n--'
export FAILURE_DOMAIN="encoding-test"
export FAILURE_SUMMARY="Multiline SQL"
export FAILURE_SEVERITY="3"

timeout 10 bash ~/.claude/emergent-learning/scripts/record-failure.sh >/dev/null 2>&1
if sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM learnings;" >/dev/null 2>&1; then
    echo "✓ Table still exists"
    stored=$(sqlite3 "$DB_PATH" "SELECT title FROM learnings WHERE domain='encoding-test' ORDER BY id DESC LIMIT 1;" 2>/dev/null)
    echo "  Stored as: $(echo "$stored" | tr '\n' ' ' | head -c 50)"
else
    echo "✗ CRITICAL: Table was dropped!"
fi
echo ""

# Test: Markdown link injection
echo "[TEST C] Markdown link injection"
export FAILURE_TITLE='[Click me](javascript:alert(1))'
export FAILURE_DOMAIN="encoding-test"
export FAILURE_SUMMARY="XSS via markdown"
export FAILURE_SEVERITY="3"

timeout 10 bash ~/.claude/emergent-learning/scripts/record-failure.sh >/dev/null 2>&1
md_file=$(find "$FAILURES_DIR" -name "*.md" -type f -newermt "1 minute ago" 2>/dev/null | head -1)
if [ -n "$md_file" ] && grep -q "javascript:" "$md_file"; then
    echo "✗ WARNING: JavaScript link present in markdown"
    echo "  Could enable XSS if rendered in browser"
else
    echo "✓ JavaScript links filtered or escaped"
fi
echo ""

# Test: UTF-8 overlong encoding
echo "[TEST D] UTF-8 overlong encoding attack"
# Overlong encoding of '/' character
export FAILURE_TITLE=$'Test\xC0\xAFTitle'
export FAILURE_DOMAIN="encoding-test"
export FAILURE_SUMMARY="Overlong UTF-8"
export FAILURE_SEVERITY="3"

timeout 10 bash ~/.claude/emergent-learning/scripts/record-failure.sh >/dev/null 2>&1 || true
stored=$(sqlite3 "$DB_PATH" "SELECT title FROM learnings WHERE domain='encoding-test' ORDER BY id DESC LIMIT 1;" 2>/dev/null)
echo "  Stored as: $(echo "$stored" | cat -v)"
echo ""

# Test: Homoglyph attack
echo "[TEST E] Unicode homoglyph attack"
export FAILURE_TITLE='Аdmin'  # First 'A' is Cyrillic А (U+0410)
export FAILURE_DOMAIN="encoding-test"
export FAILURE_SUMMARY="Homoglyph spoofing"
export FAILURE_SEVERITY="3"

timeout 10 bash ~/.claude/emergent-learning/scripts/record-failure.sh >/dev/null 2>&1
stored=$(sqlite3 "$DB_PATH" "SELECT title FROM learnings WHERE domain='encoding-test' ORDER BY id DESC LIMIT 1;" 2>/dev/null)
stored_hex=$(sqlite3 "$DB_PATH" "SELECT hex(title) FROM learnings WHERE domain='encoding-test' ORDER BY id DESC LIMIT 1;" 2>/dev/null)
if echo "$stored_hex" | grep -q "D090"; then
    echo "✗ WARNING: Cyrillic character stored (U+0410)"
    echo "  Could enable spoofing attacks"
    echo "  Looks like: $stored"
else
    echo "✓ Homoglyph detected or normalized"
fi
echo ""

# Test: Zero-width characters
echo "[TEST F] Zero-width character injection"
export FAILURE_TITLE=$'Admin\u200B\u200C\u200DTest'  # Zero-width space, non-joiner, joiner
export FAILURE_DOMAIN="encoding-test"
export FAILURE_SUMMARY="Invisible characters"
export FAILURE_SEVERITY="3"

timeout 10 bash ~/.claude/emergent-learning/scripts/record-failure.sh >/dev/null 2>&1
stored=$(sqlite3 "$DB_PATH" "SELECT title FROM learnings WHERE domain='encoding-test' ORDER BY id DESC LIMIT 1;" 2>/dev/null)
length=${#stored}
visible=$(echo "$stored" | tr -d '[:space:]')
visible_length=${#visible}
echo "  Total length: $length"
echo "  Visible length: $visible_length"
if [ $length -ne $visible_length ]; then
    echo "✗ WARNING: Invisible characters present"
else
    echo "✓ All characters visible"
fi
echo ""

# Test: Markdown header injection via summary
echo "[TEST G] Summary field markdown injection"
export FAILURE_TITLE="Normal Title"
export FAILURE_DOMAIN="encoding-test"
export FAILURE_SUMMARY=$'Normal text\n\n## Injected Header\n\nMalicious content'
export FAILURE_SEVERITY="3"

timeout 10 bash ~/.claude/emergent-learning/scripts/record-failure.sh >/dev/null 2>&1
md_file=$(find "$FAILURES_DIR" -name "*.md" -type f -newermt "1 minute ago" 2>/dev/null | head -1)
if [ -n "$md_file" ]; then
    # Count how many "## Injected Header" appear
    count=$(grep -c "## Injected Header" "$md_file" 2>/dev/null || echo "0")
    if [ "$count" -gt 0 ]; then
        echo "✗ CRITICAL: Markdown injection in summary field"
        echo "  Found $count occurrence(s) of injected header"
    else
        echo "✓ Summary injection prevented"
    fi
fi
echo ""

echo "==================================="
echo "ADVANCED TESTS COMPLETE"
echo "==================================="
