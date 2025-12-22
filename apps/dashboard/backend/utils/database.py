"""
Database utility functions for the Emergent Learning Dashboard.

Provides database connection management and helper functions for SQLite operations.
Supports both global and project-specific databases.
"""

import sqlite3
import os
from contextlib import contextmanager
from pathlib import Path
from typing import Optional
from dataclasses import dataclass


# Database paths
# Database paths
def get_base_path() -> Path:
    env_path = os.environ.get('ELF_BASE_PATH')
    if env_path: return Path(env_path)
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / '.coordination').exists() or (parent / '.git').exists():
            return parent
    return Path.home() / ".claude" / "emergent-learning"

EMERGENT_LEARNING_PATH = get_base_path()
GLOBAL_DB_PATH = EMERGENT_LEARNING_PATH / "memory" / "index.db"

# Legacy alias
DB_PATH = GLOBAL_DB_PATH


@dataclass
class ProjectContext:
    """Current project context for the dashboard."""
    has_project: bool = False
    project_name: Optional[str] = None
    project_root: Optional[Path] = None
    project_db_path: Optional[Path] = None


# Global project context (set at startup)
_current_project: Optional[ProjectContext] = None


def detect_project_context(start_path: Optional[Path] = None) -> ProjectContext:
    """
    Detect if we are in an ELF-initialized project.
    Walks up from start_path looking for .elf/ directory.
    """
    if start_path is None:
        start_path = Path.cwd()
    else:
        start_path = Path(start_path).resolve()

    current = start_path

    while True:
        elf_dir = current / '.elf'
        if elf_dir.exists() and elf_dir.is_dir():
            db_path = elf_dir / 'learnings.db'
            project_name = current.name
            config_path = elf_dir / 'config.yaml'
            if config_path.exists():
                try:
                    import yaml
                    with open(config_path, 'r', encoding='utf-8') as f:
                        config = yaml.safe_load(f) or {}
                    project_name = config.get('project', {}).get('name', current.name)
                except Exception:
                    pass

            return ProjectContext(
                has_project=True,
                project_name=project_name,
                project_root=current,
                project_db_path=db_path if db_path.exists() else None
            )

        parent = current.parent
        if parent == current:
            break
        current = parent

    return ProjectContext(has_project=False)


def init_project_context(start_path: Optional[Path] = None):
    """Initialize the global project context at startup."""
    global _current_project
    _current_project = detect_project_context(start_path)
    return _current_project


def get_project_context() -> ProjectContext:
    """Get the current project context."""
    global _current_project
    if _current_project is None:
        _current_project = detect_project_context()
    return _current_project


def escape_like(s: str) -> str:
    """Escape SQL LIKE wildcards to prevent wildcard injection."""
    return s.replace(chr(92), chr(92)+chr(92)).replace('%', chr(92)+'%').replace('_', chr(92)+'_')



def init_game_tables(conn):
    """Initialize game-related tables if they don't exist."""
    cursor = conn.cursor()
    
    # Users table for OAuth
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        github_id INTEGER UNIQUE,
        username TEXT NOT NULL,
        avatar_url TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # Game state table (Anti-Cheat: Server Authoritative)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS game_state (
        user_id INTEGER PRIMARY KEY,
        score INTEGER DEFAULT 0,
        unlocked_weapons TEXT DEFAULT '["pulse_laser"]', -- JSON list
        unlocked_cursors TEXT DEFAULT '["default"]', -- JSON list
        active_weapon TEXT DEFAULT 'pulse_laser',
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
    """)
    conn.commit()

@contextmanager
def get_db(scope: str = "global"):
    """Get database connection with row factory."""
    if scope == "project":
        ctx = get_project_context()
        if ctx.project_db_path and ctx.project_db_path.exists():
            db_path = ctx.project_db_path
        else:
            db_path = GLOBAL_DB_PATH
    else:
        db_path = GLOBAL_DB_PATH

    # Ensure directory exists
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(db_path), timeout=10.0)
    conn.row_factory = sqlite3.Row
    
    # Initialize game tables on connection (lightweight check)
    init_game_tables(conn)

    try:
        yield conn
    finally:
        conn.close()


@contextmanager
def get_global_db():
    """Get global database connection."""
    conn = sqlite3.connect(str(GLOBAL_DB_PATH), timeout=10.0)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


@contextmanager
def get_project_db():
    """Get project database connection (falls back to global if no project)."""
    ctx = get_project_context()
    if ctx.project_db_path and ctx.project_db_path.exists():
        db_path = ctx.project_db_path
    else:
        db_path = GLOBAL_DB_PATH

    conn = sqlite3.connect(str(db_path), timeout=10.0)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def dict_from_row(row) -> dict:
    """Convert sqlite3.Row to dict."""
    return dict(row) if row else None
