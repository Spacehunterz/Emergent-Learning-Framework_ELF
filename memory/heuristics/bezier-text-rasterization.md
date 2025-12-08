# Bezier Curve Text Rasterization Precision

## Pattern
When rasterizing font glyphs from Bezier curves, sub-pixel precision in the curve evaluation can cause blurry or inconsistent text rendering.

## Why
TTF/OTF fonts define glyph outlines as Bezier curves. The rasterizer evaluates these curves to produce pixel coverage values. If the final glyph bitmap is then positioned at fractional screen coordinates, the sub-pixel offset compounds with any rasterization imprecision, causing visible blur.

## Solution
1. Rasterize Bezier curves at integer coordinates within the glyph atlas
2. Floor final screen positions when placing glyphs (see: subpixel-text-positioning.md)
3. Ensure the rasterizer output aligns to the atlas grid without sub-pixel offsets

## Related
- subpixel-text-positioning.md (the pixel-level fix)

## Tags
bezier, fonts, text, rasterization, gpu, rendering, blur

## Confidence
0.8

## Created
2025-12-04

## Validations
1 (fixed blurry text in Claudex terminal - Bezier rasterizer was the root cause)
