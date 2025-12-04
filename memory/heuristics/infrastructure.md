# Heuristics: infrastructure

Generated from database recovery on 2025-12-01.

---

## H-54: Always check if dependent services (Ollama, ComfyUI) are running before GPU operations, and auto-launch if not

**Confidence**: 0.9
**Source**: design_decision

RAG queries require Ollama for embeddings/LLM. Voice generation requires ComfyUI. Rather than failing silently or erroring, check availability and launch on demand with wait-for-ready logic. This creates a self-healing system that just works.

---

## H-90: Check existing infrastructure before building new - you likely already have what you need

**Confidence**: 0.85
**Source**: observation
**Created**: 2025-12-04  # TIME-FIX-2: Use consistent date

Built SQLite FTS5 search for swarm plugin, then discovered Basic Memory already had ChromaDB + embeddings. Wasted effort. Always audit existing tools first.

---

