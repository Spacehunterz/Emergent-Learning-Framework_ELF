# Complexity Scoring - Implementation Summary

## Overview
Enhanced `pre_tool_learning.py` with complexity scoring from Context-Engine patterns.

## What Was Added

### 1. ComplexityScorer Class (Lines 72-167)

Analyzes tasks and assigns risk levels based on pattern matching:

**Risk Patterns:**
- **HIGH**: auth files, crypto, security, passwords, tokens, secrets, .env files
- **MEDIUM**: API files, configs, schemas, migrations, databases

**Scoring Logic:**
- Checks file paths/names
- Checks keywords in task descriptions
- Checks identified domains
- Aggregates scores to determine risk level: HIGH, MEDIUM, LOW-MEDIUM, or LOW

### 2. Integration Points

**In main():**
- Line 384: Calls `ComplexityScorer.score()` after domain extraction
- Line 405: Injects complexity warning if level != 'LOW'
- Line 406: Passes complexity to `format_learning_context()`

**In format_learning_context():**
- Lines 314-323: Formats complexity warning at top of injected context
- Uses warning symbols: ⚠️ for HIGH, ⚡ for MEDIUM
- Shows reasons and recommendations

### 3. Domain Enhancements

Added missing high-risk domains to domain detection:
- `database-migration`
- `production`

## Example Outputs

### HIGH Risk Task
```
Input: "Update authentication token validation in auth/security.py"

Injected Context:
---
## Building Knowledge (Auto-Injected)

### Task Complexity: HIGH ⚠️
**Reasons:**
- High-risk keyword: password
- High-risk domain: authentication
- High-risk file pattern: auth
- High-risk file pattern: token
**Recommendation:** Extra scrutiny recommended. Consider CEO escalation if uncertain.

### Golden Rules (Must Follow)
- Query Before Acting
- Document Failures Immediately
...
---
```

### MEDIUM Risk Task
```
Input: "Refactor the API configuration"

Injected Context:
---
## Building Knowledge (Auto-Injected)

### Task Complexity: MEDIUM ⚡
**Reasons:**
- Medium-risk keyword: refactor
- Medium-risk domain: api
- Medium-risk domain: configuration
**Recommendation:** Moderate care required. Review changes and test thoroughly.
---
```

### LOW Risk Task
```
Input: "Add CSS styling to button"

Injected Context:
(No complexity warning shown - goes straight to Golden Rules)
```

## Testing

All tests pass:
- ✓ HIGH risk detection for auth/password/security tasks
- ✓ MEDIUM risk detection for API/config tasks
- ✓ LOW risk (no warning) for routine tasks

## Design Decisions

1. **Advisory Only**: Complexity scoring is non-blocking - warnings only
2. **Pattern Matching**: Uses regex for file patterns, substring matching for keywords
3. **Domain-Aware**: Integrates with existing domain extraction
4. **Score Thresholds**:
   - HIGH: 2+ high-risk points OR 1 high + 3 medium
   - MEDIUM: 1 high OR 3+ medium
   - LOW-MEDIUM: 1+ medium
   - LOW: No matches
5. **File Pattern Flexibility**: Checks both file_path parameters AND task prompt text

## Integration with Learning Loop

The complexity scorer enhances the existing learning loop:
1. Tool call intercepted by hook
2. Domains extracted from context
3. **Complexity scored** (NEW)
4. Heuristics queried from building
5. Recent failures retrieved
6. All context + complexity warning injected into task prompt

This provides agents with both institutional knowledge AND risk awareness before executing tasks.

## Future Enhancements

Potential improvements:
- Machine learning-based scoring using historical failure data
- User-customizable risk patterns
- Integration with CEO inbox for auto-escalation of HIGH-risk tasks
- Tracking: Which complexity warnings prevented failures?
