# Heuristics: Service Coordination

Generated from VRAM Manager + RAG Pipeline development (2025-11-30).

---

## H-13: Always check dependent services BEFORE attempting operations that require them

> Probe service availability (health checks, port binding) before expensive GPU operations. Fail fast with clear diagnostics rather than timeout/crash.

**Explanation:** RAG queries require Ollama for embeddings, voice generation requires ComfyUI. Early design attempted to call these blindly and catch errors. User feedback pointed out the pattern: check first, launch if missing, wait for readiness. This creates self-healing systems. Service availability checks are cheap (single API call or port probe); GPU operations are expensive. Inverting the order (check → launch → wait → operate) prevents wasted resources and provides better UX.

**Source**: Session design decisions - VRAM Manager + RAG integration, user suggestion during implementation review

**Confidence**: 0.9

**Validations**: 2 (implemented successfully, user validated the pattern)

**Tags**: services, health-checks, reliability, gpu, ollama, comfyui, rag

---

## H-14: Use file-based IPC for cross-process coordination on constrained systems

> When coordinating GPU access between unrelated processes (RAG client, voice service, etc.), file-based IPC (locks + state files) is simpler than sockets/queues if all processes run locally.

**Explanation:** VRAM Manager uses simple file-based coordination: `~/.claude/services/vram_state.json` with file locking. Considered RabbitMQ, Redis, Unix sockets. File approach wins because: (1) no additional daemon required, (2) debuggable (just read the file), (3) works across Python/bash/external tools, (4) state survives restarts. Downside: slower than in-memory coordination, not suitable for high-frequency access. But for VRAM management (operations take seconds), it's ideal.

**Source**: Session design decisions - VRAM Manager architecture choice

**Confidence**: 0.85

**Validations**: 1 (implemented successfully, not yet stress-tested at scale)

**Tags**: ipc, coordination, file-based, state-management, vram, gpu

---
