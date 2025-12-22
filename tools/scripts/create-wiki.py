#!/usr/bin/env python3
"""Create wiki pages from old README content."""

from pathlib import Path

wiki_dir = Path.home() / ".claude" / "emergent-learning" / "wiki"
wiki_dir.mkdir(exist_ok=True)

# Home.md - Wiki landing page
home = """# Emergent Learning Framework Wiki

Welcome to the ELF documentation. This wiki contains detailed guides for all features.

## Quick Links

| Page | Description |
|------|-------------|
| [Installation](Installation) | Prerequisites, install options, troubleshooting |
| [Configuration](Configuration) | CLAUDE.md, settings.json, hooks setup |
| [Dashboard](Dashboard) | Visual monitoring, tabs, themes |
| [Swarm](Swarm) | Multi-agent coordination, personas |
| [CLI Reference](CLI-Reference) | All query commands |
| [Golden Rules](Golden-Rules) | Customizing constitutional principles |
| [Migration](Migration) | Upgrading, team setup, rollback |
| [Architecture](Architecture) | Database schema, hooks system |
| [Token Costs](Token-Costs) | Usage breakdown, optimization tips |

## The Core Concept

Claude Code is stateless - every session starts from zero. This framework bridges that gap by giving Claude access to your project's history:

- **Before each task:** Query the building for relevant knowledge
- **After each task:** Record outcomes automatically
- **Over time:** Patterns strengthen, mistakes don't repeat

## The Learning Loop

```
QUERY   ->  Check building for knowledge
APPLY   ->  Use heuristics during task
RECORD  ->  Capture outcome (success/failure)
PERSIST ->  Update confidence scores
            |
         (cycle repeats)
```

## What It's NOT

- **Not AI training** - Claude's model doesn't change. This is structured context injection.
- **Not magic** - It's systematic note-taking with automatic retrieval.
- **Not instant value** - It compounds over time. Day one won't feel different.
"""

# Installation.md
installation = """# Installation Guide

## Prerequisites

- Python 3.8+
- Node.js 18+ or Bun (recommended)
- Claude Code CLI installed

**Verify prerequisites:**

```bash
python --version      # Expected: 3.8.0+
node --version        # Expected: v18.0.0+
bun --version         # Alternative to Node
claude --version      # Should show version
```

## Install Options

The installer has three components:

| Component | What it does |
|-----------|-------------|
| **Core** | Query system, hooks, golden rules, CLAUDE.md |
| **Dashboard** | React UI for monitoring (localhost:3001) |
| **Swarm** | Multi-agent conductor, agent personas |

**Install everything (default):**
```bash
./install.sh              # Mac/Linux
./install.ps1             # Windows
```

**Install options:**
```bash
./install.sh --core-only      # Just core, no dashboard or swarm
./install.sh --no-dashboard   # Core + swarm, skip dashboard
./install.sh --no-swarm       # Core + dashboard, skip swarm
./install.sh --help           # Show all options
```

## What Gets Installed

```
~/.claude/
├── CLAUDE.md                    # Agent instructions
├── settings.json                # Hook configurations
├── emergent-learning/
│   ├── query/query.py          # Query system
│   ├── memory/
│   │   ├── index.db            # SQLite database
│   │   ├── golden-rules.md     # Constitutional principles
│   │   ├── failures/           # Failure logs
│   │   └── successes/          # Success logs
│   ├── scripts/                # Utility scripts
│   ├── dashboard-app/          # React UI
│   ├── conductor/              # Workflow orchestration
│   ├── agents/                 # Agent personas
│   └── ceo-inbox/              # Escalated decisions
└── hooks/
    └── learning-loop/          # Pre/post hooks
```

## Auto-Install Hooks

Hooks are automatically installed on first use. When you run `query.py --context` for the first time (or say "check in"), it copies hook files to `~/.claude/hooks/learning-loop/`.

Existing hook files are never overwritten - your customizations are safe.

## Troubleshooting

**Hooks not working:**
```bash
# Check hooks exist
ls ~/.claude/hooks/learning-loop/

# Check settings.json has hook config
cat ~/.claude/settings.json | grep learning-loop
```

**Database errors:**
```bash
# Validate database
python ~/.claude/emergent-learning/query/query.py --validate
```

**Dashboard won't start:**
```bash
# Check ports
lsof -i :8888  # Backend
lsof -i :3001  # Frontend

# Manual start
cd ~/.claude/emergent-learning/dashboard-app
./run-dashboard.sh
```
"""

