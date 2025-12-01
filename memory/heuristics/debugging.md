# Heuristics: debugging

Generated from failures, successes, and observations in the **debugging** domain.

---

## H-0: Verify file existence before assuming tool bugs

**Confidence**: 0.85
**Source**: diagnostic-testing
**Created**: 2025-12-01

When Read/Edit/Write tools fail, first check if the path is correct and file exists. In this case, golden-rules/README.md didn't exist - the actual file was memory/golden-rules.md. The 'tool tracking issue' was a secondary finding, not the root cause.

---

