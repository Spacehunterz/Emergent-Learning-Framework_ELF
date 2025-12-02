#!/bin/bash
# Verify database integrity after stress test

DB_PATH="$HOME/.claude/emergent-learning/memory/index.db"
RESULTS_FILE="test-run/db-integrity-results.txt"

> "$RESULTS_FILE"

echo "Database Integrity Verification Report" >> "$RESULTS_FILE"
echo "=======================================" >> "$RESULTS_FILE"
echo "" >> "$RESULTS_FILE"

# Check 1: Database exists and is accessible
echo "Check 1: Database File Status" >> "$RESULTS_FILE"
echo "-----------------------------" >> "$RESULTS_FILE"
if [ -f "$DB_PATH" ]; then
    echo "✓ Database file exists: $DB_PATH" >> "$RESULTS_FILE"
    ls -lh "$DB_PATH" >> "$RESULTS_FILE"
else
    echo "✗ Database file NOT found" >> "$RESULTS_FILE"
fi
echo "" >> "$RESULTS_FILE"

# Check 2: Run SQLite integrity check
echo "Check 2: SQLite Integrity Check" >> "$RESULTS_FILE"
echo "-------------------------------" >> "$RESULTS_FILE"
integrity_result=$(sqlite3 "$DB_PATH" "PRAGMA integrity_check" 2>&1)
echo "Result: $integrity_result" >> "$RESULTS_FILE"
echo "" >> "$RESULTS_FILE"

# Check 3: Count records in learnings table
echo "Check 3: Records in Database" >> "$RESULTS_FILE"
echo "----------------------------" >> "$RESULTS_FILE"
total_records=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM learnings" 2>&1)
echo "Total records in learnings table: $total_records" >> "$RESULTS_FILE"
echo "" >> "$RESULTS_FILE"

# Check 4: Count our stress test records
echo "Check 4: Stress Test Records" >> "$RESULTS_FILE"
echo "----------------------------" >> "$RESULTS_FILE"
stress_records=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM learnings WHERE domain='testing' AND title LIKE 'Stress Test Failure%'" 2>&1)
echo "Records with domain='testing' and title like 'Stress Test Failure': $stress_records" >> "$RESULTS_FILE"
echo "" >> "$RESULTS_FILE"

# Check 5: Show sample records
echo "Check 5: Sample Stress Test Records (first 3)" >> "$RESULTS_FILE"
echo "---------------------------------------------" >> "$RESULTS_FILE"
sqlite3 "$DB_PATH" <<EOF >> "$RESULTS_FILE"
SELECT id, domain, title, severity, created_at FROM learnings 
WHERE domain='testing' AND title LIKE 'Stress Test Failure%'
ORDER BY id DESC
LIMIT 3;
