# Heuristic: Script Patching Hygiene

## Domain
Shell Scripts, Security Patches

## Pattern
When adding code to shell scripts (especially security patches), naive find-and-insert can break function boundaries.

## Anti-pattern Found
```bash
log() {
    local level="$1"
# <-- SECURITY PATCH INSERTED HERE (WRONG!)
# This breaks the function completely
    shift
    ...
}
```

## Solution
1. Always verify patch location is OUTSIDE function bodies
2. Test script immediately after patching
3. Use Python for complex edits (more reliable than sed on Windows)
4. Keep backups before patching

## Confidence
0.95

## Source
2025-12-04 - Fixed record-heuristic.sh that was broken by bad security patches
