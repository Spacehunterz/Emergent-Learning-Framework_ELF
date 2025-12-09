# Heuristics: pyqt

Generated from failures, successes, and observations in the **pyqt** domain.

---

## H-106: QTimer operations must be called from Qt main thread. When callbacks come from worker threads (audio, network), emit a pyqtSignal and handle the timer in the connected main thread slot.

**Confidence**: 0.9
**Source**: failure
**Created**: 2025-12-09



---

