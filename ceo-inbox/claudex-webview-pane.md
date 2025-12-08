# Goal: Add WebView Pane to Claudex

**Date:** 2025-12-06
**Priority:** Next
**Type:** Feature Goal

## Description
Add a webview pane to Claudex terminal emulator. This would allow rendering web content alongside the terminal.

## Potential Use Cases
- Preview markdown/HTML output
- Display documentation
- Render Claude artifacts
- Show web-based tool outputs
- Split-pane development environment

## Technical Considerations
- WebView library options for Rust/Windows:
  - `wry` (Tauri's webview) - cross-platform, uses system webview
  - `webview` crate - lightweight wrapper
  - Direct WebView2 (Windows-specific, via windows-rs)
- Integration with existing wgpu renderer
- Layout management (split panes, tabs, floating)
- IPC between terminal and webview

## Questions for CEO
1. What's the primary use case driving this? (artifacts, docs, preview?)
2. Should it be a split pane, tab, or floating window?
3. Any specific web content requirements? (local only, or external URLs?)
4. Priority relative to other Claudex work?

## Status
Awaiting CEO direction

