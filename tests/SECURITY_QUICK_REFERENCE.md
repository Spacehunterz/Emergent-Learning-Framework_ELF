# Filesystem Security Quick Reference
## For Developers

**Last Updated**: 2025-12-01
**Maintained By**: Security Team

---

## BEFORE YOU WRITE CODE

### Security Checklist ✅

When writing code that touches the filesystem:

- [ ] Sanitize ALL user input used in paths
- [ ] Check for symlinks before write operations
- [ ] Check for hardlinks before overwrites
- [ ] Validate numeric inputs with regex
- [ ] Escape SQL strings
- [ ] Quote all shell variables
- [ ] Use absolute paths only
- [ ] Set restrictive permissions (600/700)
- [ ] Log security events
- [ ] Fail securely (exit on errors)

---

## COMMON VULNERABILITIES

### 🔴 Path Traversal
**Bad**:
```bash
domain="$USER_INPUT"
file="$HEURISTICS_DIR/${domain}.md"
```

**Good**:
```bash
domain=$(echo "$USER_INPUT" | tr -cd '[:alnum:]-')
domain="${domain:0:100}"
file="$HEURISTICS_DIR/${domain}.md"
```

### 🔴 Symlink Race (TOCTOU)
**Bad**:
```bash
if [ -L "$dir" ]; then exit 1; fi
# ... later ...
cat > "$dir/file.txt"
```

**Good**:
```bash
if [ -L "$dir" ]; then exit 1; fi
# ... later ...
if [ -L "$dir" ]; then exit 1; fi  # Re-check!
cat > "$dir/file.txt"
```

### 🔴 Hardlink Attack
**Bad**:
```bash
cat > "$existing_file.md" <<EOF
Confidential data
EOF
```

**Good**:
```bash
link_count=$(stat -c '%h' "$existing_file.md" 2>/dev/null || echo "1")
if [ "$link_count" -gt 1 ]; then exit 1; fi
cat > "$existing_file.md" <<EOF
Confidential data
EOF
```

### 🔴 SQL Injection
**Bad**:
```bash
sqlite3 db.db "INSERT INTO table VALUES ('$user_input')"
```

**Good**:
```bash
user_input_escaped="${user_input//\'/\'\'}"
sqlite3 db.db "INSERT INTO table VALUES ('$user_input_escaped')"
```

### 🔴 Command Injection
**Bad**:
```bash
filename=$user_input
cat > $filename  # No quotes!
```

**Good**:
```bash
filename=$(sanitize "$user_input")
cat > "$filename"  # Quoted!
```

---

## SECURITY LIBRARY

Located at: `scripts/lib/security.sh`

### Available Functions

```bash
# Source the library
source "$SCRIPT_DIR/lib/security.sh"

# Sanitize filename (alphanumeric, dash, underscore, dot only)
clean_name=$(sanitize_filename "$user_input")

# Sanitize domain (alphanumeric and dash only)
clean_domain=$(sanitize_domain "$user_input")

# Validate integer in range
if validate_integer "$value" 1 5; then
    echo "Valid"
fi

# Validate decimal number
if validate_decimal "$value" 0.0 1.0; then
    echo "Valid"
fi

# Escape SQL string
escaped=$(escape_sql "$user_string")

# Check if path is within allowed directory
if validate_path "$filepath" "$base_dir"; then
    echo "Safe"
fi

# Check for symlinks in path
if is_symlink_in_path "$filepath"; then
    echo "DANGER: Symlink detected"
    exit 6
fi

# Check for hardlink attack
if ! check_hardlink_attack "$filepath"; then
    echo "DANGER: Hardlink detected"
    exit 6
fi

# Safe directory creation
safe_mkdir "$directory"

# Check disk space (KB)
if ! check_disk_space "$directory" 1024; then
    echo "Insufficient disk space"
    exit 4
fi
```

---

## SECURE PATTERNS

### Pattern 1: User Input in Filename

```bash
#!/bin/bash
source "$(dirname "$0")/lib/security.sh"

user_title="$1"

# Sanitize
safe_title=$(sanitize_filename "$user_title")
if [ -z "$safe_title" ]; then
    echo "ERROR: Invalid title" >&2
    exit 1
fi

# Create file
filepath="$OUTPUT_DIR/${safe_title}.md"

# Check directory
if is_symlink_in_path "$OUTPUT_DIR"; then
    echo "ERROR: Directory is symlink" >&2
    exit 6
fi

# Check for hardlinks
if ! check_hardlink_attack "$filepath"; then
    echo "ERROR: Hardlink detected" >&2
    exit 6
fi

# Write file
cat > "$filepath" <<EOF
Content here
EOF
```

### Pattern 2: Database Insert

```bash
#!/bin/bash
source "$(dirname "$0")/lib/security.sh"

title="$1"
severity="$2"

# Validate integer
if ! validate_integer "$severity" 1 5; then
    echo "ERROR: Invalid severity" >&2
    exit 1
fi

# Escape string
title_escaped=$(escape_sql "$title")

# Insert
sqlite3 db.db <<SQL
INSERT INTO table (title, severity)
VALUES ('$title_escaped', CAST($severity AS INTEGER));
SQL
```

