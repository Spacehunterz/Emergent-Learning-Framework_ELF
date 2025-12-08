# Heuristic: Terminal Cursor Bounds Are Grid Height - 1

**Domain:** terminal-emulation
**Confidence:** 0.85
**Validations:** 1

## Pattern
When implementing terminal emulators, cursor position (especially cursor_y) must be clamped to `grid.height - 1`, not `grid.height`.

## Why It Matters
- Grid of 51 rows has valid indices 0-50
- Cursor at row 51 is OUT OF BOUNDS
- `grid.set(x, y, ...)` silently fails when y >= height (bounds check returns early)
- Result: characters written to invalid rows disappear - "blank space" mystery

## Detection Signs
- Content mysteriously disappears or shows as blank
- Log shows cursor at row N where grid has N rows (should be N-1 max)
- Works fine until content fills screen, then breaks

## Fix Pattern
```rust
// Use saturating_sub for safety
let scroll_bottom = grid.height.saturating_sub(1);

// Always clamp after any cursor modification
if grid.cursor_y >= grid.height {
    grid.cursor_y = grid.height.saturating_sub(1);
}
```

## Related
- LF (line feed) handler must clamp after incrementing
- write_char line wrap must clamp after incrementing
- CUP (cursor position) must clamp requested row

**Source:** Claudex VT sequence debugging session 2025-12-06
