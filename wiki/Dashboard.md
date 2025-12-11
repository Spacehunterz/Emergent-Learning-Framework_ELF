# Dashboard Guide

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
