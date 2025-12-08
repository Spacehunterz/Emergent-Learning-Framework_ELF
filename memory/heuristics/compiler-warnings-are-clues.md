# Heuristic: Compiler Warnings Are Investigation Leads

## Summary
Treat compiler warnings as investigation leads, not annoyances to suppress.

## Pattern
When you see "method X is never used" or "function Y is never called" warnings, investigate WHY before suppressing.

## Evidence
In Claudex refactoring session (2025-12-06):
- Warning "clear_to_end is never used" → revealed CSI J handler used inline code instead of helper
- Warning "is_cursor_visible is never used" → revealed cursor rendering was COMPLETELY MISSING
- Warning "wrap_bracketed_paste is never used" → revealed paste handlers weren't using bracketed paste mode
- Warning "sanitize_title is never used" → revealed OSC title handling wasn't hooked up

Each "unused" warning was a broken feature waiting to be discovered.

## Heuristic
> Before suppressing an "unused" warning, ask: "Was this SUPPOSED to be used?"
> If yes, find where it should connect and fix it.
> Only suppress after confirming it's intentionally reserved for future use.

## Tags
refactoring, debugging, rust, terminal
