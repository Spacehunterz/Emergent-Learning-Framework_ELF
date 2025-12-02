#!/bin/bash
DB_PATH="$HOME/.claude/emergent-learning/memory/index.db"

# Test FK
echo "Testing FK..."
result=$(sqlite3 "$DB_PATH" "PRAGMA foreign_keys=ON; PRAGMA foreign_keys")
echo "Result: $result"
if [ "$result" = "1" ]; then
    echo "PASS"
else
    echo "FAIL"
fi
