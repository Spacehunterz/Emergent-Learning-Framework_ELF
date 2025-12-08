# Claudex GPU Initialization Fix

Date: 2025-12-03
Project: Claudex (zero-dependency terminal emulator)
Domain: directx, rust, ffi

## Summary
Fixed GPU initialization failure (E_INVALIDARG from CreateRenderTargetView) in a zero-dependency DirectX 11 terminal emulator.

## Root Causes Found
1. **Wrong DXGI constant**: DXGI_USAGE_RENDER_TARGET_OUTPUT was `1 << 4` (16) instead of `1 << 5` (32)
2. **Missing vtable entry**: CreateTexture1D was missing from ID3D11Device vtable, shifting all subsequent offsets
3. **ID3DBlob vtable crash**: COM vtable calls segfaulted in MSYS2 environment, fixed by direct memory access
4. **Invalid blend state**: CreateBlendState requires valid descriptor, not NULL

## Debugging Approach
- Added eprintln\! checkpoints at each FFI call
- Queried texture description to verify bind flags
- Used QueryInterface to verify resource validity
- Compared vtable against Windows SDK documentation

## Outcome
- Terminal emulator now fully functional with GPU rendering
- 199 tests passing
- ~18,000 lines of Rust code
- 293 KB binary

## Key Learnings
- COM vtable completeness is critical - one missing entry breaks everything after it
- DXGI/D3D11 constants must be verified against SDK, not assumed
- Different D3D11 Create* functions have different NULL descriptor behavior
