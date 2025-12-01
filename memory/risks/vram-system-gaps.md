---
title: VRAM System Known Gaps
type: risk
domain: infrastructure
tags: vram,gaps,future-work
severity: 3
---

# Known Gaps in VRAM Coordination System

## HIGH Priority
- No VRAM enforcement (tracks ops, doesn't prevent over-subscription)
- Stale detection coarse (120s timeout, no PID check)

## MEDIUM Priority  
- Config shallow merge risk
- No audit logging
- File lock contention at >5 concurrent ops

## Not Tested
- >5 concurrent embedding batches
- Rapid voice + RAG pipelining
- Long-running LLM (9GB)
- Actual VRAM pressure scenarios
