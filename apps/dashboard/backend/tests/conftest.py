"""
Pytest configuration and shared fixtures for the Emergent Learning Dashboard tests.

Provides common test fixtures for database connections, WebSocket mocking,
security testing utilities, and authentication helpers.
"""

import asyncio
import sqlite3
import sys
import tempfile
import os
import secrets
from pathlib import Path
from typing import Generator, AsyncGenerator
from unittest.mock import AsyncMock, MagicMock

import pytest

# Ensure backend path is in sys.path for all tests
BACKEND_ROOT = Path(__file__).parent.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

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


# ==============================================================================
# Security Testing Fixtures
# ==============================================================================

@pytest.fixture(scope="session")
def app():
    """Create FastAPI application for testing with security configuration."""
    # Set test environment variables ONLY if not already set (CI may set them)
    if not os.environ.get("SESSION_ENCRYPTION_KEY"):
        try:
            from cryptography.fernet import Fernet
            os.environ["SESSION_ENCRYPTION_KEY"] = Fernet.generate_key().decode()
        except ImportError:
            os.environ["SESSION_ENCRYPTION_KEY"] = "test_key_" + secrets.token_urlsafe(32)

    if not os.environ.get("DEV_ACCESS_TOKEN"):
        os.environ["DEV_ACCESS_TOKEN"] = secrets.token_hex(32)
    if not os.environ.get("GITHUB_CLIENT_ID"):
        os.environ["GITHUB_CLIENT_ID"] = "mock"
    # SESSION_DOMAIN must be empty for TestClient - domain=localhost doesn't match testclient's host
    os.environ["SESSION_DOMAIN"] = ""
    os.environ["ENVIRONMENT"] = "test"

    # Import after env vars are set
    import sys
    backend_path = Path(__file__).parent.parent
    if str(backend_path) not in sys.path:
        sys.path.insert(0, str(backend_path))

    try:
        from main import app as fastapi_app

        # Disable rate limiting for tests
        try:
            from routers.auth import limiter
            limiter.enabled = False
        except (ImportError, AttributeError):
            pass

        return fastapi_app
    except ImportError as e:
        pytest.skip(f"Could not import FastAPI app: {e}")


@pytest.fixture
def client(app):
    """Create test client for making HTTP requests."""
    try:
        from fastapi.testclient import TestClient
        return TestClient(app)
    except ImportError:
        pytest.skip("FastAPI TestClient not available")


@pytest.fixture
def dev_token():
    """Get DEV_ACCESS_TOKEN for testing authentication."""
    return os.environ.get("DEV_ACCESS_TOKEN")


@pytest.fixture
def authenticated_client(client, dev_token):
    """Create an authenticated test client with valid session."""
    # Perform login
    response = client.get(
        f"/api/auth/dev-callback?dev_token={dev_token}",
        follow_redirects=False
    )

    # Extract session token
    session_token = response.cookies.get("session_token")

    if session_token:
        # Set cookie on client
        client.cookies.set("session_token", session_token)

    return client


@pytest.fixture
def mock_request_with_session():
    """Create mock request with valid session token."""
    try:
        from routers.auth import create_session

        user_data = {"id": 1, "username": "test_user", "github_id": 12345}
        token = create_session(user_data)

        request = MagicMock()
        request.cookies = MagicMock()
        request.cookies.get = MagicMock(return_value=token)

        return request
    except ImportError:
        pytest.skip("Auth module not available")


@pytest.fixture
def mock_request_no_session():
    """Create mock request without session (unauthenticated)."""
    request = MagicMock()
    request.cookies = MagicMock()
    request.cookies.get = MagicMock(return_value=None)
    return request


@pytest.fixture
def mock_request_invalid_token():
    """Create mock request with invalid/malicious token."""
    request = MagicMock()
    request.cookies = MagicMock()
    request.cookies.get = MagicMock(return_value="invalid_token_12345")
    return request


# ==============================================================================
# Redis Testing Fixtures
# ==============================================================================

@pytest.fixture
def mock_redis():
    """Create mock Redis client for testing."""
    redis_mock = MagicMock()
    redis_mock.get = MagicMock(return_value=None)
    redis_mock.setex = MagicMock(return_value=True)
    redis_mock.delete = MagicMock(return_value=True)
    redis_mock.ping = MagicMock(return_value=True)
    redis_mock.ttl = MagicMock(return_value=3600)
    return redis_mock


@pytest.fixture
def mock_redis_failure():
    """Create mock Redis client that simulates connection failure."""
    redis_mock = MagicMock()
    redis_mock.get = MagicMock(side_effect=ConnectionError("Redis unavailable"))
    redis_mock.setex = MagicMock(side_effect=ConnectionError("Redis unavailable"))
    redis_mock.ping = MagicMock(side_effect=ConnectionError("Redis unavailable"))
    return redis_mock


# ==============================================================================
# Attack Payload Fixtures
# ==============================================================================

