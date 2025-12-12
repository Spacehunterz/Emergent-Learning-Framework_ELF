# Heuristics: react-websocket

Generated from failures, successes, and observations in the **react-websocket** domain.

---

## H-122: useEffect with callback deps causes reconnect loops - use refs for callbacks, empty deps for mount-only effects

**Confidence**: 0.95
**Source**: failure
**Created**: 2025-12-11

React useEffect re-runs when dependencies change. Callbacks like onMessage are new references each render, causing effect to re-run and reconnect WebSocket. Fix: store callback in useRef, update ref in separate effect, use empty [] deps for connection effect.

---

