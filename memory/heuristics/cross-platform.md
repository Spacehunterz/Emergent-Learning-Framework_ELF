# Heuristics: cross-platform

Generated from failures, successes, and observations in the **cross-platform** domain.

---

## H-48: Use mkdir-based locking for cross-platform scripts

**Confidence**: 0.95
**Source**: failure
**Created**: 2025-12-01

mkdir is atomic on all platforms; flock is not available on Windows

---

