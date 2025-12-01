---
title: VRAM Management + RAG Pipeline Complete
type: success
domain: infrastructure
tags: vram,rag,voice,coordination,gpu,embeddings
severity: 5
---

# VRAM Management + RAG Pipeline Complete

## Summary
Built complete GPU resource coordination system for RTX 5090 (32GB) that manages VRAM between:
- Premium RAG pipeline (embeddings via Ollama nomic-embed-text)
- ChatterBox voice generation (ComfyUI)

## Components Built
1. **VRAM Manager** (`~/.claude/services/vram_manager.py`)
   - File-based IPC for cross-process coordination
   - RAG-first priority (voice waits for RAG)
   - Service auto-launch (Ollama)
   - CLI for status/testing

2. **RAG Query Pipeline** (`~/.claude/emergent-learning/query/rag_query.py`)
   - SQL pre-filter by domain/tags
   - Ollama embeddings (nomic-embed-text, 768 dims)
   - Vector similarity search
   - Cross-encoder re-ranking (optional)
   - Embedding cache in SQLite

3. **Voice Integration**
   - VRAMClient integrated into tts_provider.py
   - Voice operations wait for active RAG

## Test Results
13/13 tests passed including:
- Concurrent RAG+Voice coordination verified
- Voice correctly waited 1.41s for RAG operation

## Key Decisions
- RAG preempts voice (knowledge retrieval > speech)
- ComfyUI managed manually by user (auto-launch attempted but batch files don't work from MSYS)
- nomic-embed-text chosen (768 dims, runs on Ollama)
