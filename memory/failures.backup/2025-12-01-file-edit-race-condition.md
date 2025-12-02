# Failure: Repeated Edit Tool Failures Due to External File Modification

**Date:** 2025-12-01
**Domain:** debugging, process
**Severity:** Medium
**Tags:** edit-tool, race-condition, atomic-operations

## What Happened
Tried to edit face_overlay_amplitude.py using the Edit tool. Got "File has been unexpectedly modified" error 4 times in a row. Each time I re-read the file and tried again, same error.

## Expected vs Actual
- **Expected:** Edit tool modifies file successfully
- **Actual:** File kept getting modified between read and write (external process or IDE auto-save?)

## Root Cause Analysis
Something external was touching the file - likely VS Code auto-save, file watcher, or background process. The Edit tool requires file content to match exactly between read and write.

## Contributing Factors
- Didn't recognize the pattern after first failure
- Kept trying same approach 4 times
- Should have switched strategy after 2nd failure max

## Heuristic Extracted
> After 2 failed edits to same file, switch to atomic approach: write a patch script and execute it.

## Prevention
1. On first "unexpectedly modified" error, check for external processes touching the file
2. After 2 failures, use Python/script to make atomic changes
3. Consider: `Write to temp file -> atomic rename` pattern

## The Fix That Worked
Created `apply_lipsync_patch.py` that:
1. Reads entire file
2. Makes all replacements in memory
3. Writes entire file atomically
4. Executed via `python apply_lipsync_patch.py`

## Related
- Golden Rule #4: Break It Before Shipping It
- Golden Rule #1: Query Before Acting (should have checked for known issues)
