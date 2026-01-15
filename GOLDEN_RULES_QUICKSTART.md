# Golden Rules Auto-Sync - Quick Start

## TL;DR

Edit `~/.claude/emergent-learning/memory/golden-rules.md`, use any tool, and the database syncs automatically. That's it.

## 30 Second Overview

```
Edit markdown → Use any tool → Database auto-syncs
```

**No manual sync needed.** The post-tool hook detects changes and updates the database.

## Common Tasks

### Add a Golden Rule

```bash
# 1. Edit the file
nano ~/.claude/emergent-learning/memory/golden-rules.md

# 2. Add a new section (copy the format):
## 31. Your Rule Title Here
> Your rule summary

**Why:** Why this matters.
**Domain:** category
**Confidence:** 1.00 | Validated: 0 | Violated: 0

# 3. Save and use any tool
ls
# (Sync happens automatically)
```

### Check Sync Status

```bash
# Count rules in markdown
grep -c "^## " ~/.claude/emergent-learning/memory/golden-rules.md

# Count rules in database
python -c "
import sqlite3
from pathlib import Path
db = Path.home() / '.claude/emergent-learning/memory/index.db'
conn = sqlite3.connect(str(db))
cur = conn.cursor()
cur.execute('SELECT COUNT(*) FROM heuristics WHERE is_golden=1 AND status=\"active\"')
print(f'Golden rules: {cur.fetchone()[0]}')
conn.close()
"
```

These should match.

### Manual Sync

```bash
python ~/.claude/emergent-learning/scripts/sync-golden-rules.py
```

Run this if sync seems stuck (rare).

### Verify Hooks

```bash
python ~/.claude/emergent-learning/scripts/verify-hooks.py
```

Auto-installs missing hooks.

## How It Works (Simple Version)

1. **Markdown is source of truth**
   - You edit `golden-rules.md`
   - 30 golden rules live here

2. **Post-tool hook detects changes**
   - After any tool use (Read, Write, Bash, etc.)
   - Compares file hash to last known state
   - If changed: triggers sync

3. **Database updates automatically**
   - Sync script reads markdown
   - Matches rule titles in database
   - Updates `is_golden` flags
   - Silent and fast (<100ms)

4. **Query system uses updated data**
   - Next time you run `/checkin`
   - New rules are visible

## Troubleshooting

**Sync not working?**
```bash
/checkin    # Auto-installs hooks if missing
```

**Want to force sync?**
```bash
python ~/.claude/emergent-learning/scripts/sync-golden-rules.py --verbose
```

**Hook issues?**
```bash
python ~/.claude/emergent-learning/scripts/verify-hooks.py
```

## File Locations

| What | Where |
|------|-------|
| Golden Rules | `~/.claude/emergent-learning/memory/golden-rules.md` |
| Database | `~/.claude/emergent-learning/memory/index.db` |
| Sync Script | `~/.claude/emergent-learning/scripts/sync-golden-rules.py` |
| Hook | `~/.claude/hooks/PostToolUse/sync-golden-rules.py` |

## More Info

Full guide: `docs/guides/golden-rules-sync.md`

---

**One rule:** Edit markdown, use a tool, database stays in sync. That's all you need to know.
