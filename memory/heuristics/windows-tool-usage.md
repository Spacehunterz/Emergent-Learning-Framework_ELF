# Heuristic: Windows Platform Tool Usage

**Domain**: tools, windows, environment
**Confidence**: 0.8
**Created**: 2025-12-02
**Validated**: 1

## Pattern

On Windows (MSYS2/Git Bash), prefer Bash over Glob for path operations.

## Why

- Glob tool does NOT expand `~` on Windows
- Bash (via MSYS2) DOES expand `~` correctly
- Claude defaults to Linux assumptions despite environment info showing `Platform: win32`

## Rule

**Before using ANY tool, check the platform:**
```
Platform: win32 → Windows adaptations needed
```

**On Windows:**
1. Use Bash `ls` instead of Glob for paths with `~`
2. Use full Windows paths (`C:/Users/...`) if using Glob
3. Remember MSYS2 translates paths - `/c/Users/` = `C:\Users\`

## Anti-Pattern

```
# BAD - Glob doesn't expand ~
Glob pattern: ~/.claude/emergent-learning/ceo-inbox/*
Result: "No files found"

# GOOD - Bash expands ~ via MSYS2
Bash: ls ~/.claude/emergent-learning/ceo-inbox/
Result: Lists files correctly
```

## Validation

- 2025-12-02: Missed 3 CEO inbox files due to Glob + `~` on Windows
