# /start-work - Begin Autonomous Work Session

Starts a complete Ralph Loop work session with automatic PRD initialization.

## What It Does

1. **Checks for PRD** - Looks for `prd.json` in project root
2. **Auto-Initialize** - If missing, runs init-ralph.sh to create default PRD
3. **Start Ralph Loop** - Spawns fresh Claude Code sessions to complete stories

## Usage

```bash
/start-work
```

That's it. Everything else is automatic.

## What Happens

```
1. Check: Is there a prd.json?
   ✓ Yes  → Continue to Ralph Loop
   ✗ No   → Auto-create with defaults

2. Ralph Loop starts:
   - Reads prd.json
   - Finds incomplete stories
   - Spawns fresh session per story
   - Each session implements, tests, commits
   - Continues until all done

3. Progress tracked:
   - progress.txt: Append-only learnings
   - prd.json: Story completion status
   - git history: All implementations
```

## No PRD? No Problem

If you don't have a PRD:

```bash
/start-work
```

start-work automatically creates one with sensible defaults:
- TASK-001: Project Setup
- TASK-002: Core Feature
- TASK-003: Testing
- TASK-004: Documentation

Edit `prd.json` to customize stories before next run.

## With Existing PRD

If you already have `prd.json`:

```bash
/start-work
```

Ralph Loop reads it and continues from where it left off.

## Advanced: Customize Before Starting

```bash
# Edit your PRD first
nano prd.json

# Then start work
/start-work
```

## Integration with ELF

- Progress automatically feeds learnings to ELF
- Stories can reference Golden Rules
- Each session loads relevant context from memory

## Exit & Resume

Ralph Loop can be interrupted:
- Press Ctrl+C to stop current ralph.sh
- Stories marked in-progress stay in-progress
- Run `/start-work` again to resume from next story

## See Also

- `/prd` - Create/edit PRD manually
- `/ralph` - Raw ralph.sh command with options
- `progress.txt` - View learnings from all sessions

---

**Philosophy:** One command to rule them all. start-work handles setup, initialization, and orchestration. You focus on work, Ralph handles the details.
