# Heuristic: FFI Code Uses #[allow] for Naming Conventions

## Domain
Rust, FFI, Windows API

## Pattern
When writing FFI bindings to C APIs (especially Windows D3D11, Win32), the Rust naming convention warnings for:
- `non_snake_case`
- `non_camel_case_types`  
- `non_upper_case_globals`

Are expected and should be suppressed at module level.

## Solution
Add at top of FFI module:
```rust
#![allow(non_snake_case)]
#![allow(non_camel_case_types)]
#![allow(non_upper_case_globals)]
```

## Why This Is Not "Sweeping Under Rug"
- FFI code intentionally matches C API names for documentation consistency
- Renaming would make it harder to cross-reference with Windows SDK docs
- This is standard practice in windows-rs, winapi, and other FFI crates

## Confidence
0.95

## Source
Claudex warning cleanup 2025-12-04 - Applied to 9 D3D11/Win32 binding files
