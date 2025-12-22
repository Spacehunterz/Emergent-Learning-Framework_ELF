# Installation Guide

## Prerequisites

- Python 3.8+
- Peewee ORM (installed automatically)
- Node.js 18+ or Bun (recommended for dashboard)
- Claude Code CLI installed

**Verify prerequisites:**

```bash
python --version      # Expected: 3.8.0+
node --version        # Expected: v18.0.0+
bun --version         # Alternative to Node
claude --version      # Should show version
```

**Python dependencies (installed automatically by installer):**
- `peewee` - SQLite ORM for database operations

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
