# Windows EventLoop Threading

**Domain:** rust, windows, gui, tao, winit, eventloop
**Confidence:** 0.95
**Created:** 2025-12-03
**Validated:** 2025-12-03 (fixed Claudex webview)

## Problem

On Windows, `EventLoop::new()` panics if called from a non-main thread:
```
Initializing the event loop outside of the main thread is a significant 
cross-platform compatibility hazard.
```

## Solution (tao 0.30+)

Use `EventLoopBuilder` with the platform extension trait:

```rust
use tao::event_loop::EventLoopBuilder;

#[cfg(target_os = "windows")]
use tao::platform::windows::EventLoopBuilderExtWindows;

// Create event loop that works on any thread
let event_loop = {
    let mut builder = EventLoopBuilder::new();
    #[cfg(target_os = "windows")]
    builder.with_any_thread(true);
    builder.build()
};
```

## Notes

- `EventLoop::new_any_thread()` does NOT exist in tao 0.30
- Must use `EventLoopBuilder` + `with_any_thread(true)`
- The `#[cfg]` makes it compile on all platforms