# Configuration.md
configuration = """# Configuration

## CLAUDE.md

The `~/.claude/CLAUDE.md` file contains instructions Claude follows. The framework installs a template that:

- Requires querying the building before tasks
- Lists the golden rules
- Explains how to record learnings

You can add your own instructions below the ELF section.

## settings.json

Hook configuration in `~/.claude/settings.json`:

```json
{
  "hooks": {
    "PreToolUse": [{
      "matcher": "Task",
      "hooks": [{
        "type": "command",
        "command": "python ~/.claude/hooks/learning-loop/pre_tool_learning.py"
      }]
    }],
    "PostToolUse": [{
      "matcher": "Task",
      "hooks": [{
        "type": "command",
        "command": "python ~/.claude/hooks/learning-loop/post_tool_learning.py"
      }]
    }]
  }
}
```

## Key Phrases

The CLAUDE.md template teaches Claude to respond to:

| Phrase | What It Does |
|--------|--------------|
| `check in` | Queries building, reports context |
| `query the building` | Same as check in |
| `what does the building know about X` | Searches for topic X |
| `record this failure: [lesson]` | Creates failure log |
| `record this success: [pattern]` | Documents success |
| `start experiment: [hypothesis]` | Tracks hypothesis |

## Automatic vs Manual Learning

**Automatic (via hooks):**
- Pre-task query injects relevant heuristics
- Post-task recording logs outcomes
- Confidence updates based on success/failure
- Trail laying tracks files touched

**Manual (via key phrases):**
- Major failures worth documenting
- Project-specific patterns
- Experiments you want to track
"""

# Dashboard.md
dashboard = """# Dashboard Guide

## Starting the Dashboard

**Auto-Start:** Dashboard starts automatically via startup hook.

**Manual Start:**
```bash
cd ~/.claude/emergent-learning/dashboard-app
./run-dashboard.ps1  # Windows
./run-dashboard.sh   # Mac/Linux
```

Open http://localhost:3001

## Dashboard Tabs

| Tab | What It Shows |
|-----|---------------|
| **Overview** | Hotspot treemap (D3.js), anomalies, golden rules |
| **Heuristics** | All patterns with confidence, promote/demote |
| **Runs** | Agent execution history, retry failed runs |
| **Timeline** | Event-by-event history with playback |
| **Query** | Natural language search |

## Stats Bar

The top bar shows real-time metrics:

- **Total Runs** - Click to see history
- **Success Rate** - Percentage of successful runs
- **Heuristics** - Total patterns learned
- **Golden Rules** - Constitutional principles
- **Hotspots** - High-activity code locations
- **Queries** - Building queries made

## Tech Stack

- **Frontend:** React 18 + TypeScript + Vite + Tailwind CSS
- **Backend:** FastAPI (Python) with WebSocket updates
- **Visualization:** D3.js for treemaps
- **Database:** Reads from `~/.claude/emergent-learning/memory/index.db`
- **Themes:** 10 cosmic themes (black-hole, nebula, aurora, etc.)

The dashboard operates **without consuming API tokens** - it reads directly from your local SQLite database.
"""

# Swarm.md
swarm = """# Swarm: Multi-Agent Coordination

**Requires Pro or Max plan** - Free plan can't use Task tool for subagents.

## What It Does

The conductor coordinates multiple Claude Code subagents with distinct personas:

| Agent | Role | When to Use |
|-------|------|-------------|
| **Researcher** | Deep investigation | "We need to understand X" |
| **Architect** | System design | "How should we structure X?" |
| **Skeptic** | Breaking things | "Is this robust?" |
| **Creative** | Novel solutions | "We're stuck on X" |

## Using Swarm

```bash
/swarm investigate the authentication system    # Start task
/swarm show                                     # View state
/swarm reset                                    # Clear and restart
/swarm stop                                     # Stop all agents
/swarm                                          # Continue pending
```

**Example:**
```
You: /swarm investigate why the API is slow

Claude: ## Swarm Plan
        **Task:** Investigate API performance
        **Agents:** 3

        | # | Subtask | Scope |
        |---|---------|-------|
        | 1 | Profile endpoints | src/api/ |
        | 2 | Check database queries | src/db/ |
        | 3 | Review caching | src/cache/ |

        Proceed? [Y/n]
```

## The Blackboard Pattern

Agents coordinate through shared SQLite database:

**Pheromone Trails:**
- `discovery` - "Found something interesting"
- `warning` - "Be careful here"
- `blocker` - "This is broken"
- `hot` - "High activity area"
- `cold` - "Already explored"

**Flow:**
1. Researcher explores, leaves `discovery` trails
2. Architect sees trails, focuses design
3. Skeptic leaves `warning` on risky parts
4. Findings recorded for future sessions

## Agent Personalities

Defined in `~/.claude/emergent-learning/agents/`:

**Researcher:** Thorough, methodical, breadth-first
**Architect:** Top-down, structural, considers extensions
**Skeptic:** Adversarial, tests edge cases
**Creative:** Lateral thinking, challenges assumptions

## Query Conductor

```bash
python ~/.claude/emergent-learning/conductor/query_conductor.py --workflows
python ~/.claude/emergent-learning/conductor/query_conductor.py --failures
python ~/.claude/emergent-learning/conductor/query_conductor.py --hotspots
python ~/.claude/emergent-learning/conductor/query_conductor.py --trails --scent blocker
```

## When to Use Swarm

**Single agent:** Simple tasks, quick fixes, direct questions

**Swarm:** Complex investigations, architecture decisions, debugging from multiple angles
"""

