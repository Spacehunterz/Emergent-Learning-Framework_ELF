#!/bin/bash
# Record a heuristic in the Emergent Learning Framework
#
# Usage (interactive): ./record-heuristic.sh
# Usage (non-interactive):
#   HEURISTIC_DOMAIN="domain" HEURISTIC_RULE="rule" ./record-heuristic.sh
#   Or: ./record-heuristic.sh --domain "domain" --rule "rule" --explanation "why"
#   Optional: --source failure|success|observation --confidence 0.8

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$(dirname "$SCRIPT_DIR")"
MEMORY_DIR="$BASE_DIR/memory"
DB_PATH="$MEMORY_DIR/index.db"
HEURISTICS_DIR="$MEMORY_DIR/heuristics"

# Ensure heuristics directory exists
mkdir -p "$HEURISTICS_DIR"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --domain) domain="$2"; shift 2 ;;
        --rule) rule="$2"; shift 2 ;;
        --explanation) explanation="$2"; shift 2 ;;
        --source) source_type="$2"; shift 2 ;;
        --confidence) confidence="$2"; shift 2 ;;
        *) shift ;;
    esac
done

# Check for environment variables
domain="${domain:-$HEURISTIC_DOMAIN}"
rule="${rule:-$HEURISTIC_RULE}"
explanation="${explanation:-$HEURISTIC_EXPLANATION}"
source_type="${source_type:-$HEURISTIC_SOURCE}"
confidence="${confidence:-$HEURISTIC_CONFIDENCE}"

# Non-interactive mode: if we have domain and rule, skip prompts
if [ -n "$domain" ] && [ -n "$rule" ]; then
    source_type="${source_type:-observation}"
    # Validate confidence is a number, convert words to numbers
    if [ -z "$confidence" ]; then
        confidence="0.7"
    elif [[ "$confidence" =~ ^[0-9]*\.?[0-9]+$ ]]; then
        # Valid number - keep as-is
        :
    else
        # Invalid (word like "high") - convert or default
        case "$confidence" in
            low) confidence="0.3" ;;
            medium) confidence="0.6" ;;
            high) confidence="0.85" ;;
            *) confidence="0.7" ;; # default for invalid
        esac
    fi
    explanation="${explanation:-}"
    echo "=== Record Heuristic (non-interactive) ==="
else
    # Interactive mode
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
fi

# Escape single quotes for SQL
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
