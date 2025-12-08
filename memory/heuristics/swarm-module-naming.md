# Heuristic: Swarm Module Naming Conflicts

**ID:** swarm-module-naming
**Created:** 2025-12-05
**Domain:** rust, refactoring, swarm
**Confidence:** 0.7

## Pattern
When running a swarm to modularize code, extracted modules may conflict with existing library module names.

## Trigger
- Swarm extracting modules from a monolithic file
- Project has both a binary (main.rs) and library (lib.rs)
- Library already declares modules with common names (input, renderer, grid, etc.)

## Heuristic
**Check for existing module structures before naming extracted modules.**

Naming conflicts between new modules and existing library modules can derail the entire extraction. Use unique prefixes (e.g., `app_`, `main_`) to avoid collisions.

## Evidence
- Claudex modularization: Extracted `input.rs` overwrote existing `src/input/mod.rs`
- Had to rename all modules to `app_*.rs` to avoid conflicts
- Cost: ~15 minutes of debugging and renaming

## Action
Before extracting modules:
1. Check `lib.rs` for existing `pub mod` declarations
2. Check for existing module directories (`src/name/`)
3. Choose unique names that don't collide

## Validation Count
1
