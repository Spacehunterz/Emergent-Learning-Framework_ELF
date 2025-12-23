# Configuration

## CLAUDE.md

The `~/.claude/CLAUDE.md` file contains instructions Claude follows. The framework installs a template that:

- Requires querying the building before tasks
- Lists the golden rules
- Explains how to record learnings

You can add your own instructions below the ELF section.

## settings.json

Hook configuration in `~/.claude/settings.json`:

```json
{
  "hooks": {
    "PreToolUse": [{
      "matcher": "Task",
      "hooks": [{
        "type": "command",
        "command": "python ~/.claude/emergent-learning/hooks/learning-loop/pre_tool_learning.py"
      }]
    }],
    "PostToolUse": [{
      "matcher": "Task",
      "hooks": [{
        "type": "command",
        "command": "python ~/.claude/emergent-learning/hooks/learning-loop/post_tool_learning.py"
      }]
    }]
  }
}
```

## Key Phrases

The CLAUDE.md template teaches Claude to respond to:

| Phrase | What It Does |
|--------|--------------|
| `check in` | Queries building, reports context |
| `query the building` | Same as check in |
| `what does the building know about X` | Searches for topic X |
| `record this failure: [lesson]` | Creates failure log |
| `record this success: [pattern]` | Documents success |
| `start experiment: [hypothesis]` | Tracks hypothesis |

## Automatic vs Manual Learning

**Automatic (via hooks):**
- Pre-task query injects relevant heuristics
- Post-task recording logs outcomes
- Confidence updates based on success/failure
- Trail laying tracks files touched

**Manual (via key phrases):**
- Major failures worth documenting
- Project-specific patterns
- Experiments you want to track
