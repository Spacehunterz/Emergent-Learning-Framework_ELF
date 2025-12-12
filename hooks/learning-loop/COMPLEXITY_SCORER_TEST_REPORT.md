# ComplexityScorer Core Logic Test Report

**Date:** 2025-12-11
**Component:** `pre_tool_learning.py` - ComplexityScorer class
**Test Suite:** Core functionality + edge cases
**Overall Result:** 6/7 core tests PASS; 2 blockers found

---

## Executive Summary

The ComplexityScorer core logic is functional but contains a critical bug in scoring weights. Keyword and file pattern detection work correctly, but domain-based detection is underweighted, causing some HIGH-risk operations to be classified as MEDIUM risk.

**Test Results:**
- Core functionality: PASS (6/7 tests)
- Edge cases: BLOCKER (2 issues found)
- Recommended action: Fix domain weighting (line 132)

---

## Test Results: Core Tests (7 Total)

### Test 1: Auth Keyword + Domain
**Status:** PASS

**Input:**
```python
score('Task', {'prompt': 'Update authentication system'}, ['authentication'])
```

**Expected:** HIGH
**Got:** HIGH
**Reasons:** `['High-risk file pattern: auth', 'High-risk domain: authentication', 'Medium-risk keyword: update']`

---

### Test 2: Password Keyword Detection
**Status:** PASS

**Input:**
```python
score('Task', {'prompt': 'Handle password reset'}, [])
```

**Expected:** HIGH
**Got:** HIGH
**Reasons:** `['High-risk file pattern: password', 'High-risk keyword: password']`

---

### Test 3: Crypto File Pattern
**Status:** PASS

**Input:**
```python
score('Read', {'file_path': '/crypto.py'}, [])
```

**Expected:** HIGH
**Got:** HIGH
**Reasons:** `['High-risk file pattern: crypto']`

---

### Test 4: API Domain (MEDIUM Risk)
**Status:** PASS

**Input:**
```python
score('Task', {'prompt': 'Update endpoint'}, ['api'])
```

**Expected:** MEDIUM or LOW
**Got:** LOW-MEDIUM
**Reasons:** `['Medium-risk keyword: update', 'Medium-risk domain: api']`

---

### Test 5: README Documentation (LOW Risk)
**Status:** PASS

**Input:**
```python
score('Read', {'file_path': 'README.md'}, [])
```

**Expected:** LOW
**Got:** LOW
**Reasons:** `[]`

---

### Test 6: Reasons Field Population
**Status:** PASS

**Input:**
```python
score('Task', {'prompt': 'Delete user credentials', 'description': 'security'}, ['security'])
```

**Expected:** len(reasons) > 0
**Got:** 4 reasons: `['High-risk file pattern: password', 'High-risk keyword: credential', 'High-risk domain: security']`

---

### Test 7: Recommendation Field
**Status:** PASS

**Input:** Any HIGH/MEDIUM risk task
**Expected:** 'recommendation' field present
**Got:** Always present with appropriate text

---

## Blockers Found (2 Critical Issues)

### Blocker 1: Production Domain Underscored

**Severity:** HIGH
**File:** `/c~/.claude/emergent-learning/hooks/learning-loop/pre_tool_learning.py`
**Line:** 132

**Issue:**
```python
# Current code (WRONG):
for domain in cls.HIGH_RISK_PATTERNS['domains']:
    if domain in domains:
        high_score += 1  # Only +1 point!
```

Production is marked as HIGH-risk domain but only scores +1 point. The threshold for HIGH level is `>= 2`, so domain-only detection fails.

**Evidence:**
```
Input: score('Task', {'prompt': 'Deploy'}, ['production'])
Expected: HIGH
Got: MEDIUM (score = 1, needs 2 for HIGH)
```

**Fix:**
```python
high_score += 2  # Match file/keyword weighting
```

---

### Blocker 2: Database-Migration Domain Underscored

