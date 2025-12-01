# Success: Fixed confidence validation in record-heuristic.sh

**Date**: 2025-12-01
**Domain**: tools

## Summary

Fixed SQL parse error when passing word confidence values like "high" instead of numbers.

## What Was Done

Added confidence validation that converts words to numbers:
- low → 0.3
- medium → 0.6
- high → 0.85
- invalid/default → 0.7

## Root Cause

The confidence value was inserted directly into SQL without quotes since it's a REAL column. Passing "high" caused SQLite to interpret it as a column name: `Parse error near line 1: no such column: high`

## Tests Performed

Stress tested with Opus subagents:
- 18 test cases on record-heuristic.sh
- 15 test cases on record-failure.sh
- 21 test cases on query.py
- All edge cases (unicode, quotes, SQL injection, empty strings)

## Related

- Similar fix was already applied to record-failure.sh for severity words
