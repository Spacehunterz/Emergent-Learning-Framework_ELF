# Advisory Verifier Pattern Coverage Test Report

**Date:** 2025-12-11
**Component:** AdvisoryVerifier in `hooks/learning-loop/post_tool_learning.py`
**Test Focus:** All 9 security advisory patterns

---

## FINDINGS

### [FACT] All 9 Core Patterns Working Correctly

All advisory patterns in the AdvisoryVerifier class are functioning as designed:

**Code Injection Patterns (6 patterns):**
1. `eval()` - Detects `eval\s*\(` - WORKING
2. `exec()` - Detects `exec\s*\(` - WORKING
3. `shell=True` - Detects `subprocess.*shell\s*=\s*True` - WORKING
4. Hardcoded password - Detects assignment patterns with quoted values - WORKING
5. Hardcoded API key - Detects `api[_-]?key` assignments - WORKING
6. SQL injection - Detects `SELECT.*\+.*user` string concatenation - WORKING

**File Operations Patterns (3 patterns):**
7. `rm -rf /` - Detects dangerous recursive deletes - WORKING
8. `chmod 777` - Detects overly permissive permissions - WORKING
9. `> /etc/` - Detects writes to system config directories - WORKING

**Test Result:** 9/9 patterns pass core detection tests

---

### [BLOCKER] Comment Lines Trigger False Positives

**Issue:** Risky patterns in comments are flagged as warnings

**Evidence:**
```python
# eval() is dangerous here  → TRIGGERS WARNING (should not)
```

**Root Cause:** The regex patterns don't exclude comments. The `_get_added_lines()` method splits by newlines and checks against the full line, including comment syntax.

**Impact:** Low-to-moderate. Users may see advisory warnings on documentation/discussion of security issues.

**Expected Behavior:** Comments should either be:
- Excluded entirely from analysis
- Or explicitly allowed if they're just documentation

---

### [BLOCKER] Password Detection Has False Negative

**Issue:** Password strings without assignment syntax are not detected

**Evidence:**
```python
print("password: admin")  → NO WARNING (should trigger)
```

**Root Cause:** The password pattern requires assignment syntax (`=` or `:` with proper spacing):
```regex
["\']?password["\']?\s*[:=]\s*["\'][^"\']+["\']
```

This matches: `password = "secret"` and `password: "secret"`
This misses: `"password: admin"` in function arguments

**Impact:** Moderate. String literals containing "password:" in different contexts aren't caught.

**Recommendation:** Consider pattern variations for password strings in arguments, logging, etc.

---

### [FACT] Pattern Category System is Clean

The verifier properly categorizes warnings:
- **Code** - 6 patterns (code injection, secrets, injection attacks)
- **File Operations** - 3 patterns (dangerous file/permissions operations)

Each warning includes:
- Category label
- Human-readable message
- Line preview (first 80 chars)

---

### [FACT] Advisory Recommendation System Works

The verifier provides graduated recommendations based on warning count:

| Warnings | Recommendation |
|----------|----------------|
| 0 | "No concerns detected." |
| 1-2 | "[!] Review flagged items before proceeding" |
| 3+ | "[!] Multiple concerns - consider CEO escalation" |

This is appropriate for an advisory-only system that never blocks.

---

### [FACT] Added Lines Detection Works

The `_get_added_lines()` method correctly identifies new code:
- Old lines: `x = 5\ny = 10`
- New lines: `x = 5\ny = 10\neval(user_input)`
- Result: Only `eval(user_input)` triggers warning

This prevents false alarms on pre-existing risky code.

---

### [HYPOTHESIS] Missing Pattern Categories

The current 9 patterns may not cover these attack vectors:

**Potentially Missing Patterns:**
1. **Insecure deserialization** - `pickle.loads()`, `json.loads()` from untrusted sources
2. **Weak cryptography** - `MD5`, `SHA1` for passwords, weak random
3. **Path traversal** - `os.path.join()` with user input without validation
4. **LDAP injection** - LDAP query concatenation patterns
5. **Command injection in os.system()** - Already catches `rm -rf /` but not generic patterns
6. **XXE (XML External Entity)** - `xml.etree.ElementTree.parse()` without DTD protection
7. **Unvalidated redirects** - Redirect functions with user-controlled URLs
8. **Hardcoded secrets in other formats** - Docker env vars, .env files, etc.
9. **Unsafe file permissions in code** - `open(..., mode='w')` on system paths
10. **Request timeouts** - `requests.get()` without timeout argument

**Why Not Included:** These would require more sophisticated pattern matching or context-aware analysis beyond simple regex.

---

## EDGE CASES TESTED

**Passing:**
- Case insensitivity: `EVAL(x)` detected
- Whitespace flexibility: `eval  (  x  )` detected
- API key variations: `api_key = "sk_abc123"` detected
- Binary comparison: Clean code (`x = 5`) produces no warnings
- False positive prevention: "error handling" discussion doesn't trigger error detector

**Failing:**
- Comments with risky code trigger warnings (false positive)
- Password strings without assignment syntax missed (false negative)

---

## CODE LOCATION

File: `C:\Users\Evede\.claude\emergent-learning\hooks\learning-loop\post_tool_learning.py`

**AdvisoryVerifier Class:**
- Lines 57-102: Core class and pattern definitions
- Lines 66-88: `analyze_edit()` method
- Lines 90-101: Helper methods

**Pattern Definitions:**
- Lines 40-54: `RISKY_PATTERNS` dictionary with all 9 patterns

---

## RECOMMENDATIONS

### Priority 1: Fix Comment False Positives
Add logic to skip lines that are pure comments:
```python
def _is_comment_only(line: str) -> bool:
    stripped = line.strip()
    return stripped.startswith('#')
```

### Priority 2: Extend Password Detection
Enhance pattern to catch password strings in various contexts:
```regex
["\']?password["\']?\s*[:=]\s*["\'][^"\']+["\']  # Current
|                                                  # OR
["\'].*password:?\s*[^"\']*["\']                 # In quoted strings
```

### Priority 3: Document Pattern Limitations
Create a patterns reference guide explaining:
- What each pattern detects and why
- Known false positives/negatives
- Examples of detected and non-detected code
- When to escalate to CEO if patterns seem insufficient

---

## SUMMARY

**Pattern Coverage Status:** 9/9 patterns functional
**Overall Reliability:** High (with noted edge cases)
**Philosophy:** Advisory-only, human-decides approach is sound
**False Positives:** Low (only comments)
**False Negatives:** Moderate (context-dependent secrets missed)

The AdvisoryVerifier successfully implements an advisory system that warns about risky patterns without blocking operations. Minor improvements to comment handling and secret detection would increase reliability.
