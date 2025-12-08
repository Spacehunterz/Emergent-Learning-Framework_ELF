# DX11 ResizeBuffers Fix

**Date:** 2025-12-04
**Domain:** dx11, graphics, windows

## Problem

Claudex terminal emulator froze when resizing window. Log showed:
```
Failed to resize renderer: InvalidViewport
[FATAL] render_target_view is NULL!
```

## Root Cause

`IDXGISwapChain::ResizeBuffers` was called with explicit format `DXGI_FORMAT_R8G8B8A8_UNORM` instead of 0 (`DXGI_FORMAT_UNKNOWN`).

When you pass 0, DXGI preserves the existing buffer format. Passing an explicit format can fail if it doesn't match the original swap chain configuration.

## Solution

Changed:
```rust
ResizeBuffers(1, width, height, DXGI_FORMAT_R8G8B8A8_UNORM, 0)
```

To:
```rust
ResizeBuffers(0, width, height, 0, 0)
```

Also added early return when dimensions unchanged to avoid unnecessary resize operations.

## Lesson

For DXGI ResizeBuffers: use 0 for buffer count and format to preserve existing settings unless you specifically need to change them.
