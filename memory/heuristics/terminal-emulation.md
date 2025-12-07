# Heuristics: terminal-emulation

Generated from failures, successes, and observations in the **terminal-emulation** domain.

---

## H-98: Lazy Wrap Principle: Cursor wrap should be deferred (phantom cursor at index width) until a printable character needs placement, not triggered eagerly on reaching the boundary. Control codes like CR should execute BEFORE any pending wrap.

**Confidence**: 0.95
**Source**: success
**Created**: 2025-12-07

Eager wrap causes text flooding with spinners because CR goes to next line. Phantom cursor waits to see if next input is printable (then wrap) or control code (execute on current line). This matches VT100/xterm behavior.

---

