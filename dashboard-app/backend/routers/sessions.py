"""
Sessions Router - Session history and projects.
"""

import logging
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, BackgroundTasks

router = APIRouter(prefix="/api", tags=["sessions"])
logger = logging.getLogger(__name__)

# Path to summarizer script
SUMMARIZER_SCRIPT = Path.home() / ".claude" / "emergent-learning" / "scripts" / "summarize-session.py"

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


@router.get("/sessions/{session_id}/summary")
async def get_session_summary(session_id: str):
    """
    Get summary for a session (if available).

    Returns:
        {
            "tool_summary": "...",
            "content_summary": "...",
            "conversation_summary": "...",
            "files_touched": [...],
            "tool_counts": {...},
            "summarized_at": "...",
            "has_summary": true/false
        }
    """
    try:
        if session_index is None:
            raise HTTPException(status_code=500, detail="Session index not initialized")

        summary = session_index.get_session_summary(session_id)

        if summary:
            return {"has_summary": True, **summary}
        else:
            return {"has_summary": False, "message": "Session not yet summarized"}

    except Exception as e:
        logger.error(f"Error getting session summary {session_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get session summary")


def _run_summarizer(session_id: str, use_llm: bool = True):
    """Background task to run the summarizer script."""
    try:
        cmd = [sys.executable, str(SUMMARIZER_SCRIPT), session_id]
        if not use_llm:
            cmd.append("--no-llm")

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if result.returncode != 0:
            logger.error(f"Summarizer failed for {session_id}: {result.stderr}")
        else:
            logger.info(f"Summarized session {session_id}")
    except Exception as e:
        logger.error(f"Error running summarizer for {session_id}: {e}")


@router.post("/sessions/{session_id}/summarize")
async def trigger_summarize(session_id: str, background_tasks: BackgroundTasks, use_llm: bool = True):
    """
    Trigger summarization of a session.

    Args:
        session_id: Session UUID
        use_llm: Whether to use haiku (True) or fallback (False)

    Returns:
        {"status": "queued", "session_id": "..."}
    """
    try:
        if session_index is None:
            raise HTTPException(status_code=500, detail="Session index not initialized")

        # Check if session exists
        metadata = session_index.get_session_metadata(session_id)
        if not metadata:
            raise HTTPException(status_code=404, detail="Session not found")

        # Queue summarization in background
        background_tasks.add_task(_run_summarizer, session_id, use_llm)

        return {"status": "queued", "session_id": session_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error triggering summarize for {session_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to trigger summarization")


@router.post("/sessions/summarize-batch")
async def trigger_batch_summarize(
    background_tasks: BackgroundTasks,
    older_than_hours: float = 1.0,
    limit: int = 10,
    use_llm: bool = True
):
    """
    Trigger batch summarization of old unsummarized sessions.

    Args:
        older_than_hours: Only sessions older than this
        limit: Max sessions to process
        use_llm: Whether to use haiku

    Returns:
        {"status": "queued", "count": N}
    """
    try:
        cmd = [
            sys.executable, str(SUMMARIZER_SCRIPT),
            "--batch",
            "--older-than", f"{older_than_hours}h",
            "--limit", str(limit)
        ]
        if not use_llm:
            cmd.append("--no-llm")

        # Run in background
        def run_batch():
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
                if result.returncode != 0:
                    logger.error(f"Batch summarizer failed: {result.stderr}")
                else:
                    logger.info(f"Batch summarization completed: {result.stdout}")
            except Exception as e:
                logger.error(f"Batch summarizer error: {e}")

        background_tasks.add_task(run_batch)

        return {"status": "queued", "limit": limit, "older_than_hours": older_than_hours}

    except Exception as e:
        logger.error(f"Error triggering batch summarize: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to trigger batch summarization")