# CLI-Reference.md
cli_ref = """# CLI Reference

## Query Commands

```bash
# Build full context (what agents see)
python ~/.claude/emergent-learning/query/query.py --context

# Query by domain
python ~/.claude/emergent-learning/query/query.py --domain testing

# Query by tags
python ~/.claude/emergent-learning/query/query.py --tags api,error

# Get recent learnings
python ~/.claude/emergent-learning/query/query.py --recent 10

# View statistics
python ~/.claude/emergent-learning/query/query.py --stats

# Validate database
python ~/.claude/emergent-learning/query/query.py --validate

# Export learnings
python ~/.claude/emergent-learning/query/query.py --export > backup.json
```

## Recording Scripts

```bash
# Record a failure
~/.claude/emergent-learning/scripts/record-failure.sh

# Record a heuristic
~/.claude/emergent-learning/scripts/record-heuristic.sh

# Start an experiment
~/.claude/emergent-learning/scripts/start-experiment.sh
```

## Conductor Commands

```bash
# List workflow runs
python ~/.claude/emergent-learning/conductor/query_conductor.py --workflows

# Show specific run
python ~/.claude/emergent-learning/conductor/query_conductor.py --workflow 123

# Show failures
python ~/.claude/emergent-learning/conductor/query_conductor.py --failures

# Show hotspots
python ~/.claude/emergent-learning/conductor/query_conductor.py --hotspots

# Show trails by scent
python ~/.claude/emergent-learning/conductor/query_conductor.py --trails --scent blocker

# Statistics
python ~/.claude/emergent-learning/conductor/query_conductor.py --stats
```
"""

# Golden-Rules.md
golden_rules = """# Golden Rules

Golden Rules are constitutional principles all agents follow.

## Built-in Rules

1. **Query Before Acting** - Always check the building first
2. **Document Failures Immediately** - Record while context is fresh
3. **Extract Heuristics** - Document the WHY, not just outcomes
4. **Break It Before Shipping** - Test destructively before release
5. **Escalate Uncertainty** - Ask when unsure about big decisions

## Adding Project-Specific Rules

**Step 1:** Identify the pattern
- Validated 10+ times
- Applies broadly to your project
- Saves significant time when followed

**Step 2:** Add to CLAUDE.md
```markdown
## 6. Always Use Retry Logic for External APIs
> Any call to external services must include exponential backoff

**Why:** Third-party APIs are unreliable. Silent failures caused 3 incidents.
**Promoted:** 2025-12-01
**Validations:** 15
```

## Promoting Heuristics

When a heuristic has proven itself (confidence > 0.9, validations > 10):

1. Check confidence: `python query.py --context | grep "pattern"`
2. Edit `~/.claude/emergent-learning/memory/golden-rules.md`
3. Update CLAUDE.md to reference it

## Best Practices

**Good rules:**
- "Validate user input before processing"
- "Check file existence before reading"

**Bad rules:**
- "Use Joi schema with these exact fields" (too specific)
- "Be careful with files" (not actionable)

**Include the Why:**
- Good: "Hash passwords (Why: plaintext caused breach)"
- Bad: "Hash passwords"
"""

