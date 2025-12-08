# Terminal Bell on Resize - CAUSE IDENTIFIED

**Created:** 2025-12-08
**Priority:** MEDIUM
**Status:** CAUSE IDENTIFIED - claudex-mcp

## Problem
System alert sound plays when resizing the terminal window.

## Root Cause
**Confirmed: claudex-mcp server**

Test results:
- ✓ With claudex-mcp enabled: Bell sounds on resize
- ✓ With claudex-mcp disabled: No bell on resize

## Likely Issue
The claudex-mcp server monitors terminal state and likely:
1. Receives resize events (SIGWINCH or equivalent)
2. Outputs a bell character (`\x07`) somewhere in its response
3. Or has malformed escape sequences during state refresh

## Fix Location
Check claudex-mcp source code for:
- Bell character in output
- Error handling on resize events
- Escape sequence generation

## Action Items
- [ ] Report issue to claudex-mcp maintainer/repo
- [ ] Or fix locally if we have the source
