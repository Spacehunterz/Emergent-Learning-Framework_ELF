# Dashboard Guide

## Starting the Dashboard

**On Checkin:** Claude prompts "Start Dashboard? [Y/n]" at conversation start.

**Manual Start:**
```bash
cd ~/.claude/emergent-learning/dashboard-app
./run-dashboard.ps1  # Windows PowerShell
./run-dashboard.sh   # Mac/Linux/Git Bash
```

Open http://localhost:3001

## Dashboard Tabs

| Tab | What It Shows |
|-----|---------------|
| **Overview** | Hotspot treemap (D3.js), anomalies, golden rules |
| **Heuristics** | All patterns with confidence, promote/demote |
| **Runs** | Agent execution history, retry failed runs |
| **Timeline** | Event-by-event history with playback |
| **Sessions** | Browse Claude Code session history - search, filter, expand conversations |
| **Query** | Natural language search |

## Sessions Tab

The Sessions tab lets you browse your Claude Code session history without consuming tokens:

**Features:**
- **Search** - Filter sessions by prompt text
- **Project Filter** - Dropdown to focus on specific projects
- **Date Range** - Today, Last 7 days, Last 30 days, or All time
- **Expandable Cards** - Click any session to see the full conversation
- **User/Assistant Messages** - Clear visual distinction between prompts and responses
- **Tool Usage** - See what tools Claude used (Read, Edit, Bash, etc.)

**Data Source:** Reads from `~/.claude/projects/*/*.jsonl` files directly.

**API Endpoints:**
- `GET /api/sessions` - List sessions with pagination/filtering
- `GET /api/sessions/{id}` - Load full session content
- `GET /api/projects` - List projects with session counts
- `GET /api/sessions/stats` - Session statistics

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
