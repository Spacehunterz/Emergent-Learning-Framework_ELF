# Heuristic: Terminal Scrollback Buffer Architecture

**Created:** 2025-12-06
**Domain:** terminal-emulator
**Confidence:** 0.7
**Validations:** 1

## Heuristic

> Scrollback buffers should save lines ONLY when scrolling from top row (top==0) of the primary screen, never from alternate screen mode. Use a scroll_offset to track view position rather than copying data.

## Rationale

1. **Save on scroll from top only**: Lines only "leave" the screen when scrolling at the very top. Scroll regions below top row are internal repositioning.

2. **No scrollback for alt screen**: Programs like vim/less use alternate screen (?1049/?47). Users don't expect that content in history.

3. **Offset-based viewing**: Instead of copying scrollback into display buffer, use a `scroll_offset` and `get_display_cell(x, y)` that maps coordinates to either scrollback or current screen.

4. **Auto-scroll on new output**: When PTY produces new data, reset `scroll_offset=0` to return to live view.

## Implementation Pattern

```rust
// In scroll_region_up(), before scrolling:
if top == 0 && !using_alt_screen {
    scrollback.push(cells[0..width].to_vec());
    if scrollback.len() > max { scrollback.remove(0); }
}

// For rendering, use:
fn get_display_cell(&self, x: usize, y: usize) -> &Cell {
    if scroll_offset == 0 { return &cells[y * width + x]; }
    // ... map y to scrollback or current screen based on offset
}
```

## Tags

#terminal #scrollback #rendering
