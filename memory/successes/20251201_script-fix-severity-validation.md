# Success: Fixed record-failure.sh severity validation

**Date**: 2025-12-01
**Domain**: tools

## Summary

Fixed record-failure.sh script that was failing with SQL error when passing word severities like "medium" or "high".

## What Was Done

1. Restored non-interactive mode (--args and env vars) that was lost in git checkout
2. Added severity word-to-number conversion:
   - low → 2
   - medium → 3
   - high → 4
   - critical → 5
   - default → 3

## Key Insight

The SQL `$severity` was unquoted because severity is an INTEGER column. Passing "medium" caused `Parse error near line 1: no such column: medium`. The fix validates/converts input before SQL insertion.

## Tests Performed

- Numeric severity (4) → stored as 4 ✓
- Word "high" → stored as 4 ✓
- Word "critical" → stored as 5 ✓
- Default (empty) → stored as 3 ✓

## Related

- Original error: SQL parse error on non-numeric severity
- Heuristic H-15: bash vs tool tracking mismatch
