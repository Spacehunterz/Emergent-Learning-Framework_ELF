"""
Utility modules for the Emergent Learning Dashboard backend.

Modules:
- database: Database connection and helper functions
- broadcast: WebSocket connection management
- repository: Base repository for generic CRUD operations
- auto_capture: Background job for automatic failure capture
"""

from .database import (
    get_db, dict_from_row, escape_like,
    get_global_db, get_project_db,
    get_project_context, init_project_context,
    ProjectContext
)
from .broadcast import ConnectionManager
from .repository import BaseRepository
from .auto_capture import AutoCapture, auto_capture

__all__ = [
    'get_db',
    'dict_from_row',
    'escape_like',
    'get_global_db',
    'get_project_db',
    'get_project_context',
    'init_project_context',
    'ProjectContext',
    'ConnectionManager',
    'BaseRepository',
    'AutoCapture',
    'auto_capture',
]
