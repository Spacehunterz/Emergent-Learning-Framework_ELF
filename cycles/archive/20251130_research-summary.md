# Research Summary: Session 2025-11-30

**Agent**: Researcher
**Session Focus**: Extract transferable heuristics from VRAM Manager + RAG Pipeline development
**Date**: 2025-11-30
**Status**: Complete

---

## Session Context

Today's engineering focused on three interconnected systems:
1. **VRAM Manager** - GPU resource coordination between RAG and voice workloads
2. **RAG Query Pipeline** - Semantic search with embeddings via Ollama
3. **Service Auto-Launch** - Health checks and startup logic for Ollama/ComfyUI

Key challenges that became teachable moments:
- File write conflicts (multiple processes modifying tts_provider.py)
- ComfyUI batch file execution on MSYS (subprocess compatibility)
- GPU workload prioritization under resource constraints
- Cross-process coordination patterns

---

## Heuristics Extracted (5 Total)

### H-10: Avoid editing files with active hooks or background processes
**Domain**: File Write Safety
**Confidence**: 0.85
**Key Insight**: When multiple processes modify the same file, stale state is inevitable without re-reads before critical edits. Implement file-level coordination early.

### H-11: Use platform-specific file locking early
**Domain**: File Write Safety
**Confidence**: 0.8
**Key Insight**: Windows (msvcrt) and Unix (fcntl) have incompatible locking mechanisms. Assume file contention in multi-writer scenarios and implement platform-specific locks from design phase, not as retrofits.

### H-12: Batch file execution on Windows requires special handling
**Domain**: File Write Safety
**Confidence**: 0.75
**Key Insight**: ComfyUI portable (.bat files) cannot run directly via subprocess on MSYS. Requires `cmd /c wrapper` or explicit shell context. Pure Python packages (Ollama) work fine without this workaround.

### H-13: Always check dependent services BEFORE attempting operations
**Domain**: Service Coordination
**Confidence**: 0.9
**Key Insight**: Health checks are cheap; GPU operations are expensive. Check service availability first, launch if missing, wait for readiness. Creates self-healing systems. User feedback validated this pattern during review.

### H-14: Use file-based IPC for cross-process coordination
**Domain**: Service Coordination
**Confidence**: 0.85
**Key Insight**: For local multi-process coordination with constrained resources, simple file-based IPC (JSON state + locks) beats queues/sockets. Debuggable, requires no daemon, works across Python/bash/external tools. Trade-off: slower than in-memory, suitable for second-scale operations.

### H-15: Implement priority-based resource preemption
**Domain**: GPU Resource Patterns
**Confidence**: 0.85
**Key Insight**: Explicit priorities (RAG > voice) with state-based signaling avoids contention. Make lower-priority work wait rather than fail. Deterministic, simple, debuggable.

---

## Files Created

All heuristics recorded in:
- `~/.claude/emergent-learning/memory/heuristics/file-write-safety.md` (H-10, H-11, H-12)
- `~/.claude/emergent-learning/memory/heuristics/service-coordination.md` (H-13, H-14)
- `~/.claude/emergent-learning/memory/heuristics/gpu-resource-patterns.md` (H-15)

---

## Validation Status

| Heuristic | Validations | Status |
|-----------|-------------|--------|
| H-10 | 1 (incident observed) | Needs production testing |
| H-11 | 1 (designed, not deployed) | Ready for implementation |
| H-12 | 1 (observed, workaround documented) | Needs broader Windows testing |
| H-13 | 2 (implemented + user feedback) | Production-ready |
| H-14 | 1 (implemented, not stress-tested) | Ready for scale testing |
| H-15 | 2 (implemented + test suite) | Production-ready |

---

## Recommendations for Future Sessions

1. **File Write Safety**: Monitor multi-writer scenarios. When confidence reaches 0.9+, document platform-specific examples (Windows path format, Unix symlinks).

2. **Service Coordination**: H-13 and H-14 are solid. Consider extracting a sub-heuristic on timeout strategies for service waits.

3. **GPU Patterns**: H-15 validated but only for single RTX 5090. If scaling to multi-GPU or multi-machine, revisit preemption strategy.

4. **Cross-Platform Testing**: H-12 (batch files) should be validated on:
   - Pure cmd.exe (not MSYS)
   - PowerShell
   - GitHub Actions / CI environments

---

## Notes for CEO

All heuristics documented and indexed. No escalations needed. High confidence (0.8+) on 4/5 heuristics. Ready to build on this foundation for next session's multi-agent coordination work.
