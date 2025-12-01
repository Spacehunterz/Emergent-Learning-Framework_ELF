# Heuristics: error-handling

Generated from failures, successes, and observations in the **error-handling** domain.

---

## H-45: Use pre-flight checks before critical operations

**Confidence**: 0.9
**Source**: observation
**Created**: 2025-12-01

Pre-flight validation prevents cascading failures

---

## H-46: Use portable locking for cross-platform scripts

**Confidence**: 0.95
**Source**: failure
**Created**: 2025-12-01

flock is not available on Windows; use file-based locking instead

---

