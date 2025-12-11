# Heuristics: process-management

Generated from failures, successes, and observations in the **process-management** domain.

---

## H-119: Verify process termination by checking actual state, not command exit codes

**Confidence**: 0.8
**Source**: failure
**Created**: 2025-12-10

taskkill and similar commands may report success but fail to terminate processes. Always verify by checking netstat/tasklist/ps after killing. User observation trumps tool output - if user says it's still running, trust them and verify.

---

