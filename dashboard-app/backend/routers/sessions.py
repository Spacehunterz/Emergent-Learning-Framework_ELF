"""
Sessions Router - Session history and projects.
"""

import logging
from dataclasses import asdict
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

router = APIRouter(prefix="/api", tags=["sessions"])
logger = logging.getLogger(__name__)

# SessionIndex will be injected from main.py
session_index = None


def set_session_index(idx):
    """Set the SessionIndex instance."""
    global session_index
    session_index = idx


@router.get("/sessions/stats")
async def get_session_stats():
    """
    Get session statistics.

    Returns:
        {
            "total_sessions": int,
            "agent_sessions": int,
            "user_sessions": int,
            "total_prompts": int,
            "last_scan": "timestamp",
            "projects_count": int
        }
    """
    try:
        if session_index is None:
            raise HTTPException(status_code=500, detail="Session index not initialized")
        stats = session_index.get_stats()
        return stats

    except Exception as e:
        logger.error(f"Error getting session stats: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get session stats")


@router.get("/sessions")
async def get_sessions(
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    days: Optional[int] = Query(None, ge=1),
    project: Optional[str] = None,
    search: Optional[str] = None,
    include_agent: bool = False
):
    """
    Get list of sessions with metadata.

    Query Parameters:
        offset: Number of sessions to skip (pagination)
        limit: Maximum sessions to return (default 50, max 200)
        days: Filter to sessions from last N days
        project: Filter by project name
        search: Search in first prompt preview
        include_agent: Include agent sessions (default: False)

    Returns:
        {
            "sessions": [...],
            "total": int,
            "offset": int,
            "limit": int
        }
    """
    try:
        if session_index is None:
            raise HTTPException(status_code=500, detail="Session index not initialized")

        sessions, total = session_index.list_sessions(
            offset=offset,
            limit=limit,
            days=days,
            project=project,
            search=search,
            include_agent=include_agent
        )

        return {
            "sessions": [asdict(s) for s in sessions],
            "total": total,
            "offset": offset,
            "limit": limit
        }

    except Exception as e:
        logger.error(f"Error listing sessions: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to list sessions")


@router.get("/sessions/{session_id}")
async def get_session(session_id: str):
    """
    Get full session content with all messages.

    Args:
        session_id: Session UUID

    Returns:
        {
            "session_id": "...",
            "project": "...",
            "project_path": "...",
            "first_timestamp": "...",
            "last_timestamp": "...",
            "prompt_count": int,
            "git_branch": "...",
            "is_agent": bool,
            "messages": [
                {
                    "uuid": "...",
                    "type": "user" | "assistant",
                    "timestamp": "...",
                    "content": "...",
                    "is_command": bool,
                    "tool_use": [...],
                    "thinking": "..."
                },
                ...
            ]
        }
    """
    try:
        if session_index is None:
            raise HTTPException(status_code=500, detail="Session index not initialized")

        session = session_index.load_full_session(session_id)

        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        return session

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error loading session {session_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to load session")


@router.get("/projects")
async def get_session_projects():
    """
    Get list of unique projects with session counts.

    Returns:
        [
            {
                "name": "project-name",
                "session_count": int,
                "last_activity": "timestamp"
            },
            ...
        ]
    """
    try:
        if session_index is None:
            raise HTTPException(status_code=500, detail="Session index not initialized")

        projects = session_index.get_projects()
        return projects

    except Exception as e:
        logger.error(f"Error getting projects: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get projects")
