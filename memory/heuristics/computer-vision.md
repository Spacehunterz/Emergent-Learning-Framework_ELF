# Heuristics: computer-vision

Generated from failures, successes, and observations in the **computer-vision** domain.

---

## H-0: Chroma key edge cleanup requires three-step morphology: erode, dilate, blur

**Confidence**: 0.85
**Source**: success
**Created**: 2025-11-30

When removing color-keyed backgrounds (green screen), simply setting alpha based on color thresholds leaves colored fringes at edges. The fix: (1) Erode the mask to shrink green pixels inward, (2) dilate to restore size but with cleaner edges, (3) blur the alpha channel for feathering. Also reduce the threshold from 80 to 50 to catch more green while letting erosion clean up false positives.

---

## H-0: Lip sync blending region must start below nose, not overlapping it

**Confidence**: 0.80
**Source**: success
**Created**: 2025-11-30

When blending mouth frames for lip-sync, starting the blend region too high (y_start = h * 0.62) causes nose artifacts because the nose moves slightly with mouth-opening expressions in source videos. Moving y_start to h * 0.70 ensures only lips and jaw are affected. This is especially critical with frame blending since subtle differences between positions get magnified at blend boundaries.

---

