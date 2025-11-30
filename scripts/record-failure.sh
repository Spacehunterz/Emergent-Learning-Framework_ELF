#!/bin/bash
# Record a failure in the Emergent Learning Framework

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$(dirname "$SCRIPT_DIR")"
MEMORY_DIR="$BASE_DIR/memory"
DB_PATH="$MEMORY_DIR/index.db"
FAILURES_DIR="$MEMORY_DIR/failures"

# Ensure failures directory exists
mkdir -p "$FAILURES_DIR"

# Prompt for inputs
echo "=== Record Failure ==="
echo ""

read -p "Title: " title
if [ -z "$title" ]; then
    echo "Error: Title cannot be empty"
    exit 1
fi

read -p "Domain (coordination/architecture/debugging/etc): " domain
if [ -z "$domain" ]; then
    echo "Error: Domain cannot be empty"
    exit 1
fi

read -p "Severity (1-5): " severity
if [ -z "$severity" ]; then
    severity=3
fi

read -p "Tags (comma-separated): " tags

echo "Summary (press Enter twice when done):"
summary=""
while IFS= read -r line; do
    [ -z "$line" ] && break
    summary="${summary}${line}\n"
done

# Generate filename
date_prefix=$(date +%Y%m%d)
filename_title=$(echo "$title" | tr '[:upper:]' '[:lower:]' | tr ' ' '-' | tr -cd '[:alnum:]-')
filename="${date_prefix}_${filename_title}.md"
filepath="$FAILURES_DIR/$filename"
relative_path="memory/failures/$filename"

# Create markdown file
cat > "$filepath" <<EOF
# $title

**Domain**: $domain
**Severity**: $severity
**Tags**: $tags
**Date**: $(date +%Y-%m-%d)

## Summary

$summary

## What Happened

[Describe the failure in detail]

## Root Cause

[What was the underlying issue?]

## Impact

[What were the consequences?]

## Prevention

[What heuristic or practice would prevent this?]

## Related

- **Experiments**:
- **Heuristics**:
- **Similar Failures**:
EOF

echo "Created: $filepath"

# Escape single quotes for SQL injection protection
escape_sql() {
    echo "${1//\'/\'\'}"
}

title_escaped=$(escape_sql "$title")
summary_escaped=$(escape_sql "$(echo -e "$summary" | head -n 1)")
tags_escaped=$(escape_sql "$tags")
domain_escaped=$(escape_sql "$domain")

# Insert into database
sqlite3 "$DB_PATH" <<SQL
INSERT INTO learnings (type, filepath, title, summary, tags, domain, severity)
VALUES (
    'failure',
    '$relative_path',
    '$title_escaped',
    '$summary_escaped',
    '$tags_escaped',
    '$domain_escaped',
    $severity
);
SQL

echo "Database record created (ID: $(sqlite3 "$DB_PATH" "SELECT last_insert_rowid();"))"

# Git commit
cd "$BASE_DIR"
if [ -d ".git" ]; then
    git add "$filepath"
    git add "$DB_PATH"
    git commit -m "failure: $title" -m "Domain: $domain | Severity: $severity" || echo "No changes to commit"
    echo "Git commit created"
else
    echo "Warning: Not a git repository. Skipping commit."
fi

echo ""
echo "Failure recorded successfully!"
echo "Edit the full details at: $filepath"
