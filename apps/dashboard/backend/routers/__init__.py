"""
API Routers for the Emergent Learning Dashboard.

Each router handles a specific domain of the API:
- analytics: Stats, timeline, learning velocity, events, anomalies
- heuristics: Heuristics CRUD, graph, promote/demote
- runs: Workflow runs, hotspots, diffs
- knowledge: Decisions, assumptions, invariants, spike reports, learnings
- queries: Building queries, natural language interface
- sessions: Session history, projects
- admin: CEO inbox, domains, export, editor integration
- fraud: Fraud reports and review
- workflows: Workflow management
- context: Project context and scope information
"""

from .analytics import router as analytics_router
from .heuristics import router as heuristics_router
from .runs import router as runs_router
from .knowledge import router as knowledge_router
from .queries import router as queries_router
from .sessions import router as sessions_router
from .admin import router as admin_router
from .fraud import router as fraud_router
from .workflows import router as workflows_router
from .context import router as context_router
from .auth import router as auth_router
from .game import router as game_router
from .setup import router as setup_router

__all__ = [
    'analytics_router',
    'heuristics_router',
    'runs_router',
    'knowledge_router',
    'queries_router',
    'sessions_router',
    'admin_router',
    'fraud_router',
    'workflows_router',
    'context_router',
    'auth_router',
    'game_router',
    'setup_router',
]
