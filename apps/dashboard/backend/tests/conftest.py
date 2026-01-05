"""
Pytest configuration and shared fixtures for the Emergent Learning Dashboard tests.

Provides common test fixtures for database connections, WebSocket mocking,
and other test utilities.
"""

import asyncio
import sqlite3
import tempfile
from pathlib import Path
from typing import Generator, AsyncGenerator
from unittest.mock import AsyncMock, MagicMock

import pytest

try:
    import pytest_asyncio
    HAS_PYTEST_ASYNCIO = True
except ImportError:
    HAS_PYTEST_ASYNCIO = False
    # Define pytest_asyncio.fixture as an alias for pytest.fixture if not available
    class _PytestAsyncio:
        fixture = pytest.fixture
    pytest_asyncio = _PytestAsyncio()

try:
    from fastapi import WebSocket
except ImportError:
    # Mock WebSocket if FastAPI not available
    WebSocket = type('WebSocket', (), {})


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def temp_db() -> Generator[Path, None, None]:
    """Create a temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = Path(f.name)

    # Initialize the database with required tables
    conn = sqlite3.connect(str(db_path))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS workflow_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            workflow_name TEXT NOT NULL,
            status TEXT NOT NULL,
            output_json TEXT,
            error_message TEXT,
            started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP,
            completed_nodes INTEGER DEFAULT 0,
            total_nodes INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS node_executions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id INTEGER NOT NULL,
            node_name TEXT NOT NULL,
            result_text TEXT,
            result_json TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (run_id) REFERENCES workflow_runs(id)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS learnings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT NOT NULL,
            filepath TEXT NOT NULL,
            title TEXT NOT NULL,
            summary TEXT,
            domain TEXT,
            severity INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            metric_type TEXT NOT NULL,
            metric_name TEXT NOT NULL,
            metric_value REAL,
            context TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS trails (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id INTEGER,
            trail_data TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (run_id) REFERENCES workflow_runs(id)
        )
    """)
    conn.commit()
    conn.close()

    yield db_path

    import gc
    import time
    gc.collect()
    for _ in range(3):
        try:
            db_path.unlink(missing_ok=True)
            break
        except PermissionError:
            time.sleep(0.1)
            gc.collect()


@pytest.fixture
def db_connection(temp_db: Path) -> Generator[sqlite3.Connection, None, None]:
    """Provide a database connection for testing."""
    conn = sqlite3.connect(str(temp_db))
    conn.row_factory = sqlite3.Row
    yield conn
    conn.close()


@pytest.fixture
async def mock_websocket() -> AsyncMock:
    """Create a mock WebSocket for testing."""
    ws = AsyncMock(spec=WebSocket)
    ws.accept = AsyncMock()
    ws.send_json = AsyncMock()
    ws.send_text = AsyncMock()
    ws.close = AsyncMock()
    ws.receive_json = AsyncMock()
    ws.receive_text = AsyncMock()
    return ws


@pytest.fixture
async def mock_websocket_broken() -> AsyncMock:
    """Create a mock WebSocket that simulates connection failures."""
    ws = AsyncMock(spec=WebSocket)
    ws.accept = AsyncMock()
    ws.send_json = AsyncMock(side_effect=RuntimeError("Connection closed"))
    ws.send_text = AsyncMock(side_effect=RuntimeError("Connection closed"))
    ws.close = AsyncMock()
    return ws


@pytest.fixture
def sample_workflow_run(db_connection: sqlite3.Connection) -> int:
    """Create a sample workflow run for testing."""
    cursor = db_connection.cursor()
    cursor.execute("""
        INSERT INTO workflow_runs
        (workflow_name, status, output_json, completed_nodes, total_nodes)
        VALUES (?, ?, ?, ?, ?)
    """, ("test_workflow", "completed", '{"outcome": "unknown", "reason": "No content"}', 3, 3))
    db_connection.commit()
    return cursor.lastrowid


@pytest.fixture
def sample_failed_run(db_connection: sqlite3.Connection) -> int:
    """Create a sample failed workflow run for testing."""
    cursor = db_connection.cursor()
    cursor.execute("""
        INSERT INTO workflow_runs
        (workflow_name, status, error_message, output_json, completed_nodes, total_nodes)
        VALUES (?, ?, ?, ?, ?, ?)
    """, ("test_workflow", "failed", "Test error", '{"outcome": "failure", "reason": "Test error"}', 1, 3))
    db_connection.commit()
    return cursor.lastrowid
