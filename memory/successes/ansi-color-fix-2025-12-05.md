# Success: ANSI Color Support Fixed in Claudex

**Date:** 2025-12-05
**Domain:** terminal-emulator, ansi-parsing
**Project:** Claudex

## Problem

ANSI colors (256-color and true-color) were not displaying correctly:
1. Theme switching overrode explicit ANSI colors
2. Block characters (█) always displayed as orange
3. Grid clear operations destroyed stored colors
4. SPACE characters in CSI sequences broke parsing

## Solution

### 1. Sentinel-Based Color System
- Added `DEFAULT_COLOR_SENTINEL = [0.0, 0.0, 0.0, 0.0]` (alpha=0)
- SGR 0 (reset) and SGR 39 (default fg) now set sentinel instead of actual color
- Renderer resolves sentinel to theme color at render time
- Explicit ANSI colors (alpha=1.0) pass through unchanged

### 2. Grid Clear Fix
- Changed 13 locations in `app_grid.rs` from hardcoded white to `DEFAULT_FG` sentinel
- Affects: new, resize, scroll_up, scroll_down, clear_line, insert_lines, delete_lines, etc.

### 3. Block Character Fix
- Changed condition from `if block_char { use_orange }` to `if block_char && fg == SENTINEL { use_orange }`
- ANSI-colored blocks now display with their specified color

### 4. CSI Space Handling
- Added `b' ' => {}` in CSI state to ignore spaces
- Some terminals/apps emit spaces as intermediate bytes

## Key Insight

The swarm found that PowerShell's `Write-Host` with escape sequences doesn't emit raw ANSI through conpty. Testing required WSL/bash:
```bash
wsl echo -e "\e[38;5;196mRED\e[0m"
```

## Files Modified
- src/app_ansi.rs (sentinel, block char fix, CSI space)
- src/app_grid.rs (13 clear operations)
- src/main.rs (sentinel import and render-time resolution)

## Verification
- 256-color: RED (196) displays correctly
- True-color: Grayscale gradients work
- Theme switching only affects default-colored text

## Tags
#terminal #ansi #color #parsing #sentinel-pattern
