# Success: Blackboard Race Condition Fix Design

**Date:** 2025-12-08
**Domain:** coordination, architecture, multi-agent
**Significance:** 5
**Tags:** blackboard, race-conditions, event-log, event-sourcing, migration

## What Worked
Parallel swarm analysis (4 agents: Skeptic, Researcher, Architect, Implementer) to design fix for blackboard race conditions.

## Key Findings

### From Skeptic (Validation)
- Append-only doesn't magically fix races
- Windows file append NOT atomic through Python's POSIX layer
- Need checksums for crash recovery
- Current blackboard already has lock-free reads

### From Researcher (Prior Art)
- Atomic append guaranteed up to 1KB on both platforms
- Windows: Use FILE_APPEND_DATA directly
- Unix: Use O_APPEND flag
- JSONL format - corrupted line only affects that record
- Snapshot + event replay is industry standard

### From Architect (Design)
- 70x faster writes (3ms vs 211ms)
- 100+ agent scalability vs 5 agent limit
- Monotonic sequence numbers fix cursor skew
- Compaction every 10K events or 24 hours

### From Implementer (Migration)
- 4-phase dual-write migration
- Zero API changes
- Rollback capability at every phase
- 6-week implementation timeline

## The Fix

Replace mutable blackboard.json with:
1. events.jsonl (append-only, JSONL format)
2. Periodic snapshots for fast reconstruction
3. Platform-specific atomic append (FILE_APPEND_DATA / O_APPEND)
4. Monotonic sequence numbers instead of timestamps

## Race Conditions Addressed
1. TOCTOU in claim_task - Append-only eliminates check-then-act
2. Partial JSON reads - Newline is atomicity boundary
3. Zombie agents - Heartbeat events + reaper
4. Lock contention - O_APPEND = lock-free writes
5. Unbounded growth - Snapshot compaction
6. Cursor skew - Monotonic sequence numbers

## Heuristics Extracted
> Event log atomicity requires platform-specific code - Python file append mode is NOT atomic on Windows

> Dual-write migration pattern enables safe transitions - old system stays source of truth until validated

## Related
- blackboard.py - current implementation
- 20251208_parallel-swarm-async-analysis.md - stigmergic coordination insight
