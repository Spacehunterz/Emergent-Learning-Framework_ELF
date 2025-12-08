# Sub-pixel Text Positioning Causes Blur

## Pattern
When rendering text with POINT (nearest-neighbor) texture filtering, glyph positions must be floored to integer pixel coordinates.

## Why
With fractional cell dimensions (e.g., cell_width = 10.5), glyphs land on sub-pixel positions:
- Column 0: x = 0.0
- Column 1: x = 10.5
- Column 2: x = 21.0

Odd columns hit half-pixel positions. With POINT filtering, this causes inconsistent texel sampling between adjacent pixels, producing blur or shimmer.

## Solution
Floor all glyph position coordinates before rendering:
```rust
let screen_x = (x as f32 * cell_width).floor();
let screen_y = (y as f32 * cell_height).floor();
let glyph_x = (x + bearing_x).floor();
let glyph_y = (y + baseline - bearing_y).floor();
```

## Tags
rendering, fonts, text, gpu, directx, blurry

## Confidence
0.85

## Created
2025-12-04

## Validations
1 (fixed blurry text in Claudex terminal)