**Severity:** HIGH
**Root Cause:** Same as Blocker 1

**Evidence:**
```
Input: score('Task', {'prompt': 'Run migrations'}, ['database-migration'])
Expected: HIGH
Got: MEDIUM
```

---

## Edge Cases and Findings

### Finding 1: Asymmetric Risk Weighting

**Problem:**
- Files: +2 points per match
- Keywords: +2 points per match
- Domains: +1 point per match (**INCONSISTENT**)

**Impact:**
- Explicit keywords/files are twice as valuable as domain detection
- Domain-only detection cannot reach HIGH level independently
- Deployment to production requires additional risk factor

### Finding 2: Score Accumulation Without Bounds

**Observation:**
```
Input: "rm -rf /auth/crypto/token.py --force" with ['security', 'authentication']
Result: 7 reasons detected, score > 10 points
```

**Problem:** No scaling or capping means HIGH and "VERY HIGH" are indistinguishable.

### Finding 3: Keyword False Positives

**Problem:** MEDIUM-risk keywords include 'change' and 'update', which are extremely common.

**Example:**
```
"Deploy changes" -> MEDIUM risk just from 'change' keyword
"Update config" -> MEDIUM risk just from 'update' keyword
```

---

## Scoring Logic Overview

### HIGH-Risk Patterns

**Files:** auth, crypto, security, password, token, secret, .env
- Each match: +2 points

**Keywords:** delete, drop, truncate, force, sudo, rm -rf, password, credential
- Each match: +2 points

**Domains:** authentication, security, database-migration, production
- Each match: +1 point (SHOULD BE +2)

### MEDIUM-Risk Patterns

**Files:** api, config, schema, migration, database
- Each match: +1 point

**Keywords:** update, modify, change, refactor, migrate
- Each match: +1 point

**Domains:** api, configuration, database
- Each match: +1 point

### Risk Level Thresholds

```python
if high_score >= 2:
    level = 'HIGH'
elif high_score >= 1 or medium_score >= 3:
    level = 'MEDIUM'
elif medium_score >= 1:
    level = 'LOW-MEDIUM'
else:
    level = 'LOW'
```

---

## Test Coverage Assessment

### Covered
- Keyword detection (password, crypto, etc.)
- Domain detection (authentication, api, security)
- File path patterns (.env, secret, token)
- All risk levels (HIGH, MEDIUM, LOW-MEDIUM, LOW)
- Reason generation
- Recommendation field presence
- Case insensitivity

### Not Covered (Opportunities)
- Score accumulation limits
- Multiple domain combinations
- Tool-specific input parsing (Bash, Edit, Write, etc.)
- Performance with very long text inputs
- Regex pattern edge cases
- Threshold boundary testing

---

## Recommendations (Priority Order)

### Priority 1: Fix Domain Weighting (CRITICAL)
Change line 132 from `+1` to `+2` to match file/keyword weighting.

### Priority 2: Review MEDIUM-Risk Keywords
Consider moving 'update' and 'change' to a neutral category or requiring 2+ medium factors instead of 1.

### Priority 3: Add Score Capping
Prevent accumulation beyond meaningful distinction. Suggest:
- Cap HIGH score at 5 (don't accumulate beyond HIGH level)
- Or introduce CRITICAL level for 5+ factors

### Priority 4: Expand Test Coverage
- Test all tool types (Bash, Edit, Write, Grep, Read, Glob)
- Test score boundary conditions
- Test performance with large inputs

---

## Files Involved

**Main file:** `/c~/.claude/emergent-learning/hooks/learning-loop/pre_tool_learning.py`
**Affected class:** `ComplexityScorer` (lines 72-170)
**Specific line:** 132 (domain weighting)

---

## Conclusion

ComplexityScorer is functional for basic risk detection but has a weighting bug that reduces effectiveness for domain-only detection. The fix is simple (change one number) but important for correct operation of the learning loop's complexity assessment system.
