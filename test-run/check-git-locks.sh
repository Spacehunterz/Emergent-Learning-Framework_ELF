#!/bin/bash

BASE_DIR="$HOME/.claude/emergent-learning"
RESULTS_FILE="test-run/git-locks-report.txt"

> "$RESULTS_FILE"

echo "Git Lock Status Report" >> "$RESULTS_FILE"
echo "=====================" >> "$RESULTS_FILE"
echo "Timestamp: $(date)" >> "$RESULTS_FILE"
echo "" >> "$RESULTS_FILE"

echo "Check 1: Lock Files in .git Directory" >> "$RESULTS_FILE"
echo "-------------------------------------" >> "$RESULTS_FILE"
lock_files=$(find "$BASE_DIR/.git" -name "*.lock" -o -name "*.dir" 2>/dev/null)
if [ -z "$lock_files" ]; then
    echo "✓ No .lock files found in .git directory" >> "$RESULTS_FILE"
else
    echo "✗ Lock files detected:" >> "$RESULTS_FILE"
    echo "$lock_files" >> "$RESULTS_FILE"
fi
echo "" >> "$RESULTS_FILE"

echo "Check 2: Git Lock Directories (mkdir-based)" >> "$RESULTS_FILE"
echo "-------------------------------------------" >> "$RESULTS_FILE"
lock_dirs=$(find "$BASE_DIR" -name "*.lock.dir" 2>/dev/null | head -20)
if [ -z "$lock_dirs" ]; then
    echo "✓ No .lock.dir directories found" >> "$RESULTS_FILE"
else
    echo "✗ Lock directories detected:" >> "$RESULTS_FILE"
    echo "$lock_dirs" >> "$RESULTS_FILE"
    echo "" >> "$RESULTS_FILE"
    echo "Details:" >> "$RESULTS_FILE"
    ls -lhR $(echo "$lock_dirs" | head -5) 2>/dev/null >> "$RESULTS_FILE"
fi
echo "" >> "$RESULTS_FILE"

echo "Check 3: Running Processes with record-failure.sh" >> "$RESULTS_FILE"
echo "------------------------------------------------" >> "$RESULTS_FILE"
ps aux | grep record-failure.sh | grep -v grep >> "$RESULTS_FILE" 2>&1 || echo "✓ No record-failure.sh processes running" >> "$RESULTS_FILE"
echo "" >> "$RESULTS_FILE"

echo "Check 4: Git Repository Status" >> "$RESULTS_FILE"
echo "-----------------------------" >> "$RESULTS_FILE"
cd "$BASE_DIR"
git status 2>&1 | head -20 >> "$RESULTS_FILE"
echo "" >> "$RESULTS_FILE"

echo "Check 5: Recent Git Activity (last 5 commits)" >> "$RESULTS_FILE"
echo "-------------------------------------------" >> "$RESULTS_FILE"
git log --oneline -5 >> "$RESULTS_FILE"
echo "" >> "$RESULTS_FILE"

echo "Check 6: Git Index File Status" >> "$RESULTS_FILE"
echo "------------------------------" >> "$RESULTS_FILE"
ls -lh "$BASE_DIR/.git/index" 2>/dev/null | awk '{print "Index file: " $0}' >> "$RESULTS_FILE"
git rev-parse HEAD 2>&1 >> "$RESULTS_FILE"
echo "" >> "$RESULTS_FILE"

cat "$RESULTS_FILE"
