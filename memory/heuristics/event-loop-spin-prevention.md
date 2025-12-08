# Heuristic: Prevent Event Loop Spin Loops

**Created:** 2025-12-05
**Domain:** gui, winit, game-loop
**Confidence:** 0.8
**Validations:** 1

## Heuristic

> In winit/GUI event loops, NEVER use `ControlFlow::Poll` with unconditional `request_redraw()` in `AboutToWait`. This creates an infinite spin loop consuming 100% CPU.

## Correct Pattern

```rust
// Use WaitUntil for frame pacing
let next_frame = Instant::now() + Duration::from_millis(16);
elwt.set_control_flow(ControlFlow::WaitUntil(next_frame));
```

## Anti-Pattern

```rust
elwt.set_control_flow(ControlFlow::Poll);  // Constantly polls
...
Event::AboutToWait => window.request_redraw(),  // WRONG: infinite loop
```

## Evidence

Claudex terminal was rendering thousands of frames per second, causing visual "flooding" when Ink.js sent rapid updates. Changing to WaitUntil with 16ms intervals fixed the performance issue.

## Tags

#winit #event-loop #performance #gui
