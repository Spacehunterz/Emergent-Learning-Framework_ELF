# Emergent Learning Framework - Setup

This folder contains the configuration files needed to fully use the Emergent Learning Framework with Claude Code.

## Quick Install

```bash
cd ~/.claude/emergent-learning/setup
chmod +x install.sh
./install.sh
```

## What Gets Installed

| File | Destination | Purpose |
|------|-------------|---------|
| `CLAUDE.md.template` | `~/.claude/CLAUDE.md` | Main configuration - tells Claude to query the building |
| `commands/*.md` | `~/.claude/commands/` | Slash commands like `/search`, `/checkin`, `/swarm` |
| `commands/*.py` | `~/.claude/commands/` | Python scripts powering the commands |
| `hooks/*.py` | `~/.claude/hooks/` | Enforcement hooks (golden rule enforcer) |
| `hooks/SessionStart/*.py` | `~/.claude/hooks/SessionStart/` | Startup hooks (auto-query, dashboard) |

## Manual Install

If you prefer to install manually:

1. Copy `CLAUDE.md.template` to `~/.claude/CLAUDE.md`
2. Copy contents of `commands/` to `~/.claude/commands/`
3. Copy contents of `hooks/` to `~/.claude/hooks/`

## What Each Component Does

### CLAUDE.md
The main configuration file that instructs Claude to:
- Query the building at the start of every conversation
- Follow golden rules
- Use the session memory system
- Start the dashboard when needed

### Slash Commands
- `/search` - Search through session history with natural language
- `/checkin` - Manual building check-in
- `/checkpoint` - Save current progress
- `/swarm` - Launch multi-agent coordination

### Hooks
- `golden-rule-enforcer.py` - Blocks Claude if it doesn't query the building
- `SessionStart/load-building.py` - Auto-queries on startup
- `SessionStart/start-dashboard.py` - Starts dashboard servers

## Customization

Edit `~/.claude/CLAUDE.md` after installation to:
- Change package manager preference (bun vs npm)
- Modify dashboard ports
- Add project-specific instructions

## Troubleshooting

**Claude doesn't query the building:**
- Check that `~/.claude/CLAUDE.md` exists
- Verify hooks are in `~/.claude/hooks/`

**Dashboard doesn't start:**
- Install dependencies: `pip install uvicorn fastapi` and `bun install`
- Check ports 8888 and 3001 are available

**/search doesn't work:**
- Ensure `session-search.py` is in `~/.claude/commands/`
- Check Python 3 is available
