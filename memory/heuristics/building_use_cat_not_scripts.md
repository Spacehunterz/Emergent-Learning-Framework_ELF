# Heuristic: Use cat Heredocs for Building Records

## Domain
Emergent Learning Framework

## Pattern
The record-*.sh scripts often fail with cryptic errors.

## Solution
Skip the scripts. Write markdown files directly with cat heredocs.

## Why
- Scripts have parsing/validation that breaks on edge cases
- cat heredocs are simple, reliable, and fast  
- The memory files are just markdown - no magic needed

## Confidence
0.9

## Source
2025-12-04 - Script failures during Claudex cleanup, cat worked first try
