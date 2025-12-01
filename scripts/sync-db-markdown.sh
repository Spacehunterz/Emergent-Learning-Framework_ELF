#!/bin/bash
# Synchronize database and markdown files in the Emergent Learning Framework
#
# Usage: ./sync-db-markdown.sh          # Report only
#        ./sync-db-markdown.sh --fix    # Report and fix issues
#
# Detects and optionally fixes:
# - Orphaned markdown files (exist in filesystem but not in database)
# - Orphaned database records (exist in database but file missing)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$(dirname "$SCRIPT_DIR")"
MEMORY_DIR="$BASE_DIR/memory"
DB_PATH="$MEMORY_DIR/index.db"
HEURISTICS_DIR="$MEMORY_DIR/heuristics"
FAILURES_DIR="$MEMORY_DIR/failures"
SUCCESSES_DIR="$MEMORY_DIR/successes"
LOGS_DIR="$BASE_DIR/logs"

# Setup logging
LOG_FILE="$LOGS_DIR/$(date +%Y%m%d).log"
mkdir -p "$LOGS_DIR"

log() {
    local level="$1"
    shift
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [$level] [sync-db-markdown] $*" >> "$LOG_FILE"
}

# Parse arguments
FIX_MODE=false
VERBOSE=false
while [[ $# -gt 0 ]]; do
    case $1 in
        --fix) FIX_MODE=true; shift ;;
        --verbose|-v) VERBOSE=true; shift ;;
        *) shift ;;
    esac
done

# Counters
ORPHANED_MD_FILES=0
ORPHANED_DB_RECORDS=0
FIXED_MD_FILES=0
FIXED_DB_RECORDS=0

# Pre-flight checks
if [ ! -f "$DB_PATH" ]; then
    echo "ERROR: Database not found: $DB_PATH"
    exit 1
fi

if ! command -v sqlite3 &> /dev/null; then
    echo "ERROR: sqlite3 command not found"
    exit 1
fi

log "INFO" "Starting sync check (fix_mode=$FIX_MODE)"

echo "=============================================="
echo "  Database/Markdown Synchronization Report"
echo "=============================================="
echo ""

# Escape single quotes for SQL
escape_sql() {
    echo "${1//\'/\'\'}"
}

# Parse metadata from failure markdown file - sets global variables
parse_failure_md() {
    local file="$1"

    # Extract title from first heading
    PARSED_TITLE=$(grep -m1 '^# ' "$file" | sed 's/^# //' || echo "Unknown")

    # Extract domain
    PARSED_DOMAIN=$(grep -i '^\*\*Domain\*\*:' "$file" | sed 's/.*: *//' | head -1)
    if [ -z "$PARSED_DOMAIN" ]; then
        PARSED_DOMAIN=$(grep -i '^Domain:' "$file" | sed 's/.*: *//' | head -1)
    fi
    [ -z "$PARSED_DOMAIN" ] && PARSED_DOMAIN="unknown"

    # Extract severity
    PARSED_SEVERITY=$(grep -i '^\*\*Severity\*\*:' "$file" | sed 's/.*: *//' | head -1)
    if [ -z "$PARSED_SEVERITY" ]; then
        PARSED_SEVERITY=$(grep -i '^Severity:' "$file" | sed 's/.*: *//' | head -1)
    fi
    # Convert words to numbers
    case "$PARSED_SEVERITY" in
        [1-5]) ;; # already a number
        low) PARSED_SEVERITY=2 ;;
        medium|Medium) PARSED_SEVERITY=3 ;;
        high|High) PARSED_SEVERITY=4 ;;
        critical|Critical) PARSED_SEVERITY=5 ;;
        *) PARSED_SEVERITY=3 ;;
    esac

    # Extract tags
    PARSED_TAGS=$(grep -i '^\*\*Tags\*\*:' "$file" | sed 's/.*: *//' | head -1)
    if [ -z "$PARSED_TAGS" ]; then
        PARSED_TAGS=$(grep -i '^Tags:' "$file" | sed 's/.*: *//' | head -1)
    fi

    # Extract summary (use title as fallback)
    PARSED_SUMMARY=$(sed -n '/^## Summary/,/^##/p' "$file" 2>/dev/null | grep -v '^##' | head -1 | tr -d '\r\n')
    [ -z "$PARSED_SUMMARY" ] && PARSED_SUMMARY="$PARSED_TITLE"
}

# Check if heuristic file has YAML frontmatter with a rule
has_yaml_rule() {
    local file="$1"
    head -1 "$file" | grep -q '^---$' && grep -q '^rule:' "$file"
}

