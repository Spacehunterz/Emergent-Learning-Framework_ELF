# Heuristic: Sentinel Pattern for Theme-Aware Colors

**Created:** 2025-12-05
**Domain:** terminal-emulator, rendering
**Confidence:** 0.9
**Validations:** 1

## Heuristic

> When terminal cells need to distinguish between "use theme default" and "explicit color", use a sentinel value (e.g., alpha=0) that's impossible in normal usage, then resolve at render time.

## Rationale

The problem: How do you tell if a cell's color is "white because the theme is white" vs "white because ANSI code 37 was used"?

Solution: Use a sentinel value that can't occur naturally:
- `[0.0, 0.0, 0.0, 0.0]` (black with alpha=0) means "use theme default"
- Any color with alpha=1.0 means "explicit color, don't change"

At render time:
```rust
if cell.fg == SENTINEL {
    use theme.foreground()
} else {
    use cell.fg  // preserved exactly
}
```

## Benefits

1. Theme switching only affects default-colored text
2. ANSI colors survive scrolling and screen clears
3. No need to track "is_explicit_color" boolean separately
4. Clean separation between parsing and rendering

## Evidence

Fixed bug where theme switching overwrote all ANSI colors. Now only "default" text follows theme.

## Tags

#terminal #color #rendering #sentinel-pattern #theme
