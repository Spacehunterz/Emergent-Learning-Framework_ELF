# Heuristics: python

Generated from failures, successes, and observations in the **python** domain.

---

## H-99: Use keyword arguments for optional parameters to avoid positional mismatch bugs

**Confidence**: 0.7
**Source**: failure
**Created**: 2025-12-07

When calling functions with multiple optional parameters, positional args can silently bind to wrong parameters (e.g., dict to error_message instead of output). Keyword args make intent explicit and prevent type mismatches.

---