# Parse YAML heuristic and insert into DB
insert_yaml_heuristic() {
    local file="$1"
    local domain
    domain=$(basename "$file" .md)

    # Override domain if specified in YAML
    local yaml_domain
    yaml_domain=$(grep '^domain:' "$file" | sed 's/domain: *//' | head -1)
    [ -n "$yaml_domain" ] && domain="$yaml_domain"

    local rule
    rule=$(grep '^rule:' "$file" | sed 's/rule: *//')

    local explanation
    explanation=$(grep '^explanation:' "$file" | sed 's/explanation: *//')

    local source_type
    source_type=$(grep '^source_type:' "$file" | sed 's/source_type: *//')
    [ -z "$source_type" ] && source_type="observation"

    local confidence
    confidence=$(grep '^confidence:' "$file" | sed 's/confidence: *//')
    [ -z "$confidence" ] && confidence="0.7"

    # Escape for SQL
    local rule_escaped
    rule_escaped=$(escape_sql "$rule")
    local explanation_escaped
    explanation_escaped=$(escape_sql "$explanation")
    local domain_escaped
    domain_escaped=$(escape_sql "$domain")

    sqlite3 "$DB_PATH" "INSERT INTO heuristics (domain, rule, explanation, source_type, confidence) VALUES ('$domain_escaped', '$rule_escaped', '$explanation_escaped', '$source_type', $confidence);"
    echo 1
}

