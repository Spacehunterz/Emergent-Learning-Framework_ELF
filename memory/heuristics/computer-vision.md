# Heuristics: computer-vision

Generated from failures, successes, and observations in the **computer-vision** domain.

---

## H-0: Chroma key edge cleanup requires three-step morphology: erode, dilate, blur

**Confidence**: 0.85
**Source**: success
**Created**: 2025-11-30

When removing color-keyed backgrounds (green screen), simply setting alpha based on color thresholds leaves colored fringes at edges. The fix: (1) Erode the mask to shrink green pixels inward, (2) dilate to restore size but with cleaner edges, (3) blur the alpha channel for feathering. Also reduce the threshold from 80 to 50 to catch more green while letting erosion clean up false positives.

---

