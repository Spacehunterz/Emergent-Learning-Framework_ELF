# Windows Terminal Overlay Sync

**Domain:** rust, windows, terminal, gui, overlay
**Confidence:** 0.7
**Created:** 2025-12-03

## Problem

Need to position a native GUI window (WebView) to overlay a specific region of a terminal/console window, creating the illusion of embedded content.

## Solution

1. **Get console window position** using Windows API:
```rust
#[link(name = "kernel32")]
extern "system" {
    fn GetConsoleWindow() -> *mut c_void;
    fn GetStdHandle(n: u32) -> *mut c_void;
    fn GetCurrentConsoleFontEx(...) -> i32;
}

#[link(name = "user32")]
extern "system" {
    fn GetWindowRect(hwnd: *mut c_void, rect: *mut RECT) -> i32;
    fn GetClientRect(hwnd: *mut c_void, rect: *mut RECT) -> i32;
}
```

2. **Calculate cell size** from font info:
```rust
let (cell_width, cell_height) = (font_size.x, font_size.y);
```

3. **Convert cell coords to screen pixels**:
```rust
let screen_x = window_x + (col * cell_width);
let screen_y = window_y + (row * cell_height);
```

4. **Position overlay window**:
```rust
window.set_outer_position(LogicalPosition::new(screen_x, screen_y));
window.set_inner_size(LogicalSize::new(width_px, height_px));
```

## Key Details

- Use `GetClientRect` for content area (excludes title bar/borders)
- Calculate border offset: `window_rect - client_rect`
- Title bar is at TOP, so: `content_y = window_top + (border_height - border_width/2)`
- Set overlay to `with_decorations(false)` and `with_always_on_top(true)`
- Track last area to avoid redundant position updates

## Caveats

- Different terminals (cmd, PowerShell, Windows Terminal) may have different behaviors
- DPI scaling can affect calculations
- Font changes require recalculation
