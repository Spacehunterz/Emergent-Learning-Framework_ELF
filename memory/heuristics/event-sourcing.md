# Event Sourcing Heuristics

**Domain:** architecture, coordination
**Confidence:** 0.9
**Validations:** 1

## Core Heuristics

### Append-only logs eliminate race conditions
> Mutable state requires locks. Append-only requires only atomic append (O_APPEND).

**Why:** Check-then-act races disappear when you can only add, never modify.

### Platform-specific atomic append is required
> Python file append mode is NOT atomic on Windows through POSIX layer.

**Why:** Must use FILE_APPEND_DATA on Windows, O_APPEND on Unix directly.

### Keep events under 1KB for guaranteed atomicity
> Both Windows and Unix guarantee atomic writes up to ~1KB.

**Why:** Larger writes may be split, causing partial/corrupted records.

### Checksums enable crash recovery
> Append checksum to each line, skip lines with bad checksums on read.

**Why:** Crash mid-write corrupts only that line, not entire file.

### Dual-write migration enables safe transitions
> Write to both old and new systems, read from old, validate parity, then switch.

**Why:** Rollback is trivial - just revert the import.

### State = f(events) via replay
> Current state is always reconstructible by replaying all events.

**Why:** Enables time travel debugging, audit trails, and recovery.

## Anti-Patterns

- Reading and rewriting entire state file (race-prone)
- Using timestamps instead of sequence numbers (clock skew)
- Unbounded event files without compaction
