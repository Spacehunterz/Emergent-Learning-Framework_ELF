# TUI Panic Safety Pattern

**Domain:** rust, tui, terminal, panic-handling
**Confidence:** 0.8
**Created:** 2025-12-03

## Pattern

For terminal UI apps using raw mode/alternate screen, always install a panic hook that restores terminal state AND wrap the main loop in catch_unwind.

## Implementation

```rust
// Install panic hook
let original_hook = std::panic::take_hook();
std::panic::set_hook(Box::new(move |info| {
    let _ = disable_raw_mode();
    let _ = execute!(io::stdout(), LeaveAlternateScreen, DisableMouseCapture);
    original_hook(info);
}));

// Wrap main loop
let result = std::panic::catch_unwind(AssertUnwindSafe(|| {
    main_loop()
}));

// Restore hook and cleanup
let _ = std::panic::take_hook();
// ... cleanup terminal ...
```

## Why

Without this, panics leave terminal in raw mode making shell unusable.
