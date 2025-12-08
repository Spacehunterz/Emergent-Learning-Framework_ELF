# UI Click Offset Bug Pattern

**Heuristic:** When handling clicks in overlays/layered UI, content area starts AFTER borders. Use overlay.y + 1 for content start, not overlay.y.

**Why:** Off-by-one errors in click detection cause wrong elements to be selected.

**Source:** claudex settings click detection fix
**Confidence:** 0.7
**Created:** 2025-12-02
