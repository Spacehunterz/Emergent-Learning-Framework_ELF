# D3D11: Prefer Present() over explicit Flush()

**Date:** 2025-12-03
**Domain:** directx, d3d11, rendering
**Confidence:** 0.85

## Heuristic
When rendering with D3D11, prefer calling `IDXGISwapChain::Present()` directly without an explicit `ID3D11DeviceContext::Flush()` beforehand.

## Reasoning
1. `Present()` implicitly synchronizes all pending GPU work
2. Custom FFI COM vtables may have incorrect method offsets for `Flush()`
3. Removing `Flush()` reduces one potential point of failure
4. No performance benefit from explicit `Flush()` before `Present()`

## When to apply
- End-of-frame rendering in D3D11 applications
- Custom Rust FFI bindings to D3D11
- Debugging render loop hangs/crashes

## Tags
directx, d3d11, present, flush, rendering, optimization
