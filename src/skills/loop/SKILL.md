# /loop - Launch Ralph Loop Work Session

One-command autonomous work session starter. Automatically initializes PRD if needed, then spawns fresh Claude Code sessions to complete stories.

## Usage

```bash
/loop
```

That's it.

## What Happens

1. **Check PRD** - Looks for `prd.json`
2. **Auto-Init** - If missing, creates default PRD with 4 starter stories
3. **Start Ralph Loop** - Spawns fresh sessions to complete stories automatically

## How It Works

Each iteration:
- Ralph Loop finds next incomplete story
- Spawns fresh `claude-code` session
- Session reads story details, implements, tests, commits
- Session updates `progress.txt` with learnings
- Session exits (clean context)
- Ralph Loop continues to next story

## Your Flow

```
Turn on PC
  ↓
/loop
  ↓
Ralph spawns Session #1 → TASK-001 completes → exits
  ↓
Ralph spawns Session #2 → TASK-002 completes → exits
  ↓
Ralph spawns Session #3 → TASK-003 completes → exits
  ↓
All stories done → Ralph Loop exits
  ↓
Review progress.txt and git history
```

## No Manual Work

Once `/loop` runs:
- No more manual commands
- No more script running
- Ralph orchestrates everything
- Each session gets fresh, clean context
- No degradation at 100k tokens

## Customize Your PRD

Before running `/loop`, you can:

```bash
/prd create     # Define your own stories
/prd show       # Review current PRD
/prd validate   # Ensure it's valid
```

Then:

```bash
/loop
```

Ralph reads your custom PRD and executes.

## Interrupting

If you need to stop Ralph Loop:
- Press `Ctrl+C` to stop `ralph.sh`
- Stories in-progress stay marked as `in_progress`
- Run `/loop` again to resume from next story
- Ralph doesn't restart completed stories

## Monitoring

While Ralph Loop runs, check progress:

```bash
# In another terminal
cat progress.txt    # View learnings
cat prd.json        # Check story status
git log --oneline   # See implementations
```

## Auto-PRD on First Run

First time you run `/loop` with no `prd.json`:

```bash
/loop
```

Automatically creates default PRD:
- TASK-001: Project Setup
- TASK-002: Core Feature Implementation
- TASK-003: Testing and Quality
- TASK-004: Documentation and Release

Edit `prd.json` to customize, then next run uses your stories.

## Integration with ELF

- Sessions run with full ELF context (golden rules, learnings)
- Progress automatically feeds back to ELF memory
- Each session loads relevant patterns from golden-rules.md

## See Also

- `/start-work` - Same as /loop (alias)
- `/prd` - Manage PRD before running loop
- `/ralph` - Raw ralph.sh with options
- `progress.txt` - View all session learnings
- `library/guides/ralph-loop-guide.md` - Full architecture docs

---

**Philosophy:** One command to rule them all. `/loop` is your entry point to autonomous work. Ralph handles the rest.
