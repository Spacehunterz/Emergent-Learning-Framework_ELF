#!/bin/bash
# Patch to fix filesystem edge case issues
# Addresses: Collision detection and null byte handling
#
# Usage: ./filesystem-edge-case-fixes.sh
# This will create patched versions of the scripts with _patched suffix

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$(dirname "$(dirname "$SCRIPT_DIR")")"
SCRIPTS_DIR="$BASE_DIR/scripts"

echo "Applying filesystem edge case fixes..."
echo ""

# ============================================================
# PATCH 1: record-failure.sh - Add collision detection
# ============================================================

echo "Creating patched version of record-failure.sh..."

# Read the original file
input_file="$SCRIPTS_DIR/record-failure.sh"
output_file="$SCRIPTS_DIR/record-failure-patched.sh"

# Copy original to patched version
cp "$input_file" "$output_file"

# Find the line after "relative_path" assignment (around line 337)
# Add collision detection code

# Create the collision detection code block
collision_code='
# ============================================
# FILESYSTEM EDGE CASE FIX: Collision Detection
# Issue: Case-insensitive filesystems (Windows/macOS) silently overwrite
# Solution: Append counter if file exists
# ============================================
counter=1
while [ -f "$filepath" ]; do
    log "WARN" "File exists: $filename (collision detected)"
    filename="${date_prefix}_${filename_title}_${counter}.md"
    filepath="$FAILURES_DIR/$filename"
    relative_path="memory/failures/$filename"
    ((counter++))

    # Safety limit: prevent infinite loop
    if [ $counter -gt 100 ]; then
        log "ERROR" "Too many collisions for filename: $filename_title"
        echo "ERROR: Too many collisions (>100). Filename may not be unique enough." >&2
        exit 1
    fi
done

log "INFO" "Using filename: $filename"
'

# Insert collision detection code after line 337 (after relative_path assignment)
# Using sed to insert after the relative_path line
sed -i '/^relative_path="memory\/failures\/$filename"$/a\
\
# ============================================\
# FILESYSTEM EDGE CASE FIX: Collision Detection\
# Issue: Case-insensitive filesystems (Windows/macOS) silently overwrite\
# Solution: Append counter if file exists\
# ============================================\
counter=1\
while [ -f "$filepath" ]; do\
    log "WARN" "File exists: $filename (collision detected)"\
    filename="${date_prefix}_${filename_title}_${counter}.md"\
    filepath="$FAILURES_DIR/$filename"\
    relative_path="memory/failures/$filename"\
    ((counter++))\
    \
    # Safety limit: prevent infinite loop\
    if [ $counter -gt 100 ]; then\
        log "ERROR" "Too many collisions for filename: $filename_title"\
        echo "ERROR: Too many collisions (>100). Filename may not be unique enough." >&2\
        exit 1\
    fi\
done\
\
log "INFO" "Using filename: $filename"' "$output_file"

# Add null byte removal before trimming (line 314)
sed -i '/^# Trim leading\/trailing whitespace$/i\
# ============================================\
# FILESYSTEM EDGE CASE FIX: Null Byte Removal\
# Security: Prevent null byte injection\
# ============================================\
title="${title//$'"'"'\\0'"'"'/}"\
domain="${domain//$'"'"'\\0'"'"'/}"\
summary="${summary//$'"'"'\\0'"'"'/}"\
' "$output_file"

echo "✓ Created: $output_file"

# ============================================================
# PATCH 2: record-heuristic.sh - Add collision detection
# ============================================================

echo "Creating patched version of record-heuristic.sh..."

input_file="$SCRIPTS_DIR/record-heuristic.sh"
output_file="$SCRIPTS_DIR/record-heuristic-patched.sh"

# Copy original
cp "$input_file" "$output_file"

# Add collision detection for domain file
sed -i '/^domain_file="\$HEURISTICS_DIR\/\${domain}.md"$/a\
\
# ============================================\
# FILESYSTEM EDGE CASE FIX: Collision Detection\
# For heuristics, we append to existing files, but check for issues\
# ============================================\
if [ -f "$domain_file" ] && [ ! -w "$domain_file" ]; then\
    log "ERROR" "Domain file exists but is not writable: $domain_file"\
    exit 1\
fi' "$output_file"

# Null byte removal already exists in record-heuristic.sh (line 269)
# But add it for other fields too
sed -i '/^# Trim leading\/trailing whitespace$/i\
# FILESYSTEM EDGE CASE FIX: Enhanced null byte removal\
rule="${rule//$'"'"'\\0'"'"'/}"\
explanation="${explanation//$'"'"'\\0'"'"'/}"\
' "$output_file"

echo "✓ Created: $output_file"

# ============================================================
# Verification
# ============================================================

echo ""
echo "Verification:"
echo ""

# Check if patched files exist and are valid bash scripts
if bash -n "$SCRIPTS_DIR/record-failure-patched.sh" 2>/dev/null; then
    echo "✓ record-failure-patched.sh: Valid bash syntax"
else
    echo "✗ record-failure-patched.sh: Syntax error!"
fi

if bash -n "$SCRIPTS_DIR/record-heuristic-patched.sh" 2>/dev/null; then
    echo "✓ record-heuristic-patched.sh: Valid bash syntax"
else
    echo "✗ record-heuristic-patched.sh: Syntax error!"
fi

# Count number of fixes applied
fixes_in_failure=$(grep -c "FILESYSTEM EDGE CASE FIX" "$SCRIPTS_DIR/record-failure-patched.sh" || echo 0)
fixes_in_heuristic=$(grep -c "FILESYSTEM EDGE CASE FIX" "$SCRIPTS_DIR/record-heuristic-patched.sh" || echo 0)

echo ""
echo "Applied fixes:"
echo "  - record-failure.sh: $fixes_in_failure fixes"
echo "  - record-heuristic.sh: $fixes_in_heuristic fixes"

echo ""
echo "============================================================"
echo "PATCH COMPLETE"
echo "============================================================"
echo ""
echo "Patched files created:"
echo "  1. $SCRIPTS_DIR/record-failure-patched.sh"
echo "  2. $SCRIPTS_DIR/record-heuristic-patched.sh"
echo ""
echo "To use the patched versions:"
echo "  mv $SCRIPTS_DIR/record-failure.sh $SCRIPTS_DIR/record-failure-original.sh"
echo "  mv $SCRIPTS_DIR/record-failure-patched.sh $SCRIPTS_DIR/record-failure.sh"
echo ""
echo "  mv $SCRIPTS_DIR/record-heuristic.sh $SCRIPTS_DIR/record-heuristic-original.sh"
echo "  mv $SCRIPTS_DIR/record-heuristic-patched.sh $SCRIPTS_DIR/record-heuristic.sh"
echo ""
echo "Or test the patched versions first by running:"
echo "  FAILURE_TITLE=\"Test\" FAILURE_DOMAIN=\"test\" FAILURE_SEVERITY=3 \\"
echo "  FAILURE_SUMMARY=\"Test\" $SCRIPTS_DIR/record-failure-patched.sh"
echo ""