### Pattern 3: Safe File Overwrite

```bash
#!/bin/bash
source "$(dirname "$0")/lib/security.sh"

filepath="$1"
content="$2"

# Check directory is not symlink
if is_symlink_in_path "$(dirname "$filepath")"; then
    echo "ERROR: Directory is symlink" >&2
    exit 6
fi

# Check file for hardlinks
if [ -f "$filepath" ] && ! check_hardlink_attack "$filepath"; then
    echo "ERROR: File has hardlinks" >&2
    exit 6
fi

# Write to temp file first (atomic)
temp_file="${filepath}.tmp.$$"
echo "$content" > "$temp_file"
chmod 600 "$temp_file"

# Move atomically
mv "$temp_file" "$filepath"
```

---

## TESTING YOUR CODE

### Manual Security Tests

```bash
# Test 1: Path traversal
YOUR_INPUT="../../../tmp/evil" bash your_script.sh
# Expected: Input sanitized, no file in /tmp/

# Test 2: Null bytes
YOUR_INPUT="test%00.sh" bash your_script.sh
# Expected: Null bytes removed, creates test00sh not test.sh

# Test 3: SQL injection
YOUR_INPUT="'; DROP TABLE users; --" bash your_script.sh
# Expected: Quotes escaped, no SQL injection

# Test 4: Long input
YOUR_INPUT=$(python -c "print('A' * 1000)") bash your_script.sh
# Expected: Input truncated or rejected
```

### Automated Tests

```bash
# Run security test suite
cd ~/.claude/emergent-learning
bash tests/advanced_security_tests.sh
```

---

## INCIDENT RESPONSE

### If You Discover a Vulnerability

1. **DO NOT commit the vulnerable code**
2. **Immediately notify security team**
3. **Create POC exploit** (in tests/ directory)
4. **Develop fix** (follow patterns above)
5. **Verify fix blocks exploit**
6. **Document in building memory**:
   ```bash
   FAILURE_TITLE="[Vulnerability description]"
   FAILURE_DOMAIN="security"
   FAILURE_SEVERITY="critical"
   bash scripts/record-failure.sh
   ```

### If You Find an Exploit

**DO**:
- Report it immediately
- Document the exploit
- Propose a fix

**DON'T**:
- Use it maliciously
- Share it publicly
- Commit vulnerable code

---

## EXIT CODES

Use these semantic exit codes:

```bash
0  - Success
1  - Input validation error
2  - Database error
3  - Git error
4  - Filesystem error
5  - Missing dependency
6  - Security error (symlink, hardlink, etc.)
7  - Data validation error
8  - Lock acquisition error
```

Example:
```bash
if is_symlink_in_path "$dir"; then
    log "ERROR" "SECURITY: Symlink detected"
    exit 6  # Security error
fi
```

---

## LOGGING SECURITY EVENTS

Always log security failures:

```bash
log() {
    echo "[$(date)] $*" >> "$LOG_FILE"
    echo "$*" >&2  # Also to stderr
}

if [ -L "$dir" ]; then
    log "SECURITY: Symlink attack detected: $dir"
    log "SECURITY: User: $USER, Input: $input"
    exit 6
fi
```

---

## RESOURCES

### Documentation
- Full Audit: `tests/SECURITY_AUDIT_FINAL_REPORT.md`
- Verification: `tests/VERIFICATION_RESULTS.md`
- Agent Report: `tests/AGENT_B_FINAL_REPORT.md`

### Code
- Security Library: `scripts/lib/security.sh`
- Test Suite: `tests/advanced_security_tests.sh`
- Patches: `tests/patches/`

### Examples
- Look at `scripts/record-failure.sh` for secure patterns
- Look at `scripts/record-heuristic.sh` for sanitization examples

---

## QUICK WINS

### 5-Minute Security Improvements

1. **Sanitize all filenames**:
   ```bash
   filename=$(echo "$input" | tr -cd '[:alnum:]-_.')
   ```

2. **Quote all variables**:
   ```bash
   cat > "$file"  # Not: cat > $file
   ```

3. **Validate numbers**:
   ```bash
   if ! [[ "$num" =~ ^[0-9]+$ ]]; then exit 1; fi
   ```

4. **Escape SQL**:
   ```bash
   escaped="${input//\'/\'\'}"
   ```

5. **Check symlinks**:
   ```bash
   if [ -L "$dir" ]; then exit 6; fi
   ```

---

## GOLDEN RULES

1. **Never trust user input**
2. **Whitelist, don't blacklist**
3. **Fail securely, never silently**
4. **Check twice, write once** (TOCTOU)
5. **Defense in depth** (multiple layers)
6. **Log security events**
7. **Quote everything**
8. **Absolute paths only**
9. **Test with exploits**
10. **Document vulnerabilities**

---

## GET HELP

- Review: Security audit reports in `tests/`
- Ask: Building memory has security heuristics
- Test: Run `bash tests/advanced_security_tests.sh`
- Escalate: Critical issues go to `ceo-inbox/`

---

**Remember**: Security is not a feature, it's a requirement.

**Updated**: 2025-12-01 by Opus Agent B
