# ELF Hook Templates

This directory contains templates for Claude Code hooks that enhance the ELF experience.

## Hooks Included

### PostToolUse/sync-golden-rules.py
**Purpose:** Auto-sync golden-rules.md with the database after each tool use

**What it does:**
- Detects changes to `memory/golden-rules.md`
- Syncs rule definitions to the heuristics database
- Keeps markdown and database in sync automatically

**When it runs:** After every tool execution

---

## Installation

### Automatic (Recommended)
Hooks are installed automatically during:
1. **Initial ELF setup**: `bash install.sh`
2. **First checkin**: `/checkin` command
3. **Manual install**: `python scripts/install-hooks.py`

### Manual Installation
```bash
# Install all hooks
python ~/.claude/emergent-learning/scripts/install-hooks.py

# Install with verbose output
python ~/.claude/emergent-learning/scripts/install-hooks.py --verbose

# Force reinstall existing hooks
python ~/.claude/emergent-learning/scripts/install-hooks.py --force
```

### Verification
```bash
# Check if all hooks are installed
python ~/.claude/emergent-learning/scripts/verify-hooks.py
```

---

## How Hooks Work

Hooks are shell scripts that run at specific points in the Claude Code workflow:

**Hook Locations:**
- `~/.claude/hooks/PostToolUse/` - Run after tool execution
- `~/.claude/hooks/PreToolUse/` - Run before tool execution
- `~/.claude/hooks/UserPromptSubmit/` - Run after user message
- `~/.claude/hooks/SessionEnd/` - Run at session end

**Exit Codes:**
- `0` - Success (hook output is captured)
- `1+` - Failure (hook output is not captured)

---

## For New Users

When you first run ELF:
1. **Setup** automatically installs hooks
2. **Checkin** verifies hooks are installed (safety net)
3. **Auto-sync** starts working immediately

No manual action needed!

---

## Troubleshooting

**Hooks not running?**
- Check they're executable: `ls -la ~/.claude/hooks/PostToolUse/`
- Verify hooks directory exists: `ls ~/.claude/hooks/`
- Reinstall: `python ~/.claude/emergent-learning/scripts/install-hooks.py --force`

**Auto-sync not working?**
- Check hook was installed: `ls ~/.claude/hooks/PostToolUse/sync-golden-rules.py`
- Run verify script: `python ~/.claude/emergent-learning/scripts/verify-hooks.py`
- Check permissions: `chmod +x ~/.claude/hooks/PostToolUse/sync-golden-rules.py`

---

## Developing New Hooks

1. Create hook in `.hooks-templates/[HOOK_TYPE]/my-hook.py`
2. Test locally in `~/.claude/hooks/[HOOK_TYPE]/`
3. Commit to repo
4. Users will auto-install on next setup/checkin

