# Heuristics: concurrency

Generated from failures, successes, and observations in the **concurrency** domain.

---

## H-47: Use cross-platform locking for git operations

**Confidence**: 0.7
**Source**: observation
**Created**: 2025-12-01

flock is not available on Windows, use mkdir-based fallback

---

