# Heuristic: Windows Platform Awareness

**Domain**: tools, windows, platform
**Confidence**: 0.95
**Created**: 2025-12-02
**Validated**: 5 (swarm investigation)

## Pattern

Before using ANY tool, check the environment block for platform info and adapt accordingly.

## The Rule

**On Windows (MSYS2/Git Bash):**
1. **Bash tool** accepts ALL path formats - use liberally
2. **Python tools** (Read/Write/Edit/Grep/Glob) require `C:/Users/...` format
3. **Never** use tilde (`~`) or MSYS2 (`/c/`) paths with Python tools
4. **Glob tool** is broken - use `Bash: find` or `Bash: ls` instead
5. **Symlinks** don't work - use copies or hard links
6. **chmod** has no effect - just run scripts with their interpreter

## Quick Check

```
Platform: win32 → Adapt tool usage
Platform: linux/darwin → Standard behavior
```

## Reference

Full guide: `~/.claude/emergent-learning/references/windows-tool-guide.md`

## Why This Matters

The CEO spent significant time debugging issues caused by Linux assumptions on Windows. This is preventable with platform awareness.

## Promotion Candidate

This should be considered for Golden Rule status after further validation.