# Parse markdown heuristic file and insert rules into DB
insert_markdown_heuristics() {
    local file="$1"
    local domain
    domain=$(basename "$file" .md)
    local count=0

    # Find lines that look like rule headings
    while IFS= read -r line; do
        # Match ## H-N: or ## N. patterns
        if echo "$line" | grep -qE '^## (H-[0-9]+:|[0-9]+\.)'; then
            # Extract the rule text from the heading
            local rule
            rule=$(echo "$line" | sed -E 's/^## (H-[0-9]+: ?|[0-9]+\. ?)//')

            # If rule is short, it might be just a title - look for quoted version
            if [ ${#rule} -lt 30 ]; then
                local quoted
                quoted=$(grep -A3 "^${line}" "$file" 2>/dev/null | grep '^>' | head -1 | sed 's/^> *//')
                [ -n "$quoted" ] && rule="$quoted"
            fi

            # Default confidence
            local conf="0.7"

            # Escape for SQL
            local rule_escaped
            rule_escaped=$(escape_sql "$rule")
            local domain_escaped
            domain_escaped=$(escape_sql "$domain")

            sqlite3 "$DB_PATH" "INSERT INTO heuristics (domain, rule, explanation, source_type, confidence) VALUES ('$domain_escaped', '$rule_escaped', '', 'observation', $conf);"
            count=$((count + 1))
        fi
    done < "$file"

    echo $count
}

# ============================================
# PHASE 1: Check for orphaned failure markdown files
# ============================================
echo "--- Failures: Checking for orphaned markdown files ---"

for md_file in "$FAILURES_DIR"/*.md; do
    [ -f "$md_file" ] || continue
    [ "$(basename "$md_file")" = "TEMPLATE.md" ] && continue

    relative_path="memory/failures/$(basename "$md_file")"

    # Check if exists in database
    db_count=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM learnings WHERE filepath='$relative_path'")

    if [ "$db_count" -eq 0 ]; then
        ORPHANED_MD_FILES=$((ORPHANED_MD_FILES + 1))
        echo "  ORPHANED FILE: $relative_path"
        log "INFO" "Found orphaned failure file: $relative_path"

        if [ "$FIX_MODE" = true ]; then
            # Parse metadata from file (sets PARSED_* variables)
            parse_failure_md "$md_file"

            # Insert into database
            title_escaped=$(escape_sql "$PARSED_TITLE")
            summary_escaped=$(escape_sql "$PARSED_SUMMARY")
            tags_escaped=$(escape_sql "$PARSED_TAGS")
            domain_escaped=$(escape_sql "$PARSED_DOMAIN")

            sqlite3 "$DB_PATH" <<SQL
INSERT INTO learnings (type, filepath, title, summary, tags, domain, severity)
VALUES (
    'failure',
    '$relative_path',
    '$title_escaped',
    '$summary_escaped',
    '$tags_escaped',
    '$domain_escaped',
    CAST($PARSED_SEVERITY AS INTEGER)
);
SQL
            echo "    -> FIXED: Added to database"
            log "INFO" "Fixed orphaned failure file: $relative_path"
            FIXED_MD_FILES=$((FIXED_MD_FILES + 1))
        fi
    fi
done

# ============================================
# PHASE 2: Check for orphaned failure database records
# ============================================
echo ""
echo "--- Failures: Checking for orphaned database records ---"

while IFS='|' read -r id filepath title domain severity; do
    # Strip carriage return (Windows line endings)
    severity="${severity%$'\r'}"
    [ -z "$filepath" ] && continue

    full_path="$BASE_DIR/$filepath"

    if [ ! -f "$full_path" ]; then
        ORPHANED_DB_RECORDS=$((ORPHANED_DB_RECORDS + 1))
        echo "  ORPHANED DB RECORD: $filepath (ID: $id)"
        log "INFO" "Found orphaned failure DB record: $filepath"

        if [ "$FIX_MODE" = true ]; then
            # Recreate the file from database data
            mkdir -p "$(dirname "$full_path")"
            cat > "$full_path" <<EOF
# $title

**Domain**: $domain
**Severity**: $severity
**Tags**:
**Date**: $(date +%Y-%m-%d)

## Summary

(Recovered from database - original file was missing)

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
            echo "    -> FIXED: Recreated markdown file"
            log "INFO" "Recreated missing failure file: $filepath"
            FIXED_DB_RECORDS=$((FIXED_DB_RECORDS + 1))
        fi
    fi
done < <(sqlite3 "$DB_PATH" "SELECT id, filepath, title, domain, severity FROM learnings WHERE type='failure'")

# ============================================
# PHASE 3: Check for orphaned heuristic markdown files
# ============================================
echo ""
echo "--- Heuristics: Checking for orphaned markdown files ---"

for md_file in "$HEURISTICS_DIR"/*.md; do
    [ -f "$md_file" ] || continue
    [ "$(basename "$md_file")" = "TEMPLATE.md" ] && continue

    domain=$(basename "$md_file" .md)

    # Check if domain exists in database
    db_count=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM heuristics WHERE domain='$domain'")

    if [ "$db_count" -eq 0 ]; then
        ORPHANED_MD_FILES=$((ORPHANED_MD_FILES + 1))
        echo "  ORPHANED FILE: memory/heuristics/$domain.md (domain not in DB)"
        log "INFO" "Found orphaned heuristic file: $domain.md"

        if [ "$FIX_MODE" = true ]; then
            # Try YAML format first, then markdown format
            if has_yaml_rule "$md_file"; then
                rule_count=$(insert_yaml_heuristic "$md_file")
                echo "    -> FIXED: Added YAML heuristic to database"
                FIXED_MD_FILES=$((FIXED_MD_FILES + 1))
            else
                rule_count=$(insert_markdown_heuristics "$md_file")
                if [ "$rule_count" -gt 0 ]; then
                    echo "    -> FIXED: Added $rule_count heuristics to database"
                    FIXED_MD_FILES=$((FIXED_MD_FILES + 1))
                else
                    echo "    -> SKIPPED: No parseable rules found"
                fi
            fi
            log "INFO" "Fixed orphaned heuristic file: $domain.md"
        fi
    fi
done

# ============================================
# PHASE 4: Check for orphaned heuristic database records
# ============================================
echo ""
echo "--- Heuristics: Checking database domains without files ---"

while IFS= read -r domain; do
    # Strip carriage return (Windows line endings from sqlite3 on Windows)
    domain="${domain%$'\r'}"
    [ -z "$domain" ] && continue

    domain_file="$HEURISTICS_DIR/${domain}.md"

    if [ ! -f "$domain_file" ]; then
        # Count how many rules for this domain
        rule_count=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM heuristics WHERE domain='$domain'")

        ORPHANED_DB_RECORDS=$((ORPHANED_DB_RECORDS + 1))
        echo "  ORPHANED DOMAIN: $domain ($rule_count rules in DB, no file)"
        log "INFO" "Found orphaned heuristic domain: $domain"

        if [ "$FIX_MODE" = true ]; then
            # Recreate the file from database
            cat > "$domain_file" <<EOF
# Heuristics: $domain

Generated from database recovery on $(date +%Y-%m-%d).

---

EOF
            # Add each rule
            while IFS='|' read -r id rule explanation source_type confidence; do
                cat >> "$domain_file" <<EOF
## H-$id: $rule

**Confidence**: $confidence
**Source**: $source_type

$explanation

---

EOF
            done < <(sqlite3 "$DB_PATH" "SELECT id, rule, explanation, source_type, confidence FROM heuristics WHERE domain='$domain'")

            echo "    -> FIXED: Created markdown file with $rule_count rules"
            log "INFO" "Created missing heuristic file: $domain.md"
            FIXED_DB_RECORDS=$((FIXED_DB_RECORDS + 1))
        fi
    fi
done < <(sqlite3 "$DB_PATH" "SELECT DISTINCT domain FROM heuristics ORDER BY domain")

# ============================================
# SUMMARY
# ============================================
echo ""
echo "=============================================="
echo "  Summary"
echo "=============================================="
echo "  Orphaned markdown files (not in DB): $ORPHANED_MD_FILES"
echo "  Orphaned database records (no file): $ORPHANED_DB_RECORDS"
echo ""

if [ "$FIX_MODE" = true ]; then
    echo "  Fixed markdown files:    $FIXED_MD_FILES"
    echo "  Fixed database records:  $FIXED_DB_RECORDS"
    echo ""

    if [ $((FIXED_MD_FILES + FIXED_DB_RECORDS)) -gt 0 ]; then
        echo "  Status: SYNCHRONIZED"
        log "INFO" "Sync completed: fixed $FIXED_MD_FILES files and $FIXED_DB_RECORDS DB records"
    else
        echo "  Status: NO CHANGES NEEDED"
    fi
else
    TOTAL_ISSUES=$((ORPHANED_MD_FILES + ORPHANED_DB_RECORDS))
    if [ "$TOTAL_ISSUES" -gt 0 ]; then
        echo "  Status: OUT OF SYNC ($TOTAL_ISSUES issues)"
        echo ""
        echo "  Run with --fix to synchronize"
    else
        echo "  Status: SYNCHRONIZED"
    fi
fi

log "INFO" "Sync check completed: $ORPHANED_MD_FILES orphaned files, $ORPHANED_DB_RECORDS orphaned records"
echo ""
