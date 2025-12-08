# Success: Fixed VT Sequence Scroll Flooding in Claudex

**Date:** 2025-12-06
**Domain:** terminal-emulation
**Confidence:** 0.9

## Problem
Claude Code CLI caused "thought flooding" - repeated full-screen content filling terminal instead of in-place updates. Also caused blank space filling screen.

## Root Causes Identified
1. **LF at bottom caused scroll when content should overwrite** - Ink-style apps position cursor and redraw content with embedded newlines. When final LF hits bottom row, scroll shifts content up, next frame positions at same row but content has moved.

2. **Cursor going out of bounds** - cursor_y reaching row 51 on 51-row grid (valid: 0-50), causing writes to silently fail.

3. **Wrong code path investigated initially** - `src/terminal/emulator.rs` was NOT the active code; `src/app_ansi.rs` is what main.rs actually uses.

## Solution
1. **Frame-based scroll suppression**: Track when CUP positions cursor mid-screen (`frame_start_row`). When LF would scroll during a "frame", suppress the scroll instead.

2. **Bounds clamping**: Added `saturating_sub(1)` and safety clamps to ensure cursor_y never exceeds grid.height - 1.

3. **Consistent scroll suppression**: Don't clear `frame_start_row` on first suppressed scroll - keep suppressing until next CUP.

## Key Code Changes
- `app_ansi.rs`: LF handler checks `frame_start_row.is_some()` to suppress scroll
- `app_ansi.rs`: CUP handler sets `frame_start_row` when positioning mid-screen
- `app_ansi.rs`: Added safety clamps everywhere cursor_y is modified

## Heuristics Extracted
1. **Check which code path is actually active** - Multiple implementations can coexist; trace from main() to find the real code.
2. **Add diagnostic logging first** - [CUP], [LF], [EL] logs revealed the actual sequence pattern.
3. **Bounds checking is critical** - Silent failures from out-of-bounds access cause mysterious blank content.
4. **Frame-based rendering needs special handling** - Terminal apps that redraw in place need scroll suppression.

## Validation
- Progress bar test now works: `1..5 | % { Write-Host "`r$_" -NoNewline; sleep -ms 500 }`
- Claude Code thinking indicator updates in place without flooding
