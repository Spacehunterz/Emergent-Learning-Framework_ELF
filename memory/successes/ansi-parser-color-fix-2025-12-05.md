# Success: ANSI Parser 256-Color/Truecolor and State Machine Fix

**Date:** 2025-12-05
**Domain:** terminal-emulator, parsing, rust
**Confidence:** 0.9

## Context

Claudex terminal emulator had an ANSI parser that was:
1. Ignoring 256-color and truecolor sequences (ESC[38;5;n and ESC[38;2;r;g;b)
2. Getting stuck on rapid-fire escape sequences (infinite "Thinking..." spam)
3. Backspace (0x08) sometimes adding extra blank lines

## Solution

### Parser State Machine Fixes (ansi.rs)

1. **ESC handling in ALL states**: Added top-level ESC (0x1B) handling that always starts a new escape sequence from any state. This prevents the parser from getting stuck.

2. **CAN/SUB abort handling**: Added handling for CAN (0x18) and SUB (0x1A) which abort sequences and return to ground.

3. **New OscEscape state**: Properly handles two-byte ST (ESC \) terminator instead of the broken simplified version.

4. **OSC length limit**: Added MAX_OSC_LEN (4096) to prevent memory exhaustion from malformed sequences.

5. **Robust extended color parsing**: The parse_extended_color function handles:
   - 256-color: `38;5;n` and `38:5:n` (colon separator)
   - Truecolor: `38;2;r;g;b` and `38:2:r:g:b`
   - Colorspace form: `38;2;cs;r;g;b` (5-param form)
   - Incomplete sequences handled gracefully

### Backspace Fix (emulator.rs)

Changed backspace to be destructive:
- Move cursor left AND clear the cell
- Wrap to previous line end if at column 0
- Never insert new lines

## Key Insights

1. **ESC is the universal reset** - In a terminal parser, ESC should ALWAYS be able to start a new sequence from any state. The original parser didn't handle ESC in CsiIgnore state.

2. **Colon vs semicolon in SGR** - Modern terminals use both `;` and `:` as parameter separators in SGR sequences. Both must be handled identically.

3. **Two-byte terminators need dedicated states** - OSC's ST terminator (ESC \) requires tracking that we saw ESC before we see backslash.

4. **Destructive vs non-destructive backspace** - Standard terminal backspace just moves cursor, but many applications expect destructive backspace (move + erase).

## Validation

- All 24 ANSI parser unit tests pass
- Includes tests for 256-color, truecolor, colon separators, rapid sequences
- Release build compiles successfully

## Tags

#ansi #terminal #parser #state-machine #colors #rust
