# Mid-Stream Semantic Memory

> **Game Changer Alert:** This feature addresses the #1 issue with heuristic-based learning—context drift. By injecting relevant heuristics based on Claude's **current thinking** (not just the initial prompt), we keep knowledge fresh and actionable.

## Quick Start

```bash
# Install or update hooks
python scripts/install-hooks.py --force

# Verify installation
python scripts/verify-hooks.py
```

That's it. The hook runs automatically on every tool use.

---

## What Problem Does This Solve?

### The Old Way (Issue #98)

```
User: "Fix the auth bug"
  ↓
[Session Start] Heuristics shown (forgotten 5 minutes later)
  ↓
Claude works for 10 minutes...
  ↓
[Tool 5] Claude enters Plan Mode (Shift+Tab)
  ↓
❌ Heuristics scrolled out of context
  ↓
Plan created WITHOUT considering "Sequential Thinking" rule
  ↓
User frustrated: "Why didn't you remember that?!"
```

### The New Way (Mid-Stream Memory)

```
User: "Fix the auth bug"
  ↓
[Session Start] Heuristics shown (baseline)
  ↓
Claude works...
  ↓
[Tool 5] Claude thinks "I should plan this auth refactor..."
  ↓
✅ Hook fires: Extracts thinking → Semantic search
  ↓
✅ Finds: "Use Sequential Thinking before critical changes"
  ↓
✅ Injects: [🎯 Plan Mode] Sequential Thinking rule
  ↓
Plan created WITH proper methodology
  ↓
User happy: "Perfect, that's exactly what I needed"
```

---

## How It Works

### 1. Thinking Extraction

The hook reads Claude's conversation transcript and extracts the last ~1500 characters from the most recent thinking block.

**What are thinking blocks?**
When Claude reasons through a problem, it generates internal thinking (like "Hmm, I should validate this input first..."). This content is rich with intent and context.

### 2. Semantic Embedding

The thinking content is converted to a 384-dimensional vector using `sentence-transformers` (all-MiniLM-L6-v2 model).

**Example:**
```
Thinking: "I need to handle the JWT timing issue..."
Embedding: [0.23, -0.15, 0.88, ...] (384 dims)
```

### 3. Similarity Search

This embedding is compared against pre-computed embeddings of all heuristics in the database using cosine similarity.

```
Heuristic: "Always validate JWT tokens after user load"
Embedding: [0.25, -0.12, 0.85, ...] (384 dims)
Similarity: 0.87 (very relevant!)
```

### 4. Smart Filtering

Results are filtered and boosted:
- **Threshold**: Only show heuristics > 0.65 similarity
- **Deduplication**: Don't show same heuristic 3x in a row
- **Boosting**: Golden Rules +20%, plan patterns +15%
- **Limit**: Max 3 heuristics to avoid token bloat

### 5. Context Injection

The hook returns JSON with `additionalContext`:

```json
{
  "decision": "approve",
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "additionalContext": "\n---\n## [Mid-Stream Memory]...\n---\n"
  }
}
```

Claude receives this context immediately before using the tool.

---

## Special: Plan Mode

When Claude is creating plans, the system activates special handling:

### Detection

Triggers on:
- Writing to `~/.claude/plans/*.md`
- Files with "plan", "roadmap", "architecture" in name
- Thinking containing "create a plan", "design document"

### Boosting

These heuristics get score boosts during planning:

| Heuristic Type | Boost |
|----------------|-------|
| Golden Rules | +20% |
| Sequential Thinking | +15% |
| Architecture Decision Records | +15% |
| Step-by-step patterns | +15% |

### Formatting

Plan mode shows special formatting:

```markdown
---
## 🎯 [Plan Mode] Critical Heuristics

**These patterns are especially important for planning:**

### ⭐ GOLDEN RULES (Must Apply to Plan)
- **Always use Sequential Thinking** (90% confidence)
  → Break down complex tasks into steps before coding
---
```

### Validation

After the plan is written, the post-tool hook validates that injected heuristics were actually addressed. If not, it warns:

```
⚠️ Plan Review: Unaddressed Heuristics

The following heuristics were relevant but may not have been addressed:
- Use Sequential Thinking before implementing critical changes
- Create Architecture Decision Records for major changes
```

---

## Configuration

### Environment Variables

```bash
# Minimum similarity threshold (0.0 - 1.0)
export ELF_SEMANTIC_THRESHOLD=0.65

# Characters to extract from thinking
export ELF_THINKING_CHARS=1500

# Max heuristics per injection
export ELF_MAX_HEURISTICS=3

# Skip if shown in last N tool calls
export ELF_DEDUP_WINDOW=3
```

### Claude Code Settings

```json
{
  "hooks": {
    "PreToolUse": [{
      "matcher": "Task|Bash|Grep|Read|Edit|Write",
      "hooks": [{
        "type": "command",
        "command": "python ~/.claude/emergent-learning/src/hooks/learning-loop/pre_tool_semantic_memory.py",
        "timeout": 30
      }]
    }]
  }
}
```

---

## FAQ

**Q: Does this replace the UserPromptSubmit hook?**
A: No. UserPromptSubmit provides baseline context. PreToolUse provides mid-stream context. They work together.

**Q: What if sentence-transformers isn't installed?**
A: The hook gracefully degrades to keyword-based matching. Install `sentence-transformers` for full semantic search.

**Q: Will this slow down Claude?**
A: No. Total hook time is ~90ms (well under 500ms limit). Embeddings are cached.

**Q: Does it work with Plan subagents?**
A: Yes, via the standard PreToolUse hook. (SubagentStart hook coming in future release.)

**Q: Can I disable plan mode detection?**
A: Yes, set `ELF_PLAN_DETECTION=false` (not yet implemented—request if needed).

---

## Troubleshooting

**Hook not firing?**
```bash
# Check installation
ls -la ~/.claude/hooks/PreToolUse/

# Check permissions
chmod +x ~/.claude/hooks/PreToolUse/pre_tool_semantic_memory.py

# Test manually
echo '{"tool_name":"Write","tool_input":{"file_path":"test.py"}}' | \
  python ~/.claude/hooks/PreToolUse/pre_tool_semantic_memory.py
```

**No heuristics being injected?**
- Verify thinking blocks are enabled in Claude Code
- Check that heuristics exist: `python -m query --stats`
- Lower threshold: `ELF_SEMANTIC_THRESHOLD=0.5`

**Too many/few heuristics?**
- Adjust `ELF_MAX_HEURISTICS` (default: 3)
- Adjust `ELF_SEMANTIC_THRESHOLD` (default: 0.65)

---

## See Also

- [Issue #98 - Heuristics Not Applied During Plan Creation](https://github.com/Spacehunterz/Emergent-Learning-Framework_ELF/issues/98)
- [Semantic Search Implementation](../src/query/semantic_search.py)
- [Hooks Architecture](./Hooks-Architecture)
- [Full Documentation](../docs/mid-stream-semantic-memory.md)
