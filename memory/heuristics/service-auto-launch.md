---
domain: infrastructure
rule: Always check if dependent services (Ollama, ComfyUI) are running before GPU operations, and auto-launch if not
explanation: RAG queries require Ollama for embeddings/LLM. Voice generation requires ComfyUI. Rather than failing silently or erroring, check availability and launch on demand with wait-for-ready logic. This creates a self-healing system that just works.
source_type: design_decision
confidence: 0.9
tags: services,ollama,comfyui,automation,infrastructure
---