@pytest.fixture
def sql_injection_payloads():
    """Common SQL injection attack payloads."""
    return [
        "' OR '1'='1",
        "'; DROP TABLE users; --",
        "admin'--",
        "' OR 1=1--",
        "1' UNION SELECT NULL--",
        "admin'; EXEC sp_MSForEachTable 'DROP TABLE ?'; --",
        "' OR 'a'='a",
        "1' AND '1'='1",
    ]


@pytest.fixture
def xss_payloads():
    """Common XSS (Cross-Site Scripting) attack payloads."""
    return [
        "<script>alert('XSS')</script>",
        "<img src=x onerror=alert(1)>",
        "<svg/onload=alert(1)>",
        "javascript:alert(1)",
        "<iframe src='javascript:alert(1)'>",
        "<body onload=alert(1)>",
        "<input onfocus=alert(1) autofocus>",
    ]


@pytest.fixture
def path_traversal_payloads():
    """Common path traversal attack payloads."""
    return [
        "../../etc/passwd",
        "..\\..\\windows\\system32\\config\\sam",
        "....//....//etc/passwd",
        "..%2F..%2Fetc%2Fpasswd",
        "..%252F..%252Fetc%252Fpasswd",
    ]


@pytest.fixture
def malicious_origins():
    """Malicious CORS origins for testing."""
    return [
        "http://evil.com",
        "https://attacker.com",
        "http://localhost:9999",  # Different port
        "https://localhost:3001",  # Different protocol
        "null",
        "http://127.0.0.1:3001",  # Different host representation
    ]


@pytest.fixture
def oversized_payloads():
    """Payloads for testing request size limits."""
    return {
        "just_under_10mb": "x" * (10 * 1024 * 1024 - 1000),
        "exactly_10mb": "x" * (10 * 1024 * 1024),
        "over_10mb": "x" * (10 * 1024 * 1024 + 1),
        "way_over": "x" * (50 * 1024 * 1024),
    }


# ==============================================================================
# Security Test Helpers
# ==============================================================================

def assert_secure_cookie(set_cookie_header: str):
    """Assert that Set-Cookie header has secure attributes."""
    assert "HttpOnly" in set_cookie_header, "Cookie missing HttpOnly flag"
    assert "Secure" in set_cookie_header, "Cookie missing Secure flag"
    assert "SameSite" in set_cookie_header, "Cookie missing SameSite attribute"


def assert_security_headers(response):
    """Assert that response has required security headers."""
    headers = response.headers

    assert headers.get("X-Frame-Options") == "DENY", "Missing or incorrect X-Frame-Options"
    assert headers.get("X-Content-Type-Options") == "nosniff", "Missing X-Content-Type-Options"
    assert headers.get("X-XSS-Protection") == "1; mode=block", "Missing X-XSS-Protection"
    assert "Permissions-Policy" in headers, "Missing Permissions-Policy"
    assert headers.get("Referrer-Policy") == "strict-origin-when-cross-origin", "Missing Referrer-Policy"


# Make helper functions available to tests
pytest.assert_secure_cookie = assert_secure_cookie
pytest.assert_security_headers = assert_security_headers


# ==============================================================================
# Session Cleanup
# ==============================================================================

@pytest.fixture(autouse=True)
def cleanup_test_sessions():
    """Automatically clean up test sessions and reset rate limiter after each test."""
    # Reset rate limiter BEFORE test runs
    try:
        from routers.auth import limiter
        # Clear the rate limiter storage
        if hasattr(limiter, '_storage'):
            limiter._storage.reset()
        elif hasattr(limiter, 'storage'):
            limiter.storage.reset()
        # For in-memory storage, clear the internal dict
        if hasattr(limiter, '_limiter') and hasattr(limiter._limiter, '_storage'):
            storage = limiter._limiter._storage
            if hasattr(storage, 'storage'):
                storage.storage.clear()
            elif hasattr(storage, '_storage'):
                storage._storage.clear()
    except (ImportError, AttributeError):
        pass  # Rate limiter not available or different version

    yield

    try:
        from routers.auth import IN_MEMORY_SESSIONS
        IN_MEMORY_SESSIONS.clear()
    except ImportError:
        pass  # Auth module not loaded


# ==============================================================================
# Database Setup for Security Tests
# ==============================================================================

@pytest.fixture
def security_db(temp_db: Path) -> Generator[sqlite3.Connection, None, None]:
    """Create database with users table for security testing."""
    conn = sqlite3.connect(str(temp_db))
    conn.row_factory = sqlite3.Row

    # Create users table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            github_id INTEGER UNIQUE NOT NULL,
            username TEXT NOT NULL,
            avatar_url TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Create game_state table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS game_state (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE NOT NULL,
            score INTEGER DEFAULT 0,
            level INTEGER DEFAULT 1,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    conn.commit()
    yield conn
    conn.close()
