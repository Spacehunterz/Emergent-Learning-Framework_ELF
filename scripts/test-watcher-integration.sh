#!/bin/bash
#
# Test Watcher Integration
#
# Verifies all components are in place and properly configured
# Does NOT require ANTHROPIC_API_KEY or make actual API calls
#

set -e

# Detect Python command
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
else
    echo "Error: Python not found. Install from https://python.org"
    exit 1
fi

PROJECT_DIR="$HOME/.claude/emergent-learning"
WATCHER_DIR="$PROJECT_DIR/watcher"
COORD_DIR="$PROJECT_DIR/.coordination"

echo "=================================="
echo "Tiered Watcher Integration Tests"
echo "=================================="
echo

# Test 1: Directory structure
echo "[1/8] Checking directory structure..."
if [ -d "$WATCHER_DIR" ]; then
    echo "  ✓ watcher/ directory exists"
else
    echo "  ✗ watcher/ directory missing"
    exit 1
fi

if [ -d "$COORD_DIR" ]; then
    echo "  ✓ .coordination/ directory exists"
else
    echo "  ✗ .coordination/ directory missing"
    exit 1
fi

# Test 2: Core files
echo
echo "[2/8] Checking core files..."
REQUIRED_FILES=(
    "$WATCHER_DIR/__init__.py"
    "$WATCHER_DIR/config.py"
    "$WATCHER_DIR/launcher.py"
    "$WATCHER_DIR/haiku_watcher.py"
    "$WATCHER_DIR/opus_handler.py"
    "$WATCHER_DIR/README.md"
    "$WATCHER_DIR/QUICK_START.md"
)

for file in "${REQUIRED_FILES[@]}"; do
    if [ -f "$file" ]; then
        echo "  ✓ $(basename $file)"
    else
        echo "  ✗ $(basename $file) missing"
        exit 1
    fi
done

# Test 3: Scripts
echo
echo "[3/8] Checking scripts..."
if [ -x "$PROJECT_DIR/scripts/start-watcher.sh" ]; then
    echo "  ✓ start-watcher.sh exists and is executable"
else
    echo "  ✗ start-watcher.sh missing or not executable"
    exit 1
fi

# Test 4: Python syntax
echo
echo "[4/8] Validating Python syntax..."
$PYTHON_CMD -m py_compile "$WATCHER_DIR/launcher.py" 2>/dev/null && echo "  ✓ launcher.py" || (echo "  ✗ launcher.py syntax error" && exit 1)
$PYTHON_CMD -m py_compile "$WATCHER_DIR/haiku_watcher.py" 2>/dev/null && echo "  ✓ haiku_watcher.py" || (echo "  ✗ haiku_watcher.py syntax error" && exit 1)
$PYTHON_CMD -m py_compile "$WATCHER_DIR/opus_handler.py" 2>/dev/null && echo "  ✓ opus_handler.py" || (echo "  ✗ opus_handler.py syntax error" && exit 1)

# Test 5: Configuration structure
echo
echo "[5/8] Checking configuration..."
if grep -q "POLL_INTERVAL" "$WATCHER_DIR/config.py"; then
    echo "  ✓ POLL_INTERVAL defined"
else
    echo "  ✗ POLL_INTERVAL missing"
    exit 1
fi

if grep -q "MAX_RESTART_ATTEMPTS" "$WATCHER_DIR/config.py"; then
    echo "  ✓ MAX_RESTART_ATTEMPTS defined"
else
    echo "  ✗ MAX_RESTART_ATTEMPTS missing"
    exit 1
fi

if grep -q "EXIT_CODE_INTERVENTION_NEEDED" "$WATCHER_DIR/config.py"; then
    echo "  ✓ Exit codes defined"
else
    echo "  ✗ Exit codes missing"
    exit 1
fi

# Test 6: Coordination templates
echo
echo "[6/8] Checking coordination templates..."
if [ -f "$COORD_DIR/status.md.template" ]; then
    echo "  ✓ status.md.template exists"
else
    echo "  ✗ status.md.template missing"
    exit 1
fi

# Test 7: Documentation
echo
echo "[7/8] Checking documentation..."
if [ -s "$WATCHER_DIR/README.md" ]; then
    LINES=$(wc -l < "$WATCHER_DIR/README.md")
    echo "  ✓ README.md exists ($LINES lines)"
else
    echo "  ✗ README.md missing or empty"
    exit 1
fi

# Test 8: Integration report
echo
echo "[8/8] Checking integration report..."
if [ -f "$COORD_DIR/INTEGRATION_COMPLETE.md" ]; then
    echo "  ✓ INTEGRATION_COMPLETE.md exists"
else
    echo "  ✗ INTEGRATION_COMPLETE.md missing"
    exit 1
fi

# Summary
echo
echo "=================================="
echo "All Integration Tests Passed! ✓"
echo "=================================="
echo
echo "Next steps:"
echo "  1. Set ANTHROPIC_API_KEY: export ANTHROPIC_API_KEY='your-key'"
echo "  2. Start watcher: $PROJECT_DIR/scripts/start-watcher.sh"
echo "  3. Monitor logs: tail -f $COORD_DIR/launcher.log"
echo
echo "See watcher/QUICK_START.md for usage guide"
echo "See watcher/README.md for full documentation"
echo
