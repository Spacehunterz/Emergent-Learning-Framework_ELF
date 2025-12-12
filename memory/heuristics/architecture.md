# Heuristics: architecture

Generated from database recovery on 2025-12-01.

---

## H-1: Always escape user input before SQL interpolation

**Confidence**: 0.9
**Source**: failure

Direct string interpolation into SQL queries allows injection attacks. Use parameterized queries or escape special characters like single quotes.

---

## H-2: Keep schema definitions in one authoritative source

**Confidence**: 0.8
**Source**: failure

When multiple files define the same schema (ORM, raw SQL, migration scripts), they will drift. Designate one as source of truth.

---

## H-121: If the task requires judgment, use an agent not a state machine. State machines are for routing, not reasoning. If you're writing 'if keyword in text', you've already failed.

**Confidence**: 0.9
**Source**: failure
**Created**: 2025-12-11

Built 600 lines of keyword-matching Python when 50 lines of Task agent spawning would do. Wasted 100k tokens.

---

