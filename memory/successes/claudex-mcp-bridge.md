# Claudex MCP Bridge Implementation

**Date:** 2025-12-06
**Type:** Success
**Domain:** mcp, claudex, integration

## What Was Built

1. **src/mcp_bridge.rs** - Named pipe server for Claudex
   - Listens on `\.\pipe\claudex`
   - Responds to JSON commands (ping, dimensions, cursor, query_grid, etc.)
   - Thread-safe state sharing via Arc<RwLock>

2. **crates/claudex-mcp/** - MCP server binary (already existed, just needed building)
   - Connects to Claudex via named pipe
   - Exposes tools to Claude Code

3. **Integration in main.rs** - 4 lines total
   - mod declaration
   - McpState initialization
   - Server start
   - State update in event loop

## Key Learnings

- Windows named pipe API in windows 0.58 crate returns HANDLE directly, not Result
- PIPE_ACCESS_DUPLEX is in Win32::Storage::FileSystem, not Win32::System::Pipes
- MCP config can have duplicate entries with different paths - causes confusion

## Still Pending

- Semantic region detection (prompt/command/output) needs wiring in app_ansi.rs
- This is where real token savings will come from

## Tags
mcp, claudex, windows, named-pipes, integration
