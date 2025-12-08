# Success: Phantom Cursor Fix for Text Flooding

**Date:** 2025-12-07
**Domain:** terminal-emulation, cyberx
**Confidence:** 0.95
**Impact:** HIGH

## The Problem

Text flooding/scrolling issue where spinners and progress indicators would create floods of new lines instead of overwriting themselves in place.

## Root Cause

**Eager Wrap Logic**: As soon as a character was printed in the last column, the cursor immediately jumped to the next line.

### Why This Broke Spinners

1. Spinner prints a full line of text
2. Spinner sends `\r` (Carriage Return) to return to start of line
3. **BUG**: Because cursor had already wrapped to the new line, `\r` sent it to column 0 of the NEW line
4. Result: Flood of new lines instead of in-place updates

## The Solution: Phantom Cursor

Instead of immediately wrapping when hitting the last column, the cursor enters a **phantom state** (technically at index `width`, just off-screen).

The cursor then **waits** to see what comes next:
- If a **printable character** comes next → THEN wrap to next line
- If a **control code** (like `\r`) comes next → Execute the control code on current line

### Why This Works

The `\r` now correctly returns to column 0 of the **same line**, allowing spinners to overwrite themselves perfectly.

## Key Insight

Terminal cursor wrap behavior is NOT "wrap immediately on reaching edge" but rather "wrap lazily when the next character needs to be printed."

## Credit

Fix identified by Gemini Pro during debugging session.

## Transferable Heuristic

> **Lazy Wrap Principle**: In terminal emulation, cursor wrap should be deferred (phantom cursor) until actually needed, not triggered eagerly on reaching the boundary. Control codes should execute BEFORE any pending wrap.

## Validation

- Fixed spinner flooding in CyberX terminal emulator
- Matches behavior of real terminals (xterm, VT100 spec)

## Tags

- terminal-emulation
- cursor-behavior
- phantom-cursor
- line-wrap
- cyberx
- ansi-parsing
