# Heuristics: GPU Resource Patterns

Generated from VRAM Manager + RAG Pipeline development (2025-11-30).

---

## H-15: Implement priority-based resource preemption for competing GPU workloads

> When multiple workloads compete for limited VRAM (RAG embeddings, voice generation), establish explicit priority: assign high-priority work exclusive access during its operation, and make lower-priority work wait rather than fail.

**Explanation:** RTX 5090 has 32GB VRAM, but concurrent RAG + voice generation would require splitting allocation. Design decision: RAG gets priority (knowledge retrieval > speech synthesis). Voice operations check if RAG is active; if so, they wait (with timeout). This avoids resource contention, unnecessary CUDA out-of-memory errors, and queue management complexity. Pattern: (1) Define priorities based on user impact, (2) Use file-based state to signal active operations, (3) Waiting process polls state with backoff, (4) Set reasonable timeouts. Benefit: simple, deterministic, debuggable.

**Source**: Session design decision - VRAM Manager priority system, architectural review

**Confidence**: 0.85

**Validations**: 2 (implemented successfully, test suite validated concurrent behavior)

**Tags**: gpu, vram, resource-management, prioritization, coordination, rag, voice

---
