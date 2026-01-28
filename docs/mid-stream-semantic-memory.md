# Mid-Stream Semantic Memory

**Version:** 0.7.0  
**Status:** Active  
**Related Issues:** [#98 - Heuristics Not Applied During Plan Creation](https://github.com/Spacehunterz/Emergent-Learning-Framework_ELF/issues/98)

---

## Overview

Mid-Stream Semantic Memory is a game-changing enhancement to ELF's learning loop that injects relevant heuristics **during** Claude's workflow, not just at session start. By extracting Claude's thinking blocks and performing semantic similarity search, we surface the right patterns at the right time—even as context drifts from the original prompt.

### The Problem (Solved)

**Before:**
- Heuristics loaded once at `UserPromptSubmit`
- By tool 5, context has drifted
- Plan mode doesn't see relevant patterns
- Heuristics become "write-only" knowledge

**After:**
- Heuristics injected on **every** relevant tool use
- Semantic matching based on Claude's **current thinking**
- Special handling for **plan creation**
- Validation that heuristics were actually applied

---

## Features

### 1. Semantic Heuristic Injection (PreToolUse)

Extracts the last 1500 characters from Claude's most recent thinking block, embeds the intent, and performs semantic similarity search against the heuristics database.

**How it works:**
1. Hook fires before tool execution
2. Reads conversation transcript
3. Extracts thinking content
4. Embeds using `sentence-transformers` (all-MiniLM-L6-v2)
5. Searches heuristics DB for semantic similarity
6. Injects top-3 relevant heuristics via `additionalContext`

**Example:**
```
Claude thinks: "I need to handle the JWT token validation timing issue..."
↓
Hook embeds thinking
↓
Finds: "Always validate JWT tokens after user object loading" (0.87 similarity)
↓
Injects: [Mid-Stream Memory] JWT validation heuristic
↓
Claude applies pattern immediately
```

### 2. Plan Mode Detection & Boosting

Special handling when Claude is creating plans (addresses Issue #98).

**Detection triggers:**
- Writing to `~/.claude/plans/*.md`
- File names containing "plan", "roadmap", "architecture", "design"
- Thinking content mentioning "create a plan", "design document", etc.

**Heuristic boosting during planning:**
| Pattern | Boost | Reason |
|---------|-------|--------|
| Golden Rules | +20% | Constitutional importance |
| "Sequential Thinking" | +15% | Critical for planning |
| "Architecture Decision Record" | +15% | Planning best practice |
| "step by step" | +15% | Methodical approach |

**Special formatting:**
```markdown
---
## 🎯 [Plan Mode] Critical Heuristics

**These patterns are especially important for planning:**

### ⭐ GOLDEN RULES (Must Apply to Plan)
- **Always use Sequential Thinking** (90% confidence)
  → Break down complex tasks into steps before coding

### Relevant Patterns for This Plan
- [architecture] Create ADRs for major changes (85% confidence)
  [boosted: plan_pattern:architecture decision record]
---
```

### 3. Post-Tool Plan Validation

After a plan file is written, validates that injected heuristics were actually addressed.

**How it works:**
1. PostToolUse hook fires after Write/Edit
2. Checks if file is a plan (`.md` in `/plans/`)
3. Reads plan content
4. Checks if each injected heuristic is addressed
5. Warns if any are missing

**Example warning:**
```markdown
⚠️ **Plan Review: Unaddressed Heuristics**

The following heuristics were relevant but may not have been addressed:

- **Use Sequential Thinking before implementing critical changes**
  Break down complex tasks into steps before coding

- **Create Architecture Decision Records for major changes**
  Document architectural decisions for future reference

Consider updating the plan to incorporate these patterns.
```

### 4. Temporal Deduplication

Prevents the same heuristic from being injected repeatedly.

**Session state tracking:**
```json
{
  "recently_shown": {
    "heuristic_5": {
      "count": 2,
      "last_shown": "2026-01-28T13:45:00",
      "contexts": ["plan_writing", "code_edit"]
    }
  }
}
```

**Rules:**
- Skip if shown in last 3 tool calls
- Reset counter after 5 minutes
- Always show Golden Rules (they're worth repeating)

---

## Installation

### Prerequisites

```bash
# Install sentence-transformers (optional but recommended)
pip install sentence-transformers

# Without it, falls back to keyword-based matching
```

### Hook Installation

**Option 1: Automatic (Recommended)**
```bash
./install.sh
# or
python scripts/install-hooks.py --force
```

**Option 2: Manual**
```bash
# Copy semantic memory hook
cp src/hooks/learning-loop/pre_tool_semantic_memory.py \
   ~/.claude/hooks/PreToolUse/

chmod +x ~/.claude/hooks/PreToolUse/pre_tool_semantic_memory.py

# Verify installation
python scripts/verify-hooks.py
```

### Claude Code Settings

Enable thinking blocks in Claude Code so the hook has content to extract:

```json
// ~/.claude/settings.json
{
  "thinking": {
    "enabled": true,
    "show_in_context": true
  }
}
```

---

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ELF_SEMANTIC_THRESHOLD` | 0.65 | Minimum similarity score (0.0-1.0) |
| `ELF_THINKING_CHARS` | 1500 | Characters to extract from thinking |
| `ELF_MAX_HEURISTICS` | 3 | Max heuristics to inject per tool |
| `ELF_DEDUP_WINDOW` | 3 | Tool calls before showing again |

### Hook Configuration

```json
// ~/.claude/settings.json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Task|Bash|Grep|Read|Glob|Edit|Write|WebFetch|WebSearch",
        "hooks": [
          {
            "type": "command",
            "command": "python ~/.claude/emergent-learning/src/hooks/learning-loop/pre_tool_semantic_memory.py",
            "timeout": 30
          }
        ]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [
          {
            "type": "command",
            "command": "python ~/.claude/emergent-learning/src/hooks/learning-loop/post_tool_learning.py",
            "timeout": 30
          }
        ]
      }
    ]
  }
}
```

---

## Architecture

### Data Flow

```
┌─────────────────────────────────────────────────────────────┐
│  USER PROMPT                                                │
└──────────────┬──────────────────────────────────────────────┘
               │
               ▼
