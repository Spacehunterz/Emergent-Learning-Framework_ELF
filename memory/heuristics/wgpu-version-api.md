# wgpu-version-api

**Domain:** rust, wgpu, graphics
**Confidence:** 0.7
**Created:** 2025-12-04
**Last Validated:** 2025-12-04

## Heuristic

When using wgpu, check the exact version - APIs change significantly between minor versions.

## Details

wgpu 0.20 requires:
- `Surface<'static>` lifetime (use `Arc<Window>`)
- `compilation_options: Default::default()` in VertexState/FragmentState
- `desired_maximum_frame_latency` in SurfaceConfiguration

winit 0.29 uses:
- `EventLoop::run()` with closure, not `ApplicationHandler` trait
- `WindowBuilder::new().build(&event_loop)` pattern

## Evidence

Claudex migration from DX11 to wgpu encountered multiple compile errors due to version mismatches.

## Application

Pin crate versions explicitly and check changelogs when upgrading.
