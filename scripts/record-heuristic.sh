#!/bin/bash
# Record a heuristic in the Emergent Learning Framework

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$(dirname "$SCRIPT_DIR")"
MEMORY_DIR="$BASE_DIR/memory"
DB_PATH="$MEMORY_DIR/index.db"
HEURISTICS_DIR="$MEMORY_DIR/heuristics"

# Ensure heuristics directory exists
mkdir -p "$HEURISTICS_DIR"

# Prompt for inputs
echo "=== Record Heuristic ==="
echo ""

read -p "Domain: " domain
if [ -z "$domain" ]; then
    echo "Error: Domain cannot be empty"
    exit 1
fi

read -p "Rule (the heuristic): " rule
if [ -z "$rule" ]; then
    echo "Error: Rule cannot be empty"
    exit 1
fi

read -p "Explanation: " explanation

read -p "Source type (failure/success/observation): " source_type
if [ -z "$source_type" ]; then
    source_type="observation"
fi

read -p "Confidence (0.0-1.0): " confidence
if [ -z "$confidence" ]; then
    confidence="0.5"
fi

# Escape single quotes for SQL injection protection
escape_sql() {
    echo "${1//\'/\'\'}"
}

domain_escaped=$(escape_sql "$domain")
rule_escaped=$(escape_sql "$rule")
explanation_escaped=$(escape_sql "$explanation")
source_type_escaped=$(escape_sql "$source_type")

# Insert into database
sqlite3 "$DB_PATH" <<SQL
INSERT INTO heuristics (domain, rule, explanation, source_type, confidence)
VALUES (
    '$domain_escaped',
    '$rule_escaped',
    '$explanation_escaped',
    '$source_type_escaped',
    $confidence
);
SQL

heuristic_id=$(sqlite3 "$DB_PATH" "SELECT last_insert_rowid();")
echo "Database record created (ID: $heuristic_id)"

# Append to domain markdown file
domain_file="$HEURISTICS_DIR/${domain}.md"

if [ ! -f "$domain_file" ]; then
    cat > "$domain_file" <<EOF
# Heuristics: $domain

Generated from failures, successes, and observations in the **$domain** domain.

---

EOF
fi

cat >> "$domain_file" <<EOF
## H-$heuristic_id: $rule

**Confidence**: $confidence
**Source**: $source_type
**Created**: $(date +%Y-%m-%d)

$explanation

---

EOF

echo "Appended to: $domain_file"

# Git commit
cd "$BASE_DIR"
if [ -d ".git" ]; then
    git add "$domain_file"
    git add "$DB_PATH"
    git commit -m "heuristic: $rule" -m "Domain: $domain | Confidence: $confidence" || echo "No changes to commit"
    echo "Git commit created"
else
    echo "Warning: Not a git repository. Skipping commit."
fi

echo ""
echo "Heuristic recorded successfully!"
