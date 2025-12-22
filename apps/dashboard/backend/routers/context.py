"""
Context router - provides project context information for the dashboard.

Endpoints:
- GET /api/context - Get current project context and scope info
"""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

from utils import get_project_context

router = APIRouter(prefix="/api/context", tags=["context"])


class ContextResponse(BaseModel):
    """Response model for context endpoint."""
    has_project: bool
    project_name: Optional[str] = None
    project_root: Optional[str] = None
    has_project_db: bool = False
    default_scope: str = "global"  # "global" or "project"


@router.get("", response_model=ContextResponse)
async def get_context():
    """
    Get current project context.
    
    Returns information about whether we're in a project context,
    and what the default scope should be for queries.
    """
    ctx = get_project_context()
    
    return ContextResponse(
        has_project=ctx.has_project,
        project_name=ctx.project_name,
        project_root=str(ctx.project_root) if ctx.project_root else None,
        has_project_db=ctx.project_db_path is not None and ctx.project_db_path.exists() if ctx.project_db_path else False,
        default_scope="project" if ctx.has_project else "global"
    )
