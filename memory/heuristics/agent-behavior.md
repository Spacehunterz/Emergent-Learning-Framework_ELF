# Heuristics: agent-behavior

Generated from failures, successes, and observations in the **agent-behavior** domain.

---

## H-0: Execute direct commands immediately

**Confidence**: 0.95
**Source**: failure
**Created**: 2025-12-01

When user gives action commands like close, stop, kill - do it first before anything else

---

## H-0: Always record learnings to the building before ending a diagnostic task

**Confidence**: 0.95
**Source**: user-feedback
**Created**: 2025-12-01

When you diagnose an issue, find a root cause, or learn something new about tools/systems - immediately record it to the building. Do not wait for user to remind you. The building only learns if you teach it.

---

## H-0: Log to building BEFORE giving summary, not after

**Confidence**: 0.95
**Source**: user-feedback
**Created**: 2025-12-01

The correct flow is: complete work → log all learnings to building → THEN summarize for user. Do not give summary first and wait for user to remind you to log. Logging is part of completing the task, not a separate step.

---