# Token-Costs.md
token_costs = """# Token Costs

This adds tokens to usage. Here's the breakdown:

## Per-Session Costs

- **CLAUDE.md load:** ~1,500 tokens (once per session)
- **Golden rules injection:** ~500 tokens (every session)

## Per-Task Costs

- **Pre-hook query:** 200-500 tokens
- **Heuristic injection:** 50-200 tokens per heuristic
- **Post-hook recording:** Minimal (writes to DB, no API)

## Typical Usage

| Scenario | Token Overhead |
|----------|----------------|
| Simple task, no heuristics | ~1,700 tokens |
| Task with 3 heuristics | ~2,000 tokens |
| Complex task, 10+ heuristics | ~2,500 tokens |
| Swarm multi-agent | 2,500 x N agents |

## Cost-Benefit

**The tradeoff:** Higher tokens per task, but fewer wasted attempts.

**Example:**
- Without ELF: Repeat bug 5 times = 50 wasted messages
- With ELF: 500 extra tokens, avoid those 50 messages
- Break-even: Avoid 1-2 repeated bugs

## Reducing Costs

1. **Prune low-value heuristics** - Archive confidence < 0.3
2. **Use domain queries** - `--domain testing` instead of `--context`
3. **Disable for trivial tasks** - Settings profile without hooks
4. **Periodic cleanup** - Review heuristics monthly
"""

# Migration.md
migration = """# Migration Guide

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
"""

# Architecture.md
architecture = """# Architecture

## System Diagram

```
+---------------------------------------------------------------+
|                      Claude Code Session                      |
+---------------------------------------------------------------+
|                                                               |
|   +--------------+    +--------------+    +--------------+    |
|   |   Pre-Hook   |--->|  Task Tool   |--->|  Post-Hook   |    |
|   |   (inject)   |    |  (execute)   |    |   (record)   |    |
|   +------+-------+    +--------------+    +-------+------+    |
|          |                                        |           |
|          v                                        v           |
|   +-------------------------------------------------------+   |
|   |                    SQLite Database                    |   |
|   |  +----------+ +----------+ +---------+ +----------+   |   |
|   |  |Heuristics| |Learnings | | Metrics | |  Trails  |   |   |
|   |  +----------+ +----------+ +---------+ +----------+   |   |
|   +-------------------------------------------------------+   |
|          ^                                        ^           |
|          |                                        |           |
|   +------+-------+                        +-------+------+    |
|   | Query System |                        |  Dashboard   |    |
|   |  (query.py)  |                        | (React+API)  |    |
|   +--------------+                        +--------------+    |
+---------------------------------------------------------------+
```

## Database Tables

| Table | Purpose |
|-------|---------|
| `heuristics` | Learned patterns with confidence |
| `learnings` | Failures and successes |
| `metrics` | Usage statistics |
| `trails` | Pheromone signals for swarm |
| `workflow_runs` | Swarm execution instances |
| `node_executions` | Individual agent work |

## File Locations

| Path | Purpose |
|------|---------|
| `~/.claude/CLAUDE.md` | Agent instructions |
| `~/.claude/settings.json` | Hook configurations |
| `~/.claude/emergent-learning/memory/index.db` | SQLite database |
| `~/.claude/emergent-learning/query/query.py` | Query system |
| `~/.claude/hooks/learning-loop/` | Hook scripts |
| `~/.claude/emergent-learning/dashboard-app/` | React dashboard |
| `~/.claude/emergent-learning/conductor/` | Swarm orchestration |
| `~/.claude/emergent-learning/agents/` | Agent personalities |

## Hooks System

**PreToolUse (Task):**
1. Hook triggered before Task tool executes
2. Queries database for relevant heuristics
3. Injects heuristics into agent context

**PostToolUse (Task):**
1. Hook triggered after Task completes
2. Analyzes output for success/failure
3. Updates heuristic confidence
4. Lays trails for files touched
5. Auto-records failures
"""

# Write all files
files = {
    'Home.md': home,
    'Installation.md': installation,
    'Configuration.md': configuration,
    'Dashboard.md': dashboard,
    'Swarm.md': swarm,
    'CLI-Reference.md': cli_ref,
    'Golden-Rules.md': golden_rules,
    'Token-Costs.md': token_costs,
    'Migration.md': migration,
    'Architecture.md': architecture,
}

for filename, content in files.items():
    (wiki_dir / filename).write_text(content, encoding='utf-8')
    print(f"Created {filename}")

print(f"\nCreated {len(files)} wiki pages in {wiki_dir}")