┌──────────────────────────┐
│  UserPromptSubmit Hook   │◄─── Golden Rules + Domain Heuristics
│  (Existing)              │     (One-time baseline)
└──────────────┬───────────┘
               │
               ▼
┌──────────────────────────┐
│  Claude Processes        │
│  - Generates thinking    │
│  - Plans tool use        │
└──────────────┬───────────┘
               │
               ▼
┌─────────────────────────────────────────────────────────────┐
│  PreToolUse Hook (ENHANCED)                                 │
│                                                             │
│  ┌─────────────────┐    ┌─────────────────┐                │
│  │ Read Transcript │    │ Extract Thinking│                │
│  │ (tool_use_id)   │───►│ (last 1500 chars│                │
│  └─────────────────┘    └────────┬────────┘                │
│                                  │                          │
│                                  ▼                          │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Plan Detection                                     │   │
│  │  - File path: /plans/*.md?                          │   │
│  │  - Thinking: "create a plan"?                       │   │
│  │  - Yes → Enable boosting + special formatting       │   │
│  └─────────────────────────────────────────────────────┘   │
│                                  │                          │
│                                  ▼                          │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Semantic Search                                    │   │
│  │  - Embed thinking (384-dim vector)                  │   │
│  │  - Cosine similarity vs heuristic embeddings        │   │
│  │  - Return top matches (> threshold)                 │   │
│  └─────────────────────────────────────────────────────┘   │
│                                  │                          │
│                                  ▼                          │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Hybrid Scoring                                     │   │
│  │  - Base: Semantic similarity (70%)                  │   │
│  │  - Boost: Planning patterns (+15%)                  │   │
│  │  - Boost: Golden Rules (+20%)                       │   │
│  └─────────────────────────────────────────────────────┘   │
│                                  │                          │
│                                  ▼                          │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Temporal Deduplication                             │   │
│  │  - Check session state                              │   │
│  │  - Skip if shown recently                           │   │
│  │  - Always allow Golden Rules                        │   │
│  └─────────────────────────────────────────────────────┘   │
│                                  │                          │
│                                  ▼                          │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Format & Inject                                    │   │
│  │  - Plan mode: 🎯 header, ⭐ Golden Rules            │   │
│  │  - Regular: Standard mid-stream format              │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
               │
               ▼
┌──────────────────────────┐
│  Tool Executes           │
│  (Claude has context)    │
└──────────────┬───────────┘
               │
               ▼
┌─────────────────────────────────────────────────────────────┐
│  PostToolUse Hook (ENHANCED)                                │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Is this a plan file?                               │   │
│  │  - Path contains /plans/?                           │   │
│  │  - Extension is .md?                                │   │
│  │  - Yes → Validate heuristics addressed              │   │
│  └─────────────────────────────────────────────────────┘   │
│                                  │                          │
│                                  ▼                          │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Read Plan Content                                  │   │
│  │  - Load written file                                │   │
│  │  - Extract key concepts                             │   │
│  └─────────────────────────────────────────────────────┘   │
│                                  │                          │
│                                  ▼                          │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Validate Heuristics                                │   │
│  │  - For each injected heuristic:                     │   │
│  │    - Extract key concepts from rule                 │   │
│  │    - Check if mentioned in plan                     │   │
│  │    - Track addressed vs missing                     │   │
│  └─────────────────────────────────────────────────────┘   │
│                                  │                          │
│                                  ▼                          │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Warn if Missing                                    │   │
│  │  - Generate warning message                         │   │
│  │  - List unaddressed heuristics                      │   │
│  │  - Suggest updates                                  │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
               │
               ▼
┌──────────────────────────┐
│  Continue Session        │
│  (Loop continues)        │
└──────────────────────────┘
```

### Database Integration

**Pre-computed Embeddings (Performance Optimization)**

```sql
-- Optional: Pre-compute heuristic embeddings
CREATE TABLE heuristic_embeddings (
    heuristic_id INTEGER PRIMARY KEY,
    embedding BLOB,           -- 384-dim float32 array
    model_version TEXT,       -- 'all-MiniLM-L6-v2'
    updated_at TIMESTAMP,
    FOREIGN KEY (heuristic_id) REFERENCES heuristics(id)
);
```

**Session State Schema**

```json
{
  "session_id": "uuid",
  "session_start": "2026-01-28T12:00:00",
  "heuristics_consulted": [1, 5, 23],
  "domains_queried": ["auth", "security"],
  
  "mid_stream_injections": [
    {
      "tool_use_id": "toolu_01ABC...",
      "heuristic_ids": [5, 12],
      "thinking_summary": "jwt token validation...",
      "context": "plan_writing",
      "timestamp": "2026-01-28T12:05:00"
    }
  ],
  
  "recently_shown": {
    "5": {"count": 2, "last_shown": "2026-01-28T12:05:00"},
    "12": {"count": 1, "last_shown": "2026-01-28T12:03:00"}
  },
  
  "pending_plan_validations": [
    {
      "plan_file": "~/.claude/plans/auth.md",
      "heuristic_ids": [5, 12],
      "injected_at": "2026-01-28T12:05:00"
    }
  ]
}
```

---

## Performance

### Latency Budget

| Operation | Time | Notes |
|-----------|------|-------|
| Read transcript | ~10ms | JSONL parse, last N lines |
| Extract thinking | ~5ms | Regex/string ops |
| Embed thinking | ~50ms | SentenceTransformer.encode() |
| Similarity search | ~20ms | Batch cosine similarity |
| Format output | ~5ms | String formatting |
| **Total** | **~90ms** | Well under 500ms limit |

### Optimizations

1. **Embedding Cache**: Heuristic embeddings cached in `~/.embedding_cache/`
2. **Lazy Loading**: Model loads on first use, then reused
3. **Async Initialization**: Background warmup on session start
4. **Graceful Degradation**: Falls back to keyword matching if model unavailable

---

## Troubleshooting

### Hook Not Firing

```bash
# Check hook is installed
ls -la ~/.claude/hooks/PreToolUse/

# Check it's executable
chmod +x ~/.claude/hooks/PreToolUse/pre_tool_semantic_memory.py

# Check Claude Code config
claude config get hooks
```

### No Thinking Blocks Extracted

```bash
# Verify thinking is enabled in Claude Code
cat ~/.claude/settings.json | grep -A5 thinking

# Check transcript format
head -5 ~/.claude/projects/*/session.jsonl
```

### High Latency (>500ms)

```bash
# Check if embeddings are cached
ls -la ~/.claude/emergent-learning/.embedding_cache/

# Pre-compute heuristic embeddings
python -c "
from src.query.semantic_search import SemanticSearcher
import asyncio

async def warmup():
    s = await SemanticSearcher.create()
    count = await s.compute_all_heuristic_embeddings()
    print(f'Pre-computed {count} embeddings')
    await s.cleanup()

asyncio.run(warmup())
"
```

### Missing Heuristics in Plans

```bash
# Check plan detection is working
# Add to hook: print(f"Plan detected: {is_planning}", file=sys.stderr)

# Verify heuristic has planning keywords
grep -i "sequential\|step by step\|adr\|architecture decision" memory/index.db
```

---

## Testing

```bash
# Run test suite
cd ~/clawd/elf-work
python test_plan_semantic_memory.py

# Expected output:
# ============================================================
# PRE-TOOL SEMANTIC MEMORY - TEST SUITE
# ============================================================
# ...
# RESULTS: 7 passed, 0 failed
# ============================================================
# ✓ ALL TESTS PASSED - Ready for implementation
```

---

## Contributing

See [CONTRIBUTING.md](../CONTRIBUTING.md) for guidelines.

### Adding New Plan Patterns

Edit `src/hooks/learning-loop/pre_tool_semantic_memory.py`:

```python
PLAN_INDICATORS = [
    "plan", "design document", "architecture",
    "roadmap", "strategy", "approach document",
    # Add your pattern here
    "your-new-pattern"
]
```

### Adding New Boost Patterns

```python
PLAN_BOOST_PATTERNS = [
    "sequential thinking",
    "architecture decision record",
    # Add your pattern here
    "your boost pattern"
]
```

---

## Changelog

### 0.7.0 (2026-01-28)
- ✨ Initial release
- ✨ Semantic heuristic injection
- ✨ Plan mode detection & boosting
- ✨ Post-tool plan validation
- ✨ Temporal deduplication
- ✨ Hybrid keyword + semantic scoring

---

## Related Documentation

- [Issue #98: Heuristics Not Applied During Plan Creation](https://github.com/Spacehunterz/Emergent-Learning-Framework_ELF/issues/98)
- [Hooks System](../../docs/architecture/hooks.md)
- [Semantic Search](../../src/query/semantic_search.py)
- [Learning Loop](../../src/hooks/learning-loop/README.md)

---

## Credits

Inspired by [@josh_ladner](https://x.com/josh_ladner/status/2016442693140775254)'s insight:

> "If you have semantic memory tied to your UserPromptSubmit hooks, you MUST ALSO include it in your PreToolUse hook. It will put your efficiency levels over 9,000."
