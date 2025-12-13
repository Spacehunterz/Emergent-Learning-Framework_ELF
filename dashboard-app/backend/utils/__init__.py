"""
Utility modules for the Emergent Learning Dashboard backend.

Modules:
- database: Database connection and helper functions
- broadcast: WebSocket connection management
- repository: Base repository for generic CRUD operations
"""

from .database import get_db, dict_from_row, escape_like
from .broadcast import ConnectionManager
from .repository import BaseRepository

__all__ = [
    'get_db',
    'dict_from_row',
    'escape_like',
    'ConnectionManager',
    'BaseRepository',
]
