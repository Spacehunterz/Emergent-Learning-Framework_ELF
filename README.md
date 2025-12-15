<p align="center">
  <img src="assets/header.gif" alt="Emergent Learning Framework" width="100%">
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

**Auto-Setup on First Check-In:**
- **New user:** Everything installs automatically - config, commands, hooks
- **Existing CLAUDE.md:** Selection boxes to choose merge/replace/skip
- **Already configured:** Proceeds normally

**What "check in" does:**
- **First time ever:** Auto-installs config, hooks, /search, /checkin, /swarm commands
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
| **Session History** | Browse all Claude Code sessions in dashboard - search, filter by project/date, expand to see full conversations |
| **Cross-Session Continuity** | Pick up where you left off - search what you asked in previous sessions. Lightweight retrieval (~500 tokens), or ~20k for heavy users reviewing full day |
| **Async Watcher** | Background Haiku monitors your work, escalates to Opus only when needed. 95% cheaper than constant Opus monitoring |

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

Ever close a session and forget what you were working on? Use `/search` with natural language:

```
/search what was my last prompt?
/search what was I working on yesterday?
/search find prompts about git
/search when did I last check in?
```

Just type `/search` followed by your question in plain English. Pick up where you left off instantly.

**Token Usage:** ~500 tokens for quick lookups, scales with how much history you request.

### Session History (Dashboard)

Browse your Claude Code session history visually in the dashboard's **Sessions** tab:

- **Search** - Filter sessions by prompt text
- **Project Filter** - Focus on specific projects
- **Date Range** - Today, 7 days, 30 days, or all time
- **Expandable Cards** - Click to see full conversation with user/assistant messages
- **Tool Usage** - See what tools Claude used in each response

No tokens consumed - reads directly from `~/.claude/projects/` JSONL files.

### Async Watcher

A background Haiku agent monitors coordination state every 30 seconds. When it detects something that needs attention, it escalates to Opus automatically.

```
┌─────────────────┐     exit 1      ┌─────────────────┐
│  Haiku (Tier 1) │ ──────────────► │  Opus (Tier 2)  │
│  Fast checks    │   "need help"   │  Deep analysis  │
│  ~$0.001/check  │                 │  ~$0.10/call    │
└─────────────────┘                 └─────────────────┘
```

Runs automatically - no user interaction required. See [watcher/README.md](watcher/README.md) for configuration and details.

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
| `/search [question]` | Search session history with natural language |

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

## Troubleshooting

### Dashboard fails on Windows with Git Bash (Issue #11)

If you see `Cannot find module @rollup/rollup-win32-x64-msvc` when starting the dashboard:

**Cause:** Git Bash makes npm think it's running on Linux, so it installs Linux-specific binaries instead of Windows binaries.

**Fix Option 1:** Use PowerShell or CMD for npm install:
```powershell
cd ~/.claude/emergent-learning/dashboard-app/frontend
rm -rf node_modules package-lock.json
npm install
```

**Fix Option 2:** Use Bun (handles platform detection correctly):
```bash
bun install
```

The run-dashboard.sh script will now detect this issue and warn you before failing.

## Links

- [Claude Code Docs](https://docs.anthropic.com/en/docs/claude-code)
- [Hooks System](https://docs.anthropic.com/en/docs/claude-code/hooks)
- [Issues & Support](https://github.com/Spacehunterz/Emergent-Learning-Framework_ELF/issues)

## License

MIT License

<a href="https://www.buymeacoffee.com/Spacehunterz">
  <img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" alt="Buy Me A Coffee" width="150">
</a>

## Development Status

ELF is under heavy active development. Rapid commits reflect live experimentation, architectural refinement, and real-world usage. The main branch represents active research and may change frequently. Stable checkpoints will be published as versioned GitHub releases; users who prefer stability should rely on tagged releases rather than the latest commit.
