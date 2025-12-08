# Terminal Bell on Resize - Investigation Needed

**Created:** 2025-12-08
**Priority:** MEDIUM
**Status:** PENDING INVESTIGATION

## Problem
System alert sound plays when resizing the terminal window. User reports this started happening after using async agents.

## Environment
- Platform: Windows (MSYS_NT-10.0)
- MCP: claudex-mcp connected (terminal state monitoring)
- Feature: Async agents (background Task tool)

## Possible Causes
1. **Claudex MCP** - Terminal state tracking may emit bell character on resize events
2. **Background shells** - SIGWINCH handling in async agent shells
3. **Escape sequence issues** - Malformed sequences during resize on Windows

## Investigation Steps
1. [ ] Check claudex-mcp source for bell character emission
2. [ ] Test resize with claudex-mcp disconnected
3. [ ] Test resize with no background agents running
4. [ ] Check Windows Terminal bell settings
5. [ ] Review async agent shell cleanup

## Impact
- User annoyance
- Could affect adoption if others experience same issue

## Notes
- No tasks running at time of report
- Issue persists after swarm completion
