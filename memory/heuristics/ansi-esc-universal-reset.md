# Heuristic: ESC is the Universal Reset in ANSI Parsers

**Created:** 2025-12-05
**Domain:** terminal-emulator, parsing
**Confidence:** 0.8
**Validations:** 1

## Heuristic

> In ANSI/VT parser state machines, ESC (0x1B) should ALWAYS be able to start a new escape sequence from ANY state. Never let a state ignore ESC or the parser can get stuck on malformed input.

## Rationale

Real terminal output can be:
- Malformed or truncated
- Interrupted mid-sequence
- From applications that don't follow specs perfectly

If ESC doesn't reset the parser, a single malformed sequence can leave the parser stuck in a state (like CsiIgnore or OscString) indefinitely.

## Evidence

Fixed a bug where rapid-fire SGR sequences caused "infinite Thinking... spam" because:
1. Parser entered CsiIgnore on unexpected byte
2. CsiIgnore didn't handle ESC
3. Parser stayed stuck until a final byte (0x40-0x7E) arrived
4. New ESC sequences were being ignored

## Counter-examples

The only exception is when tracking multi-byte terminators like ST (ESC \). In OscEscape state, seeing ESC followed by non-backslash should still restart the sequence.

## Tags

#ansi #terminal #parser #state-machine
