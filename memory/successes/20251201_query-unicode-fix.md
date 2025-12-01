# Success: Fixed Unicode encoding in query.py for Windows

**Date**: 2025-12-01
**Domain**: tools

## Summary

Fixed UnicodeEncodeError when querying domains containing special characters (→, ✓, etc.) on Windows.

## What Was Done

Added UTF-8 encoding wrapper for stdout/stderr on Windows:
```python
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
```

## Root Cause

Windows console uses cp1252 encoding by default, which doesn't support Unicode arrows (→) and checkmarks (✓) used in heuristics.

## Tests Performed

- Query golden rules ✓
- Query context ✓  
- Query domain with unicode chars ✓
- Record failure with special chars ✓
- Record heuristic with unicode ✓
