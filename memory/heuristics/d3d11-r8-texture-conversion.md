# D3D11 R8 Texture Conversion

## Pattern
When using R8_UNORM single-channel textures in D3D11 for glyph atlases, convert to RGBA8 format.

## Why
Some GPU drivers have row alignment issues with single-byte-per-pixel R8 textures. Symptoms include:
- Checkerboard patterns with POINT filtering
- Horizontal banding or streaking
- Blur artifacts with LINEAR filtering

## Solution
Convert R8 grayscale to RGBA8:
- R = grayscale value (what shader samples via `.r`)
- G = grayscale (or 0)
- B = grayscale (or 0)
- A = 255 (opaque)

Update row pitch from `width` to `width * 4`.

## Tags
directx, textures, fonts, d3d11, debugging

## Confidence
0.8

## Created
2025-12-04

## Validations
1 (fixed checkerboard pattern in Claudex terminal)
