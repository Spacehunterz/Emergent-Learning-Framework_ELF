# Heuristics: infrastructure

Generated from database recovery on 2025-12-01.

---

## H-54: Always check if dependent services (Ollama, ComfyUI) are running before GPU operations, and auto-launch if not

**Confidence**: 0.9
**Source**: design_decision

RAG queries require Ollama for embeddings/LLM. Voice generation requires ComfyUI. Rather than failing silently or erroring, check availability and launch on demand with wait-for-ready logic. This creates a self-healing system that just works.

---

