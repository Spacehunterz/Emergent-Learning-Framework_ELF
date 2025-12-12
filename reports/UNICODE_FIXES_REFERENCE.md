# Unicode & Encoding Fixes - Quick Reference

## Files to Modify

1. `/c~/.claude/emergent-learning/scripts/record-failure.sh`
2. `/c~/.claude/emergent-learning/scripts/record-heuristic.sh`

---

## Fix 1: Filename Length Truncation

**Location:** Both scripts, around line 196-198

**Current Code:**
```bash
filename_title=$(echo "$title" | tr '[:upper:]' '[:lower:]' | tr ' ' '-' | tr -cd '[:alnum:]-')
filename="${date_prefix}_${filename_title}.md"
```

**Fixed Code:**
```bash
filename_title=$(echo "$title" | tr '[:upper:]' '[:lower:]' | tr ' ' '-' | tr -cd '[:alnum:]-')

# Truncate to 200 chars max (filesystem limit is usually 255)
filename_title="${filename_title:0:200}"

filename="${date_prefix}_${filename_title}.md"
```

---

## Fix 2: Empty Filename Fallback

**Location:** Both scripts, same location as Fix 1

**Current Code:**
```bash
filename_title=$(echo "$title" | tr '[:upper:]' '[:lower:]' | tr ' ' '-' | tr -cd '[:alnum:]-')
filename="${date_prefix}_${filename_title}.md"
```

**Fixed Code:**
```bash
filename_title=$(echo "$title" | tr '[:upper:]' '[:lower:]' | tr ' ' '-' | tr -cd '[:alnum:]-')

# If all chars were stripped, generate hash-based name
if [ -z "$filename_title" ]; then
    filename_title="special-$(echo -n "$title" | md5sum | cut -c1-8)"
fi

# Truncate to 200 chars max
filename_title="${filename_title:0:200}"

filename="${date_prefix}_${filename_title}.md"
```

---

## Fix 3: Newline Sanitization

**Location:** Both scripts, around line 202-210 (before writing to file)

**record-failure.sh - Current Code:**
```bash
# Create markdown file
cat > "$filepath" <<EOF
# $title

**Domain**: $domain
**Severity**: $severity
**Tags**: $tags
**Date**: $(date +%Y-%m-%d)
EOF
```

**record-failure.sh - Fixed Code:**
```bash
# Sanitize title for display (remove newlines, tabs, control chars)
title_display=$(echo "$title" | tr '\n\r\t' ' ' | tr -s ' ')

# Create markdown file
cat > "$filepath" <<EOF
# $title_display

**Domain**: $domain
**Severity**: $severity
**Tags**: $tags
**Date**: $(date +%Y-%m-%d)
EOF
```

**record-heuristic.sh - Current Code:**
```bash
cat >> "$heuristic_file" <<EOF

---

## H-${id}: $rule

**Confidence**: $confidence
**Source**: $source_type
**Created**: $(date +%Y-%m-%d)

$explanation
EOF
```

**record-heuristic.sh - Fixed Code:**
```bash
# Sanitize rule for display
rule_display=$(echo "$rule" | tr '\n\r\t' ' ' | tr -s ' ')
explanation_display=$(echo "$explanation" | tr '\r' ' ')

cat >> "$heuristic_file" <<EOF

---

## H-${id}: $rule_display

**Confidence**: $confidence
**Source**: $source_type
**Created**: $(date +%Y-%m-%d)

$explanation_display
EOF
```

---

## Combined Fix (Recommended)

Add helper functions at the top of both scripts (after the `log()` function):

```bash
# Sanitize filename from title
sanitize_filename() {
    local title="$1"
    local filename_title

    # Convert to lowercase, replace spaces, remove special chars
    filename_title=$(echo "$title" | tr '[:upper:]' '[:lower:]' | tr ' ' '-' | tr -cd '[:alnum:]-')

    # If empty after sanitization, use hash
    if [ -z "$filename_title" ]; then
        filename_title="special-$(echo -n "$title" | md5sum | cut -c1-8)"
    fi

    # Truncate to max 200 chars
    filename_title="${filename_title:0:200}"

    echo "$filename_title"
}

# Sanitize title for display (remove control chars)
sanitize_display() {
    local text="$1"
    echo "$text" | tr '\n\r\t' ' ' | tr -s ' '
}
```

Then use them:

```bash
# Generate filename
filename_title=$(sanitize_filename "$title")
filename="${date_prefix}_${filename_title}.md"

# Sanitize for display
title_display=$(sanitize_display "$title")

# Use $title_display in markdown headers
```

---

## Test Cases to Verify Fixes

After applying fixes, test with:

```bash
# Test 1: Long title
bash record-failure.sh --title "$(printf 'A%.0s' {1..600})" --domain "test"

# Test 2: Special chars only
bash record-failure.sh --title "!@#$%^&*()" --domain "test"

# Test 3: Newline in title
bash record-failure.sh --title "Line 1
Line 2" --domain "test"
```

All should succeed without errors and create valid markdown files.

---

## Priority

**CRITICAL** - These fixes prevent:
1. Filesystem errors (crashes)
2. Unusable filenames (makes files hard to find)
3. Broken markdown (parsing errors)

Implement before production use with user-generated titles.
