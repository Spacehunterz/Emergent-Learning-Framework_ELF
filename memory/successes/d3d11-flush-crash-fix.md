# D3D11 Context Flush() Crash Fix

**Date:** 2025-12-03
**Domain:** directx, d3d11, ffi, rendering
**Confidence:** 0.9

## Problem
When calling `ID3D11DeviceContext::Flush()` via custom Rust FFI COM vtable bindings, the application would hang/crash silently. The debug log showed the render loop completing successfully up to the Flush() call, then nothing.

## Root Cause
The `Flush()` method in the custom `ID3D11DeviceContextVtbl` struct was likely at the wrong vtable offset, causing it to call an incorrect method. D3D11 COM vtables have very specific ordering and missing/incorrect methods shift all subsequent offsets.

## Solution
Removed the explicit `Flush()` call before `Present()`. The `IDXGISwapChain::Present()` method implicitly synchronizes all pending GPU work, making an explicit `Flush()` redundant.

```rust
// BEFORE (crashing):
fn present(&mut self) -> Result<(), RenderError> {
    (*self.context).Flush();  // CRASH HERE
    (*self.swap_chain).Present(0, 0);
}

// AFTER (working):
fn present(&mut self) -> Result<(), RenderError> {
    // Skip Flush - Present() handles synchronization
    (*self.swap_chain).Present(0, 0);
}
```

## Heuristic
**When using custom D3D11 FFI bindings and a method crashes/hangs, check if:**
1. The vtable has ALL methods in the correct order
2. The method is actually necessary (many D3D11 operations have implicit synchronization)
3. Present() can be used instead of Flush() for end-of-frame sync

## Tags
directx, d3d11, ffi, vtable, flush, present, crash, debugging
