# Heuristics: tools

Generated from failures, successes, and observations in the **tools** domain.

---

## H-0: Use Write/Edit tools instead of bash echo/cat for file creation when you need to edit the file later in the same session

**Confidence**: 0.9
**Source**: diagnostic-testing
**Created**: 2025-12-01

Claude Code tracks file state internally. Files created by bash are not tracked, causing Edit tool to fail with 'unexpectedly modified' error. Read tool works fine on bash-created files, but Edit requires internal state sync.

---

