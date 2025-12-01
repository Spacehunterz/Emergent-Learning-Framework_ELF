
---
## Heavy Operations on Mouse Release

**Rule:** Defer heavy operations to mouse release, not during drag

**Explanation:** When implementing drag-to-resize or similar interactions that require expensive operations (reloading thousands of video frames), do NOT execute during mouseMoveEvent - it causes UI freezes and crashes. Instead: (1) Show lightweight preview during drag (silhouette outline, scaled placeholder), (2) Execute heavy operation on mouseReleaseEvent, (3) Show loading indicator during processing.

**Source:** data_overlay session 2025-11-30 - crashed multiple times before learning this
**Confidence:** 0.9
**Domain:** ui-interaction, pyqt, real-time
