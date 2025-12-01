---
domain: infrastructure
tags: vram,gpu,coordination,file-locking,services
created: 2025-11-30
source: coordinated-agent-review
---

# Session Heuristics: VRAM + RAG Pipeline

## H-10: File Write Safety with Active Hooks
**Rule:** Kill or pause file-watching processes before editing watched files
**Explanation:** Voice hooks were modifying tts_provider.py during edits, causing race conditions. The file changed between read and write operations, failing silently.
**Confidence:** 0.85
**Tags:** file-safety, hooks, coordination

## H-11: Cross-Platform File Locking Early
**Rule:** Implement platform-specific locks (msvcrt/fcntl) before multi-writer integration
**Explanation:** Windows and Unix locking are incompatible. Design for contention from the start, not after conflicts appear.
**Confidence:** 0.8
**Tags:** cross-platform, file-locking, ipc

## H-12: Service Health Checks Before GPU Operations
**Rule:** Probe service availability first, launch if missing, wait for ready - never attempt GPU ops blindly
**Explanation:** RAG needs Ollama, voice needs ComfyUI. Health checks are cheap; GPU operations are expensive. User validated this pattern.
**Confidence:** 0.9
**Tags:** services, health-checks, gpu, reliability

## H-13: File-Based IPC for Local Coordination
**Rule:** For local multi-process GPU coordination, file-based IPC (JSON + locks) is simpler than sockets/queues
**Explanation:** No daemon needed, debuggable (human-readable), works across tools, survives restarts. Trade-off: slower, suitable for second-scale ops.
**Confidence:** 0.85
**Tags:** ipc, coordination, state-management

## H-14: Priority-Based Resource Preemption
**Rule:** Assign explicit priorities to competing GPU workloads; lower-priority waits rather than competes
**Explanation:** RAG gets priority over voice. Voice checks if RAG active, waits with timeout. Avoids contention, OOM, complex queues.
**Confidence:** 0.85
**Tags:** gpu, vram, prioritization
