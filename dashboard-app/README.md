# Emergent Learning Dashboard

An interactive real-time dashboard for monitoring and managing your Claude Code learning system.

## Features

- **Real-time Updates** - WebSocket-powered live data streaming
- **Interactive Treemap** - D3.js visualization of code hotspots
- **Heuristic Lifecycle** - Track rules from learning to golden status
- **Timeline Replay** - Step through agent activity history
- **One-Click Actions** - Promote, retry, and open in editor
- **Natural Language Query** - Ask questions about your data
- **Visual Workflow Builder** - Create automation rules
- **Anomaly Detection** - Get alerts for unusual patterns

## Quick Start

```powershell
# Run from the dashboard-app directory
./start.ps1
```

Or manually:

```powershell
# Terminal 1 - Backend
cd backend
pip install -r requirements.txt
python -m uvicorn main:app --reload --port 8888

# Terminal 2 - Frontend
cd frontend
bun install
bun run dev
```

## URLs

- **Dashboard**: http://localhost:3001
- **API**: http://localhost:8888
- **API Docs**: http://localhost:8888/docs

## Architecture

```
dashboard-app/
├── backend/              # FastAPI server
│   ├── main.py          # API endpoints + WebSocket
│   └── requirements.txt
├── frontend/            # React + Vite app
│   ├── src/
│   │   ├── components/  # UI components
│   │   ├── hooks/       # React hooks
│   │   └── types.ts     # TypeScript types
│   └── package.json
├── start.ps1           # Startup script
└── README.md
```

## API Endpoints

### Stats & Data
- `GET /api/stats` - System statistics
- `GET /api/heuristics` - All heuristics
- `GET /api/hotspots` - Code hotspots
- `GET /api/runs` - Agent runs
- `GET /api/timeline` - Event timeline
- `GET /api/anomalies` - Detected anomalies

### Actions
- `POST /api/actions/heuristic/{id}/promote` - Promote to golden
- `POST /api/actions/heuristic/{id}/demote` - Demote from golden
- `POST /api/actions/run/{id}/retry` - Retry failed run
- `POST /api/actions/open-editor` - Open file in VS Code

### Query
- `POST /api/query` - Natural language query

### WebSocket
- `WS /ws` - Real-time updates

## Components

### Overview Tab
- Stats bar with key metrics
- Interactive hotspot treemap
- Anomaly alerts
- Golden rules summary

### Heuristics Tab
- Searchable/filterable list
- Lifecycle visualization
- One-click promote/demote
- Confidence tracking

### Runs Tab
- Agent execution history
- Status filtering
- File touchpoints
- Retry failed runs

### Timeline Tab
- Event-by-event history
- Playback controls
- Event type filtering
- Related context

### Query Tab
- Natural language interface
- Smart result rendering
- Query suggestions
- Search history

## License

MIT
