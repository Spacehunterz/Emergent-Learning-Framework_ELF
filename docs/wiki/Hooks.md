# Hooks Reference

ELF uses Claude Code's hooks system to inject context and validate actions at key points in the workflow.

## Hook Overview

| Hook | When It Fires | Purpose | ELF Usage |
|------|---------------|---------|-----------|
| `UserPromptSubmit` | After user sends message | Load baseline context | Golden rules, domain heuristics |
| `PreToolUse` | Before tool executes | Inject mid-stream context | **Semantic memory**, plan detection |
| `PostToolUse` | After tool succeeds | Validate outcomes | Learning loop, plan validation |
| `SubagentStart` | When spawning subagent | Context for subagent | (Future: Plan subagent context) |
| `SessionEnd` | Session terminates | Cleanup | Save session state |

---

## UserPromptSubmit Hook

**File:** `src/hooks/learning-loop/user_prompt_inject_context.py`

**Purpose:** Load ELF context at session start

**What it does:**
1. Queries building for golden rules
2. Loads domain-specific heuristics
3. Returns context as text (added to Claude's context)

**Example output:**
```markdown
🏢 Building Status
━━━━━━━━━━━━━━━━━━

# Task Context

{user's prompt}

---

# TIER 1: Golden Rules

1. Always validate inputs at system boundaries
2. Use Sequential Thinking for complex tasks
...

# TIER 2: Relevant Knowledge

## Domain: authentication
- [auth] Validate JWT tokens before use (85% confidence)
...
```

---

## PreToolUse Hook (Enhanced)

**File:** `src/hooks/learning-loop/pre_tool_semantic_memory.py`

**Purpose:** Inject relevant heuristics based on Claude's current thinking

**What it does:**
1. Reads conversation transcript
2. Extracts last thinking block (~1500 chars)
3. Embeds thinking content
4. Semantic search against heuristics
5. Detects plan mode context
6. Boosts relevant heuristics
7. Returns formatted context

**Special handling for Plan Mode:**
- Detects writing to `/plans/*.md`
- Detects planning intent in thinking
- Boosts Sequential Thinking, ADR patterns
- Shows special 🎯 formatting

**Example output (regular):**
```markdown
---
## [Mid-Stream Memory] Relevant Patterns Detected

### Golden Rules (Must Follow)
- **Always validate inputs**

### Relevant Heuristics
- [auth] Check JWT timing (85% confidence)
---
```

**Example output (plan mode):**
```markdown
---
## 🎯 [Plan Mode] Critical Heuristics

**These patterns are especially important for planning:**

### ⭐ GOLDEN RULES (Must Apply to Plan)
- **Use Sequential Thinking** (90% confidence)
  → Break down complex tasks into steps

### Relevant Patterns for This Plan
- [architecture] Create ADRs (80% confidence)
  [boosted: plan_pattern:architecture decision record]
---
```

---

## PostToolUse Hook

**File:** `src/hooks/learning-loop/post_tool_learning.py`

**Purpose:** Validate outcomes and close the learning loop

**What it does:**
1. Checks which heuristics were consulted
2. Validates if task succeeded
3. Updates heuristic confidence
4. Records failures/successes
5. **NEW:** Validates plan files

**Plan Validation:**
- Detects plan file writes (`.md` in `/plans/`)
- Reads plan content
- Checks if injected heuristics were addressed
- Warns if any are missing

**Example warning:**
```
⚠️ Plan Review: Unaddressed Heuristics

The following heuristics were relevant but may not have been addressed:
- Use Sequential Thinking before implementing critical changes
- Create Architecture Decision Records for major changes
```

---

## Hook Configuration

### Default ELF Hooks

```json
{
  "hooks": {
    "UserPromptSubmit": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python ~/.claude/emergent-learning/src/hooks/learning-loop/user_prompt_inject_context.py"
          }
        ]
      }
    ],
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

### Installation

**Automatic:**
```bash
./install.sh
# or
python scripts/install-hooks.py
```

**Manual:**
```bash
mkdir -p ~/.claude/hooks/PreToolUse
mkdir -p ~/.claude/hooks/PostToolUse

cp src/hooks/learning-loop/*.py ~/.claude/hooks/learning-loop/
chmod +x ~/.claude/hooks/learning-loop/*.py
```

---

## Troubleshooting

### Hooks not firing

```bash
# Check Claude Code settings
claude config get hooks

# Verify hook files exist
ls -la ~/.claude/hooks/*/

# Check permissions
chmod +x ~/.claude/hooks/*/*.py
```

### Hook timing out

Increase timeout in settings:
```json
{
  "hooks": {
    "PreToolUse": [{
      "hooks": [{
        "command": "python ...",
        "timeout": 60
      }]
    }]
  }
}
```

### Hook output not appearing

- Exit code must be 0 for output to be captured
- Use stderr for debug messages
- Use stdout for context injection

---

## Custom Hooks

You can add your own hooks alongside ELF hooks:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Write",
        "hooks": [
          {
            "type": "command",
            "command": "python ~/.claude/hooks/custom/my-hook.py"
          }
        ]
      }
    ]
  }
}
```

See [Claude Code Hooks Documentation](https://docs.anthropic.com/en/docs/claude-code/hooks) for full reference.
