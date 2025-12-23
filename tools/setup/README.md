# Emergent Learning Framework - Setup

This folder contains the configuration files and scripts to install the emergent learning framework.

**Default install path:** `~/.claude/emergent-learning` (set `ELF_BASE_PATH` to run from a different location).

## Quick Install

From the repository root:

```bash
# Mac/Linux
./install.sh

# Windows
.\install.ps1
```
Use PowerShell or CMD on Windows; Git Bash is not supported for the installer scripts.

## What Gets Installed

| Component | Destination | Purpose |
|-----------|-------------|---------|
| `CLAUDE.md` | `~/.claude/CLAUDE.md` | Main configuration - instructions for Claude |
| Commands | `~/.claude/commands/` | Slash commands like `/search`, `/checkin`, `/swarm` |
| Core Files | `~/.claude/emergent-learning/` | Query system, memories, dashboard backend |
| Hooks | `~/.claude/emergent-learning/hooks/` | Logic for pre/post task hooks |
| `settings.json` | `~/.claude/settings.json` | Configures Claude to use the ELF hooks |

## Manual Install

We strongly recommend using the installer script as it handles path configuration and virtual environments correctly.

If you must install manually, the high-level steps are:

1. Copy `templates/CLAUDE.md.template` to `~/.claude/CLAUDE.md`.
2. Copy `library/commands/*` to `~/.claude/commands/`.
3. Copy the entire repository `src` content to `~/.claude/emergent-learning/`.
4. Copy `tools/scripts/*` to `~/.claude/emergent-learning/scripts/`.
5. Create a Python virtual environment in `~/.claude/emergent-learning/.venv` and install `requirements.txt`.
6. Configure `~/.claude/settings.json` to add `PreToolUse` and `PostToolUse` hooks pointing to `~/.claude/emergent-learning/hooks/learning-loop`.

## What Each Component Does

### CLAUDE.md
The constitution. Instructs Claude to:
- Query the building at conversation start
- Follow golden rules
- Use the session memory system

### Slash Commands
- `/search` - Search session history
- `/checkin` - Manual building check-in
- `/swarm` - Multi-agent coordination

### Hooks (settings.json)
Configured in `settings.json`, these ensure that:
- **PreToolUse:** `pre_tool_learning.py` runs before tasks to provide context.
- **PostToolUse:** `post_tool_learning.py` runs after tasks to record outcomes.

## Customization

Edit `~/.claude/CLAUDE.md` after installation to:
- Change package manager preference (bun vs npm)
- Modify dashboard ports
- Add project-specific instructions
