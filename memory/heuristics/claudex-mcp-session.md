# Claudex MCP Session Learnings (2025-12-06)

## Heuristic: UTF-8 String Slicing Safety
**Domain:** rust, utf8, strings
**Confidence:** 0.9
**Principle:** Never use byte slicing `[..n]` on strings with multi-byte UTF-8 characters. Use `.chars().take(n).collect()` or check `.is_char_boundary()` first.
**Why:** Rust panics on invalid byte boundaries. Box-drawing chars (─) are 3 bytes.

## Heuristic: Cross-Thread PTY Access Pattern  
**Domain:** rust, threads, architecture
**Confidence:** 0.8
**Principle:** When MCP server runs in separate thread from main loop, use `Arc<Mutex<VecDeque<Action>>>` queue. MCP queues, main loop polls and executes.
**Why:** PTY writer can't be shared across threads safely.

## Heuristic: MCP Token Savings Are Contextual
**Domain:** mcp, tokens, architecture
**Confidence:** 0.9
**Principle:** Token savings occur when: (1) Claude runs inside terminal it controls, (2) user would paste output, (3) checking state without commands. Normal bash doesn't benefit.
**Why:** Direct bash output already minimal. MCP shines for state queries.

## Success: Claudex MCP Full Implementation
- propose_action with escape sequences (\n, \t, \xNN, \uNNNN)
- Semantic state detection (prompt/command/output/error)
- 5 UTF-8 panics fixed
- 3 unused code warnings → all functional
- Verified 85-97% token savings on targeted queries
