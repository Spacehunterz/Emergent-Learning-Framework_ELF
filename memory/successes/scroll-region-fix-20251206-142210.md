# Success: Scroll Region Support for Claudex VTE

**Date:** 2025-12-06
**Domain:** terminal-emulation
**Confidence:** 0.7 (compiles but needs runtime testing)

## Problem
Duplicate status lines appearing in Claudex when running Claude Code. The status bar (`▶▶ bypass permissions on`) was being printed twice.

## Root Cause
The `TerminalStateAdapter` in `terminal/emulator.rs` had stub implementations for scroll region functions:
- `set_scroll_region()` was a no-op
- `get_scroll_region()` always returned `(0, 0)`
- `line_feed()` didn't respect scroll regions

Claude Code uses DECSTBM (Set Top and Bottom Margins) to create a fixed status bar. Without scroll region support, line feeds would scroll the entire screen instead of just the region above the status bar.

## Solution
1. Added `scroll_top` and `scroll_bottom` fields to `TerminalState`
2. Added `scroll_region_up()` and `scroll_region_down()` methods to `Grid`
3. Updated `line_feed()` to check scroll region bounds
4. Implemented proper `set_scroll_region()` and `get_scroll_region()`
5. Bonus: Fixed `horizontal_tab()` to use actual tab stops instead of +8

## Key Files
- `src/semantic/mod.rs` - Grid and TerminalState changes
- `src/terminal/emulator.rs` - TerminalStateAdapter fixes

## Heuristic
When terminal output looks duplicated or corrupted, check scroll region support first - many TUI apps (Claude Code, vim, tmux) rely on DECSTBM for fixed UI regions.

## Tags
terminal, vte, scroll-region, decstbm, claudex
