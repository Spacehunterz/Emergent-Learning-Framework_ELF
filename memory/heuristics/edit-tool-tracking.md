# Edit Tool Requires Write Tool Tracking

## Heuristic
The Edit tool only works on files that have been "registered" via the Write tool. Reading a file with Read tool does NOT register it for editing.

## Pattern
- Write creates file → Edit works ✓
- Write tracked + bash modifies (notification shown) → Edit works ✓  
- Bash-only files (never Write) → Edit fails ✗
- Read + Edit (no prior Write) → Edit fails ✗

## Root Cause
Edit tool compares against internal file state that is ONLY populated by Write tool. The Read tool reads content but doesn't add to tracking.

## Workarounds
1. Use `sed` for files only touched by bash
2. Use Write to overwrite file (registers it)
3. Touch file with Write before editing

## Confidence
HIGH - Tested with 6 scenarios, pattern confirmed

## Domain
tools, editing, bash

## Date
2025-12-02

## Validated By
Systematic testing of Edit tool behavior
