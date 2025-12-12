# Session Tools Reference

Detailed documentation for session history and search tools.

## get_last_prompts.py

Retrieves user prompts from previous Claude Code sessions.

### Basic Usage

```bash
# Last 5 prompts from most recent session
python ~/.claude/emergent-learning/sessions/get_last_prompts.py

# Last 10 prompts
python ~/.claude/emergent-learning/sessions/get_last_prompts.py --limit 10

# Search across multiple recent sessions
python ~/.claude/emergent-learning/sessions/get_last_prompts.py --all-sessions

# JSON output for scripting
python ~/.claude/emergent-learning/sessions/get_last_prompts.py --json
```

### Options

| Flag | Description |
|------|-------------|
| `--limit N` | Number of prompts to retrieve (default: 5) |
| `--all-sessions` | Search across multiple recent sessions |
| `--json` | Output as JSON |
| `--project-dir PATH` | Override project directory path |

### Example Output

```
==================================================
  LAST 5 USER PROMPTS
==================================================

[1] 2025-12-12 09:15:01
    fix the authentication bug in login.py

[2] 2025-12-12 09:22:34
    add unit tests for the fix

[3] 2025-12-12 09:45:12
    commit and push
```

---

## search.py

Natural language search across session logs (tool usage history).

### Basic Usage

```bash
# Search for specific work
python ~/.claude/emergent-learning/sessions/search.py "auth bug we fixed"

# Search recent history
python ~/.claude/emergent-learning/sessions/search.py "what failed yesterday" --days 1

# Limit results
python ~/.claude/emergent-learning/sessions/search.py "database migrations" --limit 5

# JSON output
python ~/.claude/emergent-learning/sessions/search.py "grep searches" --json
```

### Options

| Flag | Description |
|------|-------------|
| `--days N` | Number of days to search back (default: 7) |
| `--limit N` | Maximum number of results (default: 10) |
| `--json` | Output results as JSON |
| `--debug` | Show debug information |

### What It Searches

The search indexes:
- Tool names (Bash, Read, Edit, Grep, etc.)
- Input summaries (what was requested)
- Output summaries (what was returned)
- Outcomes (success/failure)

### Search Keywords

Certain words map to outcome searches:
- `failed`, `failing`, `broke`, `broken`, `crashed` → searches failures
- `succeeded`, `worked`, `passed` → searches successes

---

## How Sessions Are Logged

Session data comes from two sources:

1. **Claude Code history files** (`~/.claude/projects/*/[session-id].jsonl`)
   - Contains full conversation: user prompts and assistant responses
   - Used by `get_last_prompts.py`

2. **Framework session logs** (`~/.claude/emergent-learning/sessions/logs/`)
   - Contains tool usage summaries
   - Used by `search.py`
   - Lighter weight, designed for searchability

---

## Token Usage

| Operation | Approximate Tokens |
|-----------|-------------------|
| Last 5 prompts | ~500 |
| Last 20 prompts | ~2,000 |
| Full day (heavy user) | ~20,000 |
| Search results (10) | ~1,500 |

Control token usage with `--limit` flag.
