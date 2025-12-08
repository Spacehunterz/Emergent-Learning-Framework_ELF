# Heuristic: Replace static mut with AtomicXXX

## Domain
Rust

## Pattern
When you see `static mut VARNAME: Type = ...` with references like `unsafe { VARNAME }`, this is **undefined behavior**.

## Solution
Replace with atomic types:
```rust
use std::sync::atomic::{AtomicU64, Ordering};
static COUNTER: AtomicU64 = AtomicU64::new(0);

// To increment and get value:
let val = COUNTER.fetch_add(1, Ordering::Relaxed);

// To just read:
let val = COUNTER.load(Ordering::Relaxed);
```

## Confidence
0.9

## Source
Claudex warning cleanup 2025-12-04 - Fixed 2 instances of static_mut_refs UB
