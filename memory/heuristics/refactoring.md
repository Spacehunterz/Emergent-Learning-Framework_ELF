# Heuristics: refactoring

Generated from failures, successes, and observations in the **refactoring** domain.

---

## H-96: Check git history when refactoring loses features - use git log -p -S to find removed code

**Confidence**: 0.8
**Source**: observation
**Created**: 2025-12-06

Scrollback buffer was silently dropped during modularization. git log -p -S scrollback found the exact commit where it was lost.

---

