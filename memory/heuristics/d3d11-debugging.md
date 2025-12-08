# DirectX 11 FFI Debugging Heuristics

Created: 2025-12-03
Domain: directx, ffi, rust, windows
Confidence: 0.9

## Heuristic 1: Verify COM Vtable Completeness
When defining COM vtable structs for DirectX, verify EVERY method is present in the correct order. Missing methods shift all subsequent offsets causing silent failures with misleading error codes like E_INVALIDARG.

**Example:** ID3D11Device was missing CreateTexture1D between CreateBuffer and CreateTexture2D, causing CreateRenderTargetView to actually call CreateUnorderedAccessView.

**Validation:** Fixed Claudex terminal emulator GPU init issue.

## Heuristic 2: Check DXGI Constants Against SDK
DXGI usage flags are bit-shifted values. Double-check the shift amounts:
- DXGI_USAGE_SHADER_INPUT = 1 << 4 (0x10)
- DXGI_USAGE_RENDER_TARGET_OUTPUT = 1 << 5 (0x20)

**Example:** Had `1 << 4` for both, causing back buffer to lack BIND_RENDER_TARGET.

## Heuristic 3: NULL Descriptor Behavior Varies
Some D3D11 Create* functions accept NULL for auto-detect (CreateRenderTargetView), others require valid descriptors (CreateBlendState). Check MSDN for each function.

## Heuristic 4: Add Debug Checkpoints for FFI Calls
When debugging FFI issues, add eprintln\! before/after each COM call to identify exactly which call fails. The error may appear at a different location than the actual bug.
