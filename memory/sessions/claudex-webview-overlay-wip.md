# Claudex WebView Overlay - Work In Progress

**Date:** 2025-12-03
**Status:** In Progress

## What Works
- WebView opens without crashing (EventLoopBuilder fix)
- Terminal panic handler (restores terminal state on crash)
- Thread tracking (stderr thread now joined properly)
- Auto-open WebView when panel toggles on
- Auto-close WebView when panel toggles off

## What's Broken
- WebView position/size not syncing to panel area
- Opens as small window, not overlaying panel

## Debug Info Needed
Run and capture stderr:
```
./target/release/claudex.exe 2>&1 | grep -E "\[SYNC\]|\[TERMINAL"
```

## Next Steps
1. Get debug output to see calculated values
2. Fix position calculation for Windows Terminal
3. Test resize sync
