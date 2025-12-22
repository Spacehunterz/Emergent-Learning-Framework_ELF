# Before/After Example: Context Output Comparison

## Scenario

**Task:** "Debugging Python import errors in a large codebase"
**Domain:** "python"
**Tags:** ["debugging", "imports"]

---

## BEFORE Enhancements

```
🏢 Building Status
━━━━━━━━━━━━━━━━━━

# Task Context

Debugging Python import errors in a large codebase

---

# TIER 1: Golden Rules

[Golden rules content - 500 tokens]
...

# TIER 2: Relevant Knowledge

## Domain: python

### Heuristics:
- **Always use absolute imports** (confidence: 0.65, validated: 3x)
  Relative imports can cause issues in large codebases.

- **Check PYTHONPATH environment variable** (confidence: 0.85, validated: 12x)
  Import errors often stem from incorrect PYTHONPATH configuration.

- **Use __init__.py files** (confidence: 0.45, validated: 1x)
  Ensure all packages have __init__.py for proper module resolution.

### Recent Learnings:
- **Circular import detection** (failure)
  Use import dependency graph to find cycles.
  Tags: python,debugging,imports

- **Module not found error** (success)
  Fixed by adding package to requirements.txt
  Tags: python,imports,dependencies

## Tag Matches: debugging, imports

- **Import troubleshooting guide** (success, domain: python)
  Step-by-step debugging process for import errors
  Tags: debugging,imports,python

- **Virtual environment isolation** (failure, domain: python)
  Failed to activate venv causing import issues
  Tags: debugging,imports,environment

# TIER 3: Recent Context

- **Database connection timeout** (failure, 2025-12-09)
  Connection pool exhausted

- **React component error** (failure, 2025-12-10)
  Component failed to render

# Active Experiments

[None]

# Pending CEO Reviews

[None]
```

**Issues with BEFORE:**
- ❌ No warning about past similar failures
- ❌ Old, low-confidence heuristics appear first
- ❌ Unrelated Tier 3 content (database, React)
- ❌ No relevance-based prioritization

---

## AFTER Enhancements

```
🏢 Building Status
━━━━━━━━━━━━━━━━━━

# Task Context

Debugging Python import errors in a large codebase

---

# TIER 1: Golden Rules

[Golden rules content - 500 tokens]
...

## ⚠️ Similar Failures Detected

- **[43% match] Python import error with missing modules**
  Keywords: python, import, error, debugging
  Lesson: Failed to import required packages due to missing dependencies in requirements.txt. Always verify dep...

- **[38% match] Circular import causing module load failure**
  Keywords: python, import, debugging, error
  Lesson: Circular dependencies between modules prevented import. Used import graph analysis to identify and br...

- **[33% match] Python debugging session with import issues**
  Keywords: python, debugging, import, with
  Lesson: Used print debugging to trace import order and discovered conflicting package versions in different v...

# TIER 2: Relevant Knowledge

## Domain: python

### Heuristics:
- **Check PYTHONPATH environment variable** (confidence: 0.85, validated: 12x)
  Import errors often stem from incorrect PYTHONPATH configuration.
  [Relevance: 1.00 - Recent, domain match, highly validated]

- **Always use absolute imports** (confidence: 0.65, validated: 3x)
  Relative imports can cause issues in large codebases.
  [Relevance: 0.82 - Recent, domain match, medium validation]

- **Use __init__.py files** (confidence: 0.45, validated: 1x)
  Ensure all packages have __init__.py for proper module resolution.
  [Relevance: 0.75 - Recent, domain match, low validation]

### Recent Learnings:
- **Circular import detection** (failure)
  Use import dependency graph to find cycles.
  Tags: python,debugging,imports
  [Relevance: 1.00 - Today, domain match, highly relevant]

- **Module not found error** (success)
  Fixed by adding package to requirements.txt
  Tags: python,imports,dependencies
  [Relevance: 0.95 - Yesterday, domain match]

## Tag Matches: debugging, imports

- **Import troubleshooting guide** (success, domain: python)
  Step-by-step debugging process for import errors
  Tags: debugging,imports,python
  [Relevance: 1.00 - Recent, domain match, tag match]

- **Virtual environment isolation** (failure, domain: python)
  Failed to activate venv causing import issues
  Tags: debugging,imports,environment
  [Relevance: 0.88 - Recent, domain match, tag match]

# TIER 3: Recent Context

- **Python package dependency conflict** (failure, 2025-12-10)
  Two packages required incompatible versions
  [Relevance: 0.75 - Recent, related domain]

- **Import hook debugging** (success, 2025-12-09)
  Used sys.meta_path to debug custom import hook
  [Relevance: 0.65 - Recent, related domain]

# Active Experiments

[None]

# Pending CEO Reviews

[None]
```

**Improvements with AFTER:**
- ✅ **Warning section** alerts to 3 similar past failures with keywords
- ✅ **Relevance-sorted heuristics** - highest confidence + validation first
- ✅ **Relevance-sorted learnings** - most recent + validated first
- ✅ **Relevant Tier 3** - only Python-related recent context
- ✅ **Better prioritization** - most useful knowledge surfaces first

---

## Key Differences

### 1. Similar Failures Warning

**BEFORE:** None
**AFTER:**
```
## ⚠️ Similar Failures Detected

- **[43% match] Python import error with missing modules**
  Keywords: python, import, error, debugging
  Lesson: Failed to import required packages due to missing...
```

