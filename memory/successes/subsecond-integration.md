# Success: Subsecond Hot-Patching Integration

**Date:** 2025-12-06
**Domain:** Claudex Terminal

## What Was Built

1. **app_hotpatch.rs** - New module for subsecond integration
   - `HotPatchSession` manages `dx serve --hotpatch` process
   - Event parsing: Building, Patched(ms), Rebuilding, Error
   - Duration extraction from dx output

2. **Keyboard Shortcut**: Ctrl+H toggles hotpatch session

3. **UI Status Indicator**: Bottom-left corner shows patch status
   - Green for success (✓)
   - Red for errors (✗)
   - Gray for building/other

4. **Sample Project**: `projects/cats/`
   - HTML dashboard for webview live preview
   - Rust project with `subsecond::call()` wrapper

## Key Design Decisions

- Used `dx` CLI as build driver (not reinventing compiler integration)
- Leveraged existing file watcher infrastructure
- Status announced to accessibility layer

## Heuristic Extracted

> When integrating external tooling (subsecond), wrap the CLI rather than reimplementing internals. The Dioxus team maintains the compiler integration - we just orchestrate it.

## Dependencies

- Requires `dioxus-cli` installed: `cargo install dioxus-cli`
- Projects need `subsecond::call()` at patch points
