<p align="center">
  <img src="assets/header.jpg" alt="Emergent Learning Framework" width="100%">
</p>

# Emergent Learning Framework

> Persistent memory and pattern tracking for Claude Code sessions.

Claude Code learns from your failures and successes, building institutional knowledge that persists across sessions. Patterns strengthen automatically. Install once, watch knowledge compound over weeks.

## Install

```bash
./install.sh              # Mac/Linux
./install.ps1             # Windows
```

## First Use: Say "check in"

**Every session, start with `check in`.** This is the most important habit:

```
You: check in

Claude: [Queries building, starts dashboard, returns golden rules + heuristics]
```

**What "check in" does:**
- **First time ever:** Installs hooks, initializes database, starts dashboard
- **Start of session:** Loads knowledge, starts dashboard at http://localhost:3001 (Ctrl+click to open)
- **When stuck:** Searches for relevant patterns that might help
- **Before closing:** Ensures learnings are captured (CYA - cover your ass)

**When to check in:**
| Moment | Why |
|--------|-----|
| Start of every session | Load context, start dashboard, prevent repeating mistakes |
| When you hit a problem | See if building knows about this issue |
| Before closing session | Ensure learnings are captured |

## Core Features

| Feature | What It Does |
|---------|--------------|
| **Persistent Learning** | Failures and successes recorded to SQLite, survive across sessions |
| **Heuristics** | Patterns gain confidence through validation (0.0 -> 1.0) |
| **Golden Rules** | High-confidence heuristics promoted to constitutional principles |
| **Pheromone Trails** | Files touched by tasks tracked for hotspot analysis |
| **Coordinated Swarms** | Multi-agent workflows with specialized personas |
| **Local Dashboard** | Visual monitoring at http://localhost:3001 (no API tokens used) |
| **Cross-Session Continuity** | Pick up where you left off - search what you asked in previous sessions. Lightweight retrieval (~500 tokens), or ~20k for heavy users reviewing full day |

### Hotspots
![Hotspots](assets/Hotspots.png)
Treemap of file activity - see which files get touched most and spot anomalies at a glance.

### Graph
![Graph](assets/graph.png)
Interactive knowledge graph showing how heuristics connect across domains.

### Analytics
![Analytics](assets/analytics.png)
Track learning velocity, success rates, and confidence trends over time.

### Cross-Session Continuity

Ever close a session and forget what you were working on? This solves that.

**The Problem:** Claude Code sessions are ephemeral. Close the terminal, lose the context. You start fresh every time, re-explaining what you were doing.

**The Solution:** Session history is now searchable. Pick up exactly where you left off.

```bash
# What did I ask last session?
python ~/.claude/emergent-learning/sessions/get_last_prompts.py

# Last 10 prompts across sessions
python ~/.claude/emergent-learning/sessions/get_last_prompts.py --all-sessions --limit 10

# Search session logs for specific work
python ~/.claude/emergent-learning/sessions/search.py "auth bug we fixed"
python ~/.claude/emergent-learning/sessions/search.py "what failed yesterday" --days 1
```

**Example Output:**
```
==================================================
  LAST 5 USER PROMPTS
==================================================

[1] 2025-12-12 06:36:01
    check in

[2] 2025-12-12 06:39:24
    we have better memory now right?

[3] 2025-12-12 06:41:26
    no we added a way to not lose any progress even if session closes
```

**Token Usage:**
- Quick lookup (last 5 prompts): ~500 tokens
- Full day review for heavy users: ~20k tokens
- You control how much to retrieve with `--limit`

## How It Works

```
+---------------------------------------------------+
|              The Learning Loop                    |
+---------------------------------------------------+
|  QUERY   ->  Check building for knowledge         |
|  APPLY   ->  Use heuristics during task           |
|  RECORD  ->  Capture outcome (success/failure)    |
|  PERSIST ->  Update confidence scores             |
|                    |                              |
|         (cycle repeats, patterns strengthen)      |
+---------------------------------------------------+
```

## Key Phrases

| Say This | What Happens |
|----------|--------------|
| `check in` | Start dashboard, query building, show golden rules + heuristics |
| `query the building` | Same as check in |
| `what does the building know about X` | Search for topic X |
| `record this failure: [lesson]` | Create failure log |
| `record this success: [pattern]` | Document what worked |

## Quick Commands

```bash
# Check what has been learned
python ~/.claude/emergent-learning/query/query.py --stats

# Start dashboard manually (if needed)
cd ~/.claude/emergent-learning/dashboard-app && ./run-dashboard.sh

# Multi-agent swarm (Pro/Max plans)
/swarm investigate the authentication system
```

## Swarm Agents

| Agent | Role |
|-------|------|
| **Researcher** | Deep investigation, gather evidence |
| **Architect** | System design, big picture |
| **Skeptic** | Break things, find edge cases |
| **Creative** | Novel solutions, lateral thinking |

## Documentation

Full documentation in the [Wiki](https://github.com/Spacehunterz/Emergent-Learning-Framework_ELF/wiki):

- [Installation](https://github.com/Spacehunterz/Emergent-Learning-Framework_ELF/wiki/Installation) - Prerequisites, options, troubleshooting
- [Configuration](https://github.com/Spacehunterz/Emergent-Learning-Framework_ELF/wiki/Configuration) - CLAUDE.md, settings.json, hooks
- [Dashboard](https://github.com/Spacehunterz/Emergent-Learning-Framework_ELF/wiki/Dashboard) - Tabs, stats, themes
- [Swarm](https://github.com/Spacehunterz/Emergent-Learning-Framework_ELF/wiki/Swarm) - Multi-agent coordination, blackboard pattern
- [CLI Reference](https://github.com/Spacehunterz/Emergent-Learning-Framework_ELF/wiki/CLI-Reference) - All query commands
- [Golden Rules](https://github.com/Spacehunterz/Emergent-Learning-Framework_ELF/wiki/Golden-Rules) - How to customize principles
- [Migration](https://github.com/Spacehunterz/Emergent-Learning-Framework_ELF/wiki/Migration) - Upgrading, team setup
- [Architecture](https://github.com/Spacehunterz/Emergent-Learning-Framework_ELF/wiki/Architecture) - Database schema, hooks system
- [Token Costs](https://github.com/Spacehunterz/Emergent-Learning-Framework_ELF/wiki/Token-Costs) - Usage breakdown, optimization

## Plan Compatibility

| Plan | Core + Dashboard | Swarm |
|------|------------------|-------|
| Free | Yes | No |
| Pro ($20) | Yes | Yes |
| Max ($100+) | Yes | Yes |

## Links

- [Claude Code Docs](https://docs.anthropic.com/en/docs/claude-code)
- [Hooks System](https://docs.anthropic.com/en/docs/claude-code/hooks)
- [Issues & Support](https://github.com/Spacehunterz/Emergent-Learning-Framework_ELF/issues)

## License

MIT License

<a href="https://www.buymeacoffee.com/Spacehunterz">
  <img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" alt="Buy Me A Coffee" width="150">
</a>
