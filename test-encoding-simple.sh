#!/bin/bash
# Simple encoding edge case tests - runs each test individually

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DB_PATH="$SCRIPT_DIR/memory/index.db"
FAILURES_DIR="$SCRIPT_DIR/memory/failures"
RECORD_SCRIPT="$SCRIPT_DIR/scripts/record-failure.sh"

echo "==================================="
echo "SIMPLE ENCODING EDGE CASE TESTS"
echo "==================================="
echo ""

# Test 1: NULL byte injection
echo "[TEST 1] NULL byte in title"
printf "Title with null byte: Test\x00Title\n"
result=$(printf "Test\x00Title" | od -An -tx1)
echo "Hex representation: $result"
echo ""

# Try to record it
echo "Attempting to record..."
export FAILURE_TITLE="TestTitle"  # Bash strips NULL bytes in command substitution
export FAILURE_DOMAIN="encoding-test"
export FAILURE_SUMMARY="Testing NULL byte handling"
export FAILURE_SEVERITY="3"

timeout 10 "$RECORD_SCRIPT" >/dev/null 2>&1 && echo "✓ Recorded successfully" || echo "✗ Failed (exit code: $?)"
echo ""

# Test 2: SQL injection with quotes
echo "[TEST 2] SQL injection attempt"
export FAILURE_TITLE="'; DROP TABLE learnings; --"
export FAILURE_DOMAIN="encoding-test"
export FAILURE_SUMMARY="Testing SQL injection"
export FAILURE_SEVERITY="3"

timeout 10 "$RECORD_SCRIPT" >/dev/null 2>&1 && echo "✓ Recorded successfully" || echo "✗ Failed (exit code: $?)"

# Check if table still exists
if sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM learnings;" >/dev/null 2>&1; then
    echo "✓ Table learnings still exists (injection prevented)"
else
    echo "✗ CRITICAL: Table was dropped!"
fi
echo ""

# Test 3: Unicode emoji
echo "[TEST 3] Unicode emoji"
export FAILURE_TITLE="🔥💻🚀 Test Title"
export FAILURE_DOMAIN="encoding-test"
export FAILURE_SUMMARY="Testing emoji support"
export FAILURE_SEVERITY="3"

timeout 10 "$RECORD_SCRIPT" >/dev/null 2>&1 && echo "✓ Recorded successfully" || echo "✗ Failed (exit code: $?)"

# Check if stored correctly
stored=$(sqlite3 "$DB_PATH" "SELECT title FROM learnings WHERE domain='encoding-test' ORDER BY id DESC LIMIT 1;" 2>/dev/null)
echo "Stored in DB: $stored"
echo ""

# Test 4: CRLF injection
echo "[TEST 4] CRLF injection"
export FAILURE_TITLE="Title"$'\r\n'"## Injected Header"
export FAILURE_DOMAIN="encoding-test"
export FAILURE_SUMMARY="Testing CRLF"
export FAILURE_SEVERITY="3"

timeout 10 "$RECORD_SCRIPT" >/dev/null 2>&1 && echo "✓ Recorded successfully" || echo "✗ Failed (exit code: $?)"

# Check the markdown file
md_file=$(find "$FAILURES_DIR" -name "*.md" -type f -newermt "1 minute ago" 2>/dev/null | head -1)
if [ -n "$md_file" ]; then
    echo "Checking markdown file: $(basename "$md_file")"
    if grep -q "## Injected Header" "$md_file"; then
        echo "✗ CRITICAL: CRLF injection succeeded!"
        echo "  Markdown structure was manipulated"
    else
        echo "✓ CRLF injection prevented"
    fi
fi
echo ""

# Test 5: ANSI escape codes
echo "[TEST 5] ANSI escape codes"
export FAILURE_TITLE=$'\033[31m'"Red Title"$'\033[0m'
export FAILURE_DOMAIN="encoding-test"
export FAILURE_SUMMARY="Testing ANSI codes"
export FAILURE_SEVERITY="3"

timeout 10 "$RECORD_SCRIPT" >/dev/null 2>&1 && echo "✓ Recorded successfully" || echo "✗ Failed (exit code: $?)"

# Check if ANSI codes are in file
md_file=$(find "$FAILURES_DIR" -name "*.md" -type f -newermt "1 minute ago" 2>/dev/null | head -1)
if [ -n "$md_file" ]; then
    if grep -q $'\033\[' "$md_file"; then
        echo "✗ WARNING: ANSI escape codes present in markdown"
        echo "  Could cause terminal manipulation"
    else
        echo "✓ ANSI codes filtered/escaped"
    fi
fi
echo ""

# Test 6: Long filename test
echo "[TEST 6] Very long title (filename length)"
long_title=$(python3 -c "print('A' * 300)" 2>/dev/null || printf 'A%.0s' {1..300})
export FAILURE_TITLE="$long_title"
export FAILURE_DOMAIN="encoding-test"
export FAILURE_SUMMARY="Testing long titles"
export FAILURE_SEVERITY="3"

timeout 10 "$RECORD_SCRIPT" >/dev/null 2>&1 && echo "✓ Recorded successfully" || echo "✗ Failed (exit code: $?)"

# Check created file
md_file=$(find "$FAILURES_DIR" -name "*.md" -type f -newermt "1 minute ago" 2>/dev/null | head -1)
if [ -n "$md_file" ]; then
    filename=$(basename "$md_file")
    length=${#filename}
    echo "  Created filename length: $length characters"
    if [ $length -gt 255 ]; then
        echo "✗ WARNING: Filename may exceed filesystem limits"
    else
        echo "✓ Filename within safe limits"
    fi
fi
echo ""

# Test 7: Path traversal attempt
echo "[TEST 7] Path traversal in title"
export FAILURE_TITLE="../../../etc/passwd"
export FAILURE_DOMAIN="encoding-test"
export FAILURE_SUMMARY="Testing path traversal"
export FAILURE_SEVERITY="3"

timeout 10 "$RECORD_SCRIPT" >/dev/null 2>&1 && echo "✓ Recorded successfully" || echo "✗ Failed (exit code: $?)"

# Check if file was created outside failures directory
if find "$SCRIPT_DIR" -name "*passwd*" -type f -newermt "1 minute ago" 2>/dev/null | grep -qv "$FAILURES_DIR"; then
    echo "✗ CRITICAL: Path traversal succeeded!"
else
    echo "✓ Path traversal prevented"
fi
echo ""

echo "==================================="
echo "TESTS COMPLETE"
echo "==================================="
echo ""
echo "Check the database and files manually for detailed inspection:"
echo "  Database: $DB_PATH"
echo "  Failures: $FAILURES_DIR"
echo ""
