# Migration Guide

## v0.2.0 Async Migration (Breaking Change)

**v0.2.0** migrates QuerySystem to async using `peewee-aio` + `aiosqlite`.

### What Changed

| Before (v0.1.x) | After (v0.2.0) |
|-----------------|----------------|
| `qs = QuerySystem()` | `qs = await QuerySystem.create()` |
| `qs.query_by_domain(...)` | `await qs.query_by_domain(...)` |
| `qs.cleanup()` | `await qs.cleanup()` |

### Quick Migration

```python
# Before (v0.1.x)
from query import QuerySystem
qs = QuerySystem()
result = qs.build_context("task")

# After (v0.2.0)
import asyncio
from query import QuerySystem

async def main():
    qs = await QuerySystem.create()
    try:
        result = await qs.build_context("task")
    finally:
        await qs.cleanup()

asyncio.run(main())
```

### CLI Unchanged

The CLI handles async internally - no changes needed:
```bash
python -m query --context
python -m query --stats
```

### Performance

| Workload | Speedup |
|----------|---------|
| Pure DB queries | ~1.3x |
| Mixed I/O (DB + network) | ~2.9x |

See [query/MIGRATION.md](../query/MIGRATION.md) for detailed migration guide.

---

## From Plain Claude Code

**Step 1: Backup**
```bash
cp ~/.claude/CLAUDE.md ~/.claude/CLAUDE.md.backup
cp ~/.claude/settings.json ~/.claude/settings.json.backup
```

**Step 2: Install**
```bash
./install.sh
```

**Step 3: Merge custom instructions**
Add your custom CLAUDE.md content AFTER the ELF section.

**Step 4: Test**
```bash
claude
# Say "check in" - should query building
python ~/.claude/emergent-learning/query/query.py --stats
```

## Upgrading Versions

```bash
# 1. Backup
cp ~/.claude/emergent-learning/memory/index.db ~/elf-backup.db

# 2. Pull latest
cd /path/to/ELF-repo && git pull

# 3. Reinstall
./install.sh

# 4. Validate
python ~/.claude/emergent-learning/query/query.py --validate
```

## Team Setup

**Option 1: Individual instances (recommended)**

> **Note:** Export/import commands are planned but not yet implemented.
> For now, manually share heuristics by copying from `memory/heuristics/` markdown files
> or by sharing the `memory/index.db` database.

```bash
# PLANNED (not yet implemented):
# python query.py --export-heuristics > team-heuristics.json
# python query.py --import-heuristics team-heuristics.json

# Current workaround: Copy heuristic markdown files
cp ~/.claude/emergent-learning/memory/heuristics/*.md /shared/team-heuristics/
```

**Option 2: Project golden rules**
- Create `.claude/CLAUDE.md` in project repo
- Team members include project rules

## Rollback

**Full uninstall:**
1. Remove hooks from settings.json
2. Delete `~/.claude/emergent-learning/`
3. Restore CLAUDE.md.backup

**Partial disable:**
- Remove learning-loop from settings.json
- Keep database for later
