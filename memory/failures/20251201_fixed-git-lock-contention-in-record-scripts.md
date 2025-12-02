# Fixed git lock contention in record scripts

**Domain**: fix
**Severity**: 1
**Tags**: git,concurrency,fix,success
**Date**: 2025-12-01  # TIME-FIX-3: Use consistent captured date

## Summary

Changed git lock timeout from 30s to 5s. Made lock failure non-fatal - if lock cannot be acquired, data is still saved to DB and file, git commit skipped with warning. Fixes 20-30% failure rate under concurrent load. Applied to both record-failure.sh and record-heuristic.sh.

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
