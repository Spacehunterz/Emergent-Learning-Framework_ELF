# Failure Analysis: ComplexityScorer Domain Scoring Bug

**Date:** 2025-12-11
**Context:** Testing ComplexityScorer.score() core logic in pre_tool_learning.py
**Component:** Emergent Learning Framework - Learning Loop Hook
**Severity:** HIGH

---

## What Went Wrong

ComplexityScorer fails to correctly classify HIGH-risk operations when the risk comes from domain detection only (without explicit keywords or files).

### Specific Failure Case
```python
# Test: Production domain should trigger HIGH risk
score('Task', {'prompt': 'Deploy'}, ['production'])

# Expected: {'level': 'HIGH', ...}
# Got: {'level': 'MEDIUM', 'reasons': ['High-risk domain: production'], ...}
```

### Root Cause

The scoring logic has **asymmetric weighting**:

**Lines 119-128 (Files and Keywords):**
```python
# Files: +2 points each match
for pattern in cls.HIGH_RISK_PATTERNS['files']:
    if re.search(pattern, file_paths_lower) or re.search(pattern, text_lower):
        high_score += 2  # <-- +2 points

# Keywords: +2 points each match
for keyword in cls.HIGH_RISK_PATTERNS['keywords']:
    if keyword in text_lower:
        high_score += 2  # <-- +2 points
```

**Lines 130-133 (Domains - THE BUG):**
```python
# Domains: +1 point each match (INCONSISTENT!)
for domain in cls.HIGH_RISK_PATTERNS['domains']:
    if domain in domains:
        high_score += 1  # <-- +1 point (INCONSISTENT!)
        reasons.append(f"High-risk domain: {domain}")
```

**Threshold (Line 153):**
```python
if high_score >= 2:
    level = 'HIGH'
```

**Impact:** HIGH-risk domains are marked as HIGH-risk but only contribute +1 to the score. This requires a second risk factor to reach the HIGH threshold of 2 points.

---

## What Should Have Happened

All HIGH-risk patterns (files, keywords, and domains) should add the same weight to the score:

```python
for domain in cls.HIGH_RISK_PATTERNS['domains']:
    if domain in domains:
        high_score += 2  # Match file/keyword weighting
        reasons.append(f"High-risk domain: {domain}")
```

---

## Affected Operations

These HIGH-risk domains are incorrectly classified as MEDIUM:

1. **production** - Production deployment tasks (only +1 score)
2. **database-migration** - Schema migrations (only +1 score)
3. **authentication** - Auth system updates (only +1 score)
4. **security** - Security-related work (only +1 score)

### Evidence
```
"Deploy" + ['production'] domain      -> MEDIUM (expected HIGH)
"Run migrations" + ['database-migration'] -> MEDIUM (expected HIGH)
"Update auth" + ['authentication']    -> MEDIUM (expected HIGH)
```

---

## Lesson Learned

**Pattern Consistency Rule:**
When marking patterns as HIGH-risk, MEDIUM-risk, or LOW-risk, ensure all patterns in the same category contribute equally to the score. Asymmetric weighting creates false negatives where classified-HIGH patterns fail to achieve HIGH scoring.

---

## Related Findings (During Edge Case Testing)

1. **MEDIUM-risk keywords too broad**
   - Keywords 'change' and 'update' appear in almost any deployment task
   - Causes high false-positive rate for routine work
   - Example: "Deploy changes" scores MEDIUM just from 'change' keyword

2. **Score accumulation without bounds**
   - Multiple risk factors accumulate without scaling
   - Example: "rm -rf /auth/crypto/token.py --force" generates 7 reasons
   - No distinction between "HIGH" and "VERY HIGH"

---

## Recommended Fix

**File:** `/c/Users/Evede/.claude/emergent-learning/hooks/learning-loop/pre_tool_learning.py`
**Line:** 132

**Change from:**
```python
high_score += 1
```

**Change to:**
```python
high_score += 2
```

---

## Test Coverage

**Core Tests Status:**
- Test 1 (Auth keyword): PASS
- Test 2 (Password keyword): PASS
- Test 3 (Crypto file): PASS
- Test 4 (API domain): PASS
- Test 5 (README): PASS
- Test 6 (Reasons populated): PASS
- Test 7 (Recommendation field): PASS

**Blockers Found During Edge Case Testing:**
- Blocker 1: Production domain underscored (this failure)
- Blocker 2: Database-migration domain underscored (same root cause)

---

## Proposed Golden Rule

**"Pattern Classification Consistency"**

When classifying risk patterns into tiers (HIGH, MEDIUM, LOW), ensure all patterns in the same tier contribute the same weight to the score. Asymmetric weighting between pattern types (files vs. keywords vs. domains) creates inconsistent risk levels and false negatives.
