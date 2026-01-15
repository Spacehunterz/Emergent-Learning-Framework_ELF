# emergent-learning Project

See `~/.claude/CLAUDE.md` for full ELF Integration Guide.

---

## Auto-Learning: [LEARNED:] Markers

When working in Task tool outputs (subagents), mark discoveries using inline markers to auto-record learnings:

```
[LEARNED:domain] The lesson or pattern discovered
```

**Format variations:**
- `[LEARNED:react] Always use refs for callbacks in useEffect`
- `[LEARNING:api] Retry logic should use exponential backoff`
- `[LEARN:general] Check file exists before reading`

**How it works:**
- Markers are auto-extracted from Task tool outputs by post-tool hooks
- If text contains "always", "never", "should", "must", "avoid", or "prefer" → recorded as **heuristic** (confidence: 0.5)
- Otherwise → recorded as **observation**

**When to use:**
- When a subagent discovers something worth remembering
- Quick inline capture without interrupting workflow
- Domain is optional (defaults to context-detected or "general")

---

## GIT REMOTES - READ THIS BEFORE PUSHING

- `origin` = **PUBLIC REPO** (Emergent-Learning-Framework_ELF) - PUSH HERE
- `private-backup` = private backup only - DO NOT PUSH unless explicitly asked

When user says "push" or "push to git", use: `git push origin`
