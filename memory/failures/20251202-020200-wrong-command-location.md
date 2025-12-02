# Failure: Wrong Command Location

**Date:** 2025-12-02
**Severity:** 3
**Domain:** plugins, commands

## What Happened

Created `/swarm` command at `~/.claude/plugins/agent-coordination/commands/swarm.md` but Claude Code doesn't discover commands from plugin folders.

User ran `/swarm` in new window → "Unknown slash command: swarm"

## Root Cause

Assumed Claude Code has a plugin system that auto-discovers commands from `~/.claude/plugins/*/commands/`. It doesn't.

Claude Code only looks for commands in:
- `~/.claude/commands/` (global)
- `.claude/commands/` (project-local)

## Fix Applied

Copied command to correct location:
```bash
cp ~/.claude/plugins/agent-coordination/commands/swarm.md ~/.claude/commands/swarm.md
```

## Heuristic

> Claude Code commands must be in `~/.claude/commands/` or `.claude/commands/` - there is no plugin auto-discovery for commands.

## Prevention

Before creating custom commands, verify the correct location. Don't assume plugin patterns from other systems apply to Claude Code.
