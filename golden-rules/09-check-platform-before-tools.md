# Golden Rule 9: Check Platform Before Tool Use

> Read the environment block. Adapt tool selection and syntax to the actual platform.

**Why:** Claude defaults to Linux assumptions even when `Platform: win32` is shown. This causes silent failures, missed files, and wasted debugging time.

**Promoted:** 2025-12-02 (from swarm investigation of Windows tool compatibility)
**Validations:** 5 (comprehensive 5-agent investigation)

---

## The Rule

Before using ANY tool, check:
```
Platform: win32 → Windows adaptations needed
Platform: linux → Standard behavior
Platform: darwin → macOS behavior
```

## Windows Adaptations

| Tool | Adaptation |
|------|------------|
| **Glob** | Don't use - broken on Windows. Use `Bash: find` |
| **Read/Write/Edit/Grep** | Use `C:/Users/...` format only. No tilde, no `/c/` |
| **Bash** | Use freely - handles all path formats |
| **Symlinks** | Don't use `ln -s` - use copies |
| **chmod** | Skip - no effect on Windows |

## Quick Reference

```
~/.claude/emergent-learning/references/windows-tool-guide.md
```

## Anti-Pattern

```
# BAD: Using Glob with tilde on Windows
Glob pattern="~/.claude/emergent-learning/ceo-inbox/*"
Result: "No files found" (tilde not expanded)

# GOOD: Using Bash instead
ls ~/.claude/emergent-learning/ceo-inbox/
Result: Lists files correctly
```
