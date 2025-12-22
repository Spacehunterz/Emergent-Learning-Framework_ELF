```markdown
# Proposal: Investigation Before Re-Attempting Failed Fixes

**Type:** heuristic
**Confidence:** 0.45
**Source Sessions:** [session_2024-12-11.jsonl]
**Domain:** debugging

## Summary
When an initial bug fix attempt fails (tests still failing), pausing to investigate the code flow and search for related patterns before re-attempting leads to successful resolution.

## Evidence
- 13:30 - Initial edit to fix login bug resulted in "Changes applied but tests still failing"
- 14:25 - Read auth.py to understand token flow (150 lines)
- 14:28 - Grep for token validation patterns (found 3 files)
- 14:32 - Second fix attempt succeeded after investigation

The ~55 minute gap between failed fix and investigation, followed by successful fix 7 minutes after investigation, suggests the investigation was the key differentiator.

## Proposed Content
**Rule:** When a fix attempt fails, investigate the code flow and search for related patterns before re-attempting - don't iterate blindly on the same approach
**Explanation:** Failed fixes often indicate incomplete understanding of the system. Reading the relevant code to understand the flow (not just the symptom location) and searching for related patterns reveals context that makes the second attempt more informed and successful.
**When to Apply:** After any fix attempt where tests still fail or the bug persists
**Suggested Confidence:** 0.45

## Cross-References
- May relate to: debugging-read-before-edit heuristics (if exists)
- Validates: general "understand before acting" principle
- Related domain: authentication/token handling patterns

---
**Status:** pending
**Generated:** 2025-12-11T14:35:00Z
**Reviewed:**
```