# Golden Rules Auto-Sync Guide

## Overview

Golden Rules Auto-Sync keeps your golden rules consistent between the source markdown file and the ELF database. When you edit golden rules in markdown, the database automatically syncs—no manual updates needed.

## How It Works

```
You edit markdown               Post-tool hook detects             Database updates
golden-rules.md    -------->    file change via hash    -------->  heuristics table
    (30 rules)                                                      (30 rules)
```

**When sync happens:**
- After every tool execution (post-tool hook)
- After any tool use: Read, Write, Bash, etc.
- Automatically and silently

**What syncs:**
- Rule titles (used for matching)
- `is_golden` flag in database
- No manual action required

## For Users: Using Golden Rules

### Editing Golden Rules

Golden rules live in: `~/.claude/emergent-learning/memory/golden-rules.md`

**To add a new golden rule:**

1. Open `golden-rules.md`
2. Add a new section with proper format:

```markdown
## 31. Your New Rule Title
> Your rule summary here

**Why:** Brief explanation of why this rule matters.
**Domain:** category
**Confidence:** 1.00 | Validated: 0 | Violated: 0
```

3. Save the file
4. Use any tool (even a simple `ls` command)
5. **Sync happens automatically** - database updated

**To remove a golden rule:**

1. Delete the rule section from markdown
2. Use any tool
3. **Sync happens automatically** - database updated

### Checking Sync Status

**View current golden rules in database:**

```bash
python -c "
import sqlite3
from pathlib import Path
db = Path.home() / '.claude/emergent-learning/memory/index.db'
conn = sqlite3.connect(str(db))
cur = conn.cursor()
cur.execute('SELECT COUNT(*) FROM heuristics WHERE is_golden=1 AND status=\"active\"')
print(f'Golden rules in database: {cur.fetchone()[0]}')
conn.close()
"
```

**View rules in markdown:**

```bash
grep -c "^## " ~/.claude/emergent-learning/memory/golden-rules.md
```

These should match.

**Manual sync (if needed):**

```bash
python ~/.claude/emergent-learning/scripts/sync-golden-rules.py --verbose
```

## For New Users: First Setup

When you install ELF for the first time:

1. **Setup runs** - Hooks automatically installed
2. **First /checkin** - `[OK] Hooks verified` message appears
3. **Golden rules auto-sync enabled** - Automatically from now on

No manual configuration needed!

### Verify Hooks Are Installed

```bash
ls ~/.claude/hooks/PostToolUse/sync-golden-rules.py
```

Should show: `sync-golden-rules.py` exists

If missing, run:

```bash
python ~/.claude/emergent-learning/scripts/verify-hooks.py
```

## For Developers: Understanding the System

### Architecture

Three-layer sync system:

```
Layer 1: Markdown (source of truth)
    ↓ (sync detects changes)
Layer 2: Database (cached state)
    ↓ (query system uses)
Layer 3: Runtime (loaded via query --context)
```

### Key Components

**1. Markdown Source (`memory/golden-rules.md`)**
- Single source of truth
- Readable, versionable, git-friendly
- 30 golden rules as of v0.4.3

**2. Sync Script (`scripts/sync-golden-rules.py`)**
- Manual sync utility
- Extracts rule titles from markdown
- Finds matching heuristics in database
- Updates `is_golden` flags
- Can be run standalone

**3. Hook (`~/.claude/hooks/PostToolUse/sync-golden-rules.py`)**
- Runs after every tool execution
- Detects file changes via SHA256 hash
- Calls sync script if changes detected
- Tracks state in `investigation-state.json`

**4. Auto-Install (`scripts/install-hooks.py`)**
- Copies hook from `.hooks-templates/` to `~/.claude/hooks/`
- Called during setup
- Can be run manually anytime

**5. Verifier (`scripts/verify-hooks.py`)**
- Checks if hooks are installed
- Auto-installs missing hooks
- Called by `/checkin` command
- Safety net for new users

### How Sync Works

**Step-by-step:**

1. User edits `golden-rules.md` and saves
2. User runs any tool (automatic trigger)
3. Post-tool hook runs:
   - Computes SHA256 hash of markdown file
   - Compares with last known hash
   - If different, calls `sync-golden-rules.py`
4. Sync script:
   - Reads markdown file
   - Extracts rule titles via regex: `^## \d+\. (.+)$`
   - Queries database for all active heuristics
   - For each heuristic:
     - Check if title matches any markdown rule
     - Update `is_golden` flag if mismatch
5. Sync completes silently
6. Next time you run `/checkin`, new rules are visible

### Database Schema

Golden rules are stored in `heuristics` table:

```sql
SELECT
    id,
    rule,
    is_golden,
    status
FROM heuristics
WHERE is_golden=1 AND status='active'
ORDER BY id;
```

**Columns:**
- `rule` - The actual rule text (matched against markdown)
- `is_golden` - Boolean (1 = golden, 0 = regular heuristic)
- `status` - 'active' or 'dormant'

### File Structure

```
~/.claude/emergent-learning/
├── memory/
│   ├── golden-rules.md              ← Source of truth (edited by users)
│   └── index.db                     ← Database with heuristics table
├── scripts/
│   ├── sync-golden-rules.py         ← Manual sync utility
│   ├── install-hooks.py             ← Hook installer
│   └── verify-hooks.py              ← Hook verifier
├── .hooks-templates/
│   ├── README.md                    ← Hook documentation
│   └── PostToolUse/
│       └── sync-golden-rules.py     ← Template hook (versioned)
└── src/query/
    └── checkin.py                   ← Calls verify_hooks()
```

### Adding New Sync Hooks

To add another post-tool hook:

1. Create template: `.hooks-templates/PostToolUse/my-hook.py`
2. Implement your logic
3. Add to `verify-hooks.py` required hooks list
4. Commit to repo
5. Users auto-install on next setup/checkin

## Troubleshooting

### Golden Rules Not Syncing

**Symptom:** You edit markdown but database doesn't update

**Check:**

1. Hooks installed?
   ```bash
   ls ~/.claude/hooks/PostToolUse/sync-golden-rules.py
   ```

2. Run /checkin to auto-install if missing:
   ```bash
   /checkin
   ```

3. Manually sync:
   ```bash
   python ~/.claude/emergent-learning/scripts/sync-golden-rules.py --verbose
   ```

### Hook Permission Issues (Windows)

**Symptom:** `[WARN] Hook verification failed`

**Fix:**

```bash
chmod +x ~/.claude/hooks/PostToolUse/sync-golden-rules.py
```

### Stale Database State

**Symptom:** Database has wrong count after editing markdown

**Fix:**

```bash
python ~/.claude/emergent-learning/scripts/sync-golden-rules.py --verbose
```

This will resync everything.

### Hash Mismatch Issues

**Symptom:** Sync runs on every tool use (inefficient)

**Check:**

```bash
python ~/.claude/emergent-learning/scripts/verify-hooks.py
```

This should report "Hooks verified" with no output.

If hook is corrupt, reinstall:

```bash
python ~/.claude/emergent-learning/scripts/install-hooks.py --force
```

## Performance

**Sync speed:**
- Check file hash: <1ms
- Compare with stored hash: <1ms
- Database update (30 rules): 10-50ms
- **Total time: <100ms per tool use**

No noticeable impact on performance.

## Security

**Considerations:**

- Only markdown in `.claude/emergent-learning/memory/` is checked
- Hook runs as current user (same as Claude Code)
- Database transactions ensure atomicity
- No external network calls
- State file (`investigation-state.json`) is local only

## Future Enhancements

Potential improvements (not yet implemented):

- Multi-file sync support (sync multiple markdown docs)
- Validation rules (enforce domain requirements)
- Rollback on sync failures
- Conflict resolution (manual merge on divergence)
- Sync history/audit log

## Questions?

**For issues:**
1. Run `/checkin` to verify system health
2. Check logs in `~/.claude/hooks/PostToolUse/sync-golden-rules.py`
3. Check database: `python scripts/sync-golden-rules.py --verbose`

**For feature requests:**
- File issue on GitHub
- Document as ADR in `/docs/ADR.md`
