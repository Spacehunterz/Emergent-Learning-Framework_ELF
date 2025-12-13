"""
Workflows Router - Workflow management.
"""

import logging
import sys
from pathlib import Path

from fastapi import APIRouter

from models import WorkflowCreate, ActionResult
from utils import get_db, dict_from_row

router = APIRouter(prefix="/api", tags=["workflows"])
logger = logging.getLogger(__name__)

# Path will be set from main.py
EMERGENT_LEARNING_PATH = None


def set_paths(elf_path: Path):
    """Set the paths for workflow operations."""
    global EMERGENT_LEARNING_PATH
    EMERGENT_LEARNING_PATH = elf_path


@router.get("/workflows")
async def get_workflows():
    """Get all workflow definitions."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT w.*, COUNT(DISTINCT we.id) as edge_count
            FROM workflows w
            LEFT JOIN workflow_edges we ON w.id = we.workflow_id
            GROUP BY w.id
            ORDER BY w.created_at DESC
        """)
        return [dict_from_row(r) for r in cursor.fetchall()]


@router.post("/workflows")
async def create_workflow(workflow: WorkflowCreate) -> ActionResult:
    """Create a new workflow."""
    try:
        if EMERGENT_LEARNING_PATH is None:
            return ActionResult(success=False, message="Paths not configured")

        sys.path.insert(0, str(EMERGENT_LEARNING_PATH / "conductor"))
        from conductor import Conductor

        conductor = Conductor()
        workflow_id = conductor.create_workflow(
            name=workflow.name,
            description=workflow.description,
            nodes=workflow.nodes,
            edges=workflow.edges
        )

        return ActionResult(
            success=True,
            message=f"Created workflow '{workflow.name}'",
            data={"workflow_id": workflow_id}
        )
    except Exception as e:
        logger.error(f"Error creating workflow '{workflow.name}': {e}", exc_info=True)
        return ActionResult(success=False, message="Failed to create workflow. Please check workflow configuration.")
