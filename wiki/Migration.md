# Migration Guide

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
```bash
# Export valuable heuristics
python query.py --export-heuristics > team-heuristics.json

# Team members import
python query.py --import-heuristics team-heuristics.json
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