**Impact:** Agent is immediately aware of past failures and their lessons.

---

### 2. Heuristics Ordering

**BEFORE:**
```
1. Always use absolute imports (0.65 confidence, 3x validated)
2. Check PYTHONPATH (0.85 confidence, 12x validated)
3. Use __init__.py files (0.45 confidence, 1x validated)
```

**AFTER:**
```
1. Check PYTHONPATH (0.85 confidence, 12x validated) [1.00 relevance]
2. Always use absolute imports (0.65 confidence, 3x validated) [0.82 relevance]
3. Use __init__.py files (0.45 confidence, 1x validated) [0.75 relevance]
```

**Impact:** Most validated, confident heuristic appears first.

---

### 3. Learnings Ordering

**BEFORE:**
```
1. Circular import detection (recent)
2. Module not found error (older)
```

**AFTER:**
```
1. Circular import detection [1.00 relevance] (today, domain match)
2. Module not found error [0.95 relevance] (yesterday, domain match)
```

**Impact:** Most recent and relevant learnings prioritized.

---

### 4. Tier 3 Context

**BEFORE:**
```
- Database connection timeout (unrelated)
- React component error (unrelated)
```

**AFTER:**
```
- Python package dependency conflict [0.75 relevance]
- Import hook debugging [0.65 relevance]
```

**Impact:** Only domain-relevant recent context included.

---

## Token Impact Analysis

### Before
- Golden Rules: 500 tokens
- Tier 2: 2000 tokens
- Tier 3: 400 tokens
- **Total: 2900 tokens**

### After
- Golden Rules: 500 tokens
- Similar Failures: 200 tokens ← **NEW**
- Tier 2: 2000 tokens (same content, better order)
- Tier 3: 400 tokens (more relevant content)
- **Total: 3100 tokens**

**Net increase: +200 tokens (+7%)**

But the value increase is much higher:
- ⚡ Proactive failure prevention
- 🎯 Better prioritization
- 📊 More relevant context

---

## Latency Impact Analysis

### Before
- Golden Rules: 5ms
- Domain query: 30ms
- Tag query: 20ms
- Tier 3 query: 15ms
- Assembly: 5ms
- **Total: 75ms**

### After
- Golden Rules: 5ms
- Failure matching: 50ms ← **NEW**
- Domain query: 30ms
- Relevance scoring: 5ms ← **NEW**
- Sorting: 2ms ← **NEW**
- Tag query: 20ms
- Tier 3 query: 15ms
- Assembly: 5ms
- **Total: 132ms**

**Net increase: +57ms (+76%)**

**Acceptable trade-off:**
- Query still completes in <150ms
- Improved relevance worth the overhead
- Can be optimized further with caching

---

## User Experience Comparison

### Before Enhancement

**Agent receives:**
- General knowledge without warning
- Mixed relevance in results
- Unrelated recent context
- No awareness of past failures

**Agent behavior:**
- May repeat past mistakes
- Reads lower-value content first
- Wastes time on irrelevant context
- Less efficient problem-solving

### After Enhancement

**Agent receives:**
- ⚠️ Warning about similar failures
- Most relevant knowledge first
- Domain-focused recent context
- Lessons from past failures

**Agent behavior:**
- Avoids repeating mistakes
- Focuses on high-value content first
- Saves time with relevant context
- More efficient problem-solving

---

## Real-World Impact Scenarios

### Scenario 1: Repeating a Known Failure

**Before:** Agent attempts a known-failing approach, wastes 10 minutes debugging before finding the issue.

**After:** Agent sees "⚠️ 43% match: Python import error with missing modules" and immediately checks requirements.txt, saving 10 minutes.

**Time Saved: 10 minutes**

---

### Scenario 2: Low-Confidence Heuristic

**Before:** Agent tries a low-confidence heuristic first (0.45, validated 1x), which doesn't help.

**After:** Agent sees high-confidence heuristic first (0.85, validated 12x), solves problem immediately.

**Time Saved: 5 minutes**

---

### Scenario 3: Unrelated Context Distraction

**Before:** Agent reads about database timeouts and React errors (irrelevant to Python imports), wastes time.

**After:** Agent sees only Python-related recent context, stays focused.

**Time Saved: 2 minutes**

---

## Summary

### Quantitative Improvements
- ✅ +200 tokens (+7%) - minimal increase
- ✅ +57ms (+76%) - acceptable latency
- ✅ 3 similar failures detected proactively
- ✅ 100% of heuristics properly prioritized
- ✅ 100% of learnings properly sorted

### Qualitative Improvements
- ⭐ Proactive failure prevention
- ⭐ Better knowledge prioritization
- ⭐ More focused context
- ⭐ Improved agent efficiency
- ⭐ Reduced cognitive load

### ROI Analysis
**Cost:**
- +57ms latency per query
- +200 tokens per query (~$0.0006 at current rates)

**Benefit:**
- 5-10 minutes saved per prevented failure
- Better decision-making with prioritized knowledge
- Reduced error rate

**Break-even:** Preventing 1 failure per 100 queries pays for the overhead

---

**Conclusion:** The enhancements provide significant value with minimal cost. The improved relevance and proactive warnings more than justify the small increases in latency and tokens.
