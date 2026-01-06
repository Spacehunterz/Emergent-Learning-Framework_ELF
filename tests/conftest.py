"""
Pytest configuration for ELF test suite.

Fixtures and configuration for testing the Emergent Learning Framework.

All path manipulations are centralized here - individual test files should NOT
modify sys.path. Import from this conftest.py instead.
"""
from pathlib import Path
import os
import sys
import tempfile
import shutil
import sqlite3
from contextlib import contextmanager
from typing import Generator, Any

import pytest

# =============================================================================
# PATH CONFIGURATION (Centralized - DO NOT duplicate in test files)
# =============================================================================
REPO_ROOT = Path(__file__).parent.parent
SRC_PATH = REPO_ROOT / "src"
COORDINATOR_PATH = REPO_ROOT / "coordinator"
TESTS_PATH = Path(__file__).parent

# Add paths once at import time
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))
if str(COORDINATOR_PATH) not in sys.path:
    sys.path.insert(0, str(COORDINATOR_PATH))
if str(TESTS_PATH) not in sys.path:
    sys.path.insert(0, str(TESTS_PATH))

# Set default environment
os.environ.setdefault("ELF_BASE_PATH", str(REPO_ROOT))

# =============================================================================
# TEST MARKERS
# =============================================================================
def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line("markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')")
    config.addinivalue_line("markers", "concurrent: marks tests with threading/async")
    config.addinivalue_line("markers", "database: marks tests requiring database")
    config.addinivalue_line("markers", "integration: marks integration tests")
    config.addinivalue_line("markers", "stress: marks stress/load tests")

# =============================================================================
# DATABASE SCHEMA (Shared across all database fixtures)
# =============================================================================
HEURISTICS_SCHEMA = """
CREATE TABLE IF NOT EXISTS heuristics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    domain TEXT NOT NULL,
    rule TEXT NOT NULL,
    explanation TEXT,
    source_type TEXT,
    source_id INTEGER,
    confidence REAL DEFAULT 0.5,
    times_validated INTEGER DEFAULT 0,
    times_violated INTEGER DEFAULT 0,
    times_contradicted INTEGER DEFAULT 0,
    is_golden INTEGER DEFAULT 0,
    status TEXT DEFAULT 'active',
    dormant_since DATETIME,
    last_used_at DATETIME,
    revival_conditions TEXT,
    times_revived INTEGER DEFAULT 0,
    min_applications INTEGER DEFAULT 10,
    last_confidence_update DATETIME,
    update_count_today INTEGER DEFAULT 0,
    update_count_reset_date DATE,
    confidence_ema REAL,
    ema_alpha REAL,
    ema_warmup_remaining INTEGER DEFAULT 0,
    last_ema_update DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS confidence_updates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    heuristic_id INTEGER NOT NULL,
    old_confidence REAL NOT NULL,
    new_confidence REAL NOT NULL,
    delta REAL NOT NULL,
    update_type TEXT NOT NULL,
    reason TEXT,
    session_id TEXT,
    agent_id TEXT,
    rate_limited INTEGER DEFAULT 0,
    raw_target_confidence REAL,
    smoothed_delta REAL,
    alpha_used REAL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS revival_triggers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    heuristic_id INTEGER NOT NULL,
    trigger_type TEXT NOT NULL,
    trigger_value TEXT NOT NULL,
    priority INTEGER DEFAULT 100,
    is_active INTEGER DEFAULT 1,
    last_checked DATETIME,
    times_triggered INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    applied_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    description TEXT
);
"""

VIEWS_SCHEMA = """
CREATE VIEW IF NOT EXISTS eviction_candidates AS
SELECT
    h.id,
    h.domain,
    h.rule,
    h.status,
    h.confidence,
    h.times_validated,
    h.times_violated,
    h.times_contradicted,
    h.last_used_at,
    h.created_at,
    h.confidence *
    (CASE
        WHEN h.last_used_at IS NULL THEN 0.25
        WHEN julianday('now') - julianday(h.last_used_at) > 90 THEN 0.1
        WHEN julianday('now') - julianday(h.last_used_at) > 60 THEN 0.3
        WHEN julianday('now') - julianday(h.last_used_at) > 30 THEN 0.5
        WHEN julianday('now') - julianday(h.last_used_at) > 14 THEN 0.7
        WHEN julianday('now') - julianday(h.last_used_at) > 7 THEN 0.85
        ELSE 1.0
    END) *
    (CASE
        WHEN h.times_validated = 0 THEN 0.5
        WHEN h.times_validated < 3 THEN 0.7
        WHEN h.times_validated < 10 THEN 0.85
        ELSE 1.0
    END) AS eviction_score,
    (h.times_validated + h.times_violated + h.times_contradicted) AS total_applications
FROM heuristics h
WHERE h.status = 'active' OR h.status = 'dormant'
ORDER BY eviction_score ASC;

CREATE VIEW IF NOT EXISTS domain_health AS
SELECT
    domain,
    COUNT(*) AS total_heuristics,
    SUM(CASE WHEN status = 'active' THEN 1 ELSE 0 END) AS active_count,
    SUM(CASE WHEN status = 'dormant' THEN 1 ELSE 0 END) AS dormant_count,
    AVG(confidence) AS avg_confidence
FROM heuristics
GROUP BY domain;
"""

# =============================================================================
# ENVIRONMENT CLEANUP FIXTURES
# =============================================================================
@pytest.fixture
def clean_env():
    """
    Fixture that saves and restores environment variables.

    Use this when tests modify os.environ to prevent pollution.
    """
    original_env = os.environ.copy()
    yield os.environ
    os.environ.clear()
    os.environ.update(original_env)

@pytest.fixture
def isolated_elf_env(tmp_path, clean_env):
    """
    Provide an isolated ELF environment with its own base path.

    Creates a temporary ELF directory structure and sets ELF_BASE_PATH.
    Automatically cleans up after the test.
    """
    elf_base = tmp_path / "elf"
    elf_base.mkdir()
    (elf_base / "memory").mkdir()

    clean_env["ELF_BASE_PATH"] = str(elf_base)
    yield elf_base

# =============================================================================
# DATABASE FIXTURES
# =============================================================================
@pytest.fixture
def in_memory_db():
    """
    Fast in-memory SQLite database for unit tests.

    No I/O overhead - use for tests that don't need persistence.
    """
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(HEURISTICS_SCHEMA)
    yield conn
    conn.close()

@pytest.fixture
def in_memory_db_with_views():
    """
    In-memory database with views for lifecycle/eviction tests.
    """
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(HEURISTICS_SCHEMA)
    conn.executescript(VIEWS_SCHEMA)
    conn.execute("INSERT INTO schema_version (version, description) VALUES (2, 'Test schema')")
    conn.commit()
    yield conn
    conn.close()

@pytest.fixture
def file_db(tmp_path):
    """
    File-based SQLite database for tests requiring persistence.

    Use for: crash recovery, file locking, WAL mode tests.
    """
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.executescript(HEURISTICS_SCHEMA)
    conn.executescript(VIEWS_SCHEMA)
    conn.execute("INSERT INTO schema_version (version, description) VALUES (2, 'Test schema')")
    conn.commit()
    yield db_path, conn
    conn.close()

@pytest.fixture
def transactional_db(in_memory_db):
    """
    Database with automatic rollback after each test.

    Faster than recreating - use for tests that modify data.
    """
    in_memory_db.execute("BEGIN")
    yield in_memory_db
    in_memory_db.rollback()

# =============================================================================
# MOCK DATABASE CLASS (Shared across tests)
# =============================================================================
class MockDatabase:
    """
    Test database manager with isolation.

    Use this instead of creating your own MockDatabase in test files.
    Provides consistent schema and cleanup.
    """
    __test__ = False  # Prevent pytest collection

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._setup()

    def _setup(self):
        """Create test database with schema."""
        if self.db_path.exists():
            self.db_path.unlink()

        conn = sqlite3.connect(self.db_path)
        conn.executescript(HEURISTICS_SCHEMA)
        conn.executescript(VIEWS_SCHEMA)
        conn.execute("INSERT INTO schema_version (version, description) VALUES (2, 'Test schema')")
        conn.commit()
        conn.close()

    def teardown(self):
        """Remove test database."""
        if self.db_path.exists():
            try:
                self.db_path.unlink()
            except PermissionError:
                pass  # Windows file locking

    def insert_heuristic(self, domain: str, rule: str, confidence: float = 0.5,
                        times_validated: int = 0, times_violated: int = 0,
                        times_contradicted: int = 0, status: str = "active") -> int:
        """Insert a test heuristic and return its ID."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO heuristics (domain, rule, confidence, times_validated,
                                   times_violated, times_contradicted, status, last_used_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))
        """, (domain, rule, confidence, times_validated, times_violated, times_contradicted, status))
        conn.commit()
        heuristic_id = cursor.lastrowid
        conn.close()
        return heuristic_id

    def get_connection(self) -> sqlite3.Connection:
        """Get a connection to the test database."""
        return sqlite3.connect(self.db_path)

@pytest.fixture
def mock_db(tmp_path):
    """
    Provide a MockDatabase instance with automatic cleanup.

    Use this instead of creating MockDatabase manually in tests.
    """
    db_path = tmp_path / "test_lifecycle.db"
    db = MockDatabase(db_path)
    yield db
    db.teardown()


class TestResults:
    """
    Test result tracker for legacy test functions.

    This is a pytest-compatible adapter for tests that were designed
    to run manually with a TestResults tracker. Supports both naming
    conventions:
    - pass_test/fail_test (used by test_dependency_graph.py)
    - record_pass/record_fail (used by test_claim_chains_comprehensive.py)

    When run under pytest, pass methods do nothing (pytest tracks success)
    and fail methods raise AssertionError to let pytest handle the failure.
    """
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []

    # Methods used by test_dependency_graph.py
    def pass_test(self, name: str):
        """Record a passing test."""
        self.passed += 1

    def fail_test(self, name: str, reason: str):
        """Record a failing test - raises AssertionError for pytest."""
        self.failed += 1
        self.errors.append(f"{name}: {reason}")
        raise AssertionError(f"{name}: {reason}")

    # Methods used by test_claim_chains_comprehensive.py
    def record_pass(self, test_name: str):
        """Record a passing test (alias for pass_test)."""
        self.passed += 1

    def record_fail(self, test_name: str, reason: str):
        """Record a failing test - raises AssertionError for pytest."""
        self.failed += 1
        error_msg = f"{test_name}: {reason}"
        self.errors.append(error_msg)
        raise AssertionError(error_msg)

    def summary(self):
        """Print summary - not needed under pytest."""
        return self.failed == 0


@pytest.fixture
def results():
    """
    Provide a TestResults instance for legacy tests.

    Tests that were designed to run manually with results.pass_test()
    and results.fail_test() or results.record_pass() and
    results.record_fail() can use this fixture.
    """
    return TestResults()


@pytest.fixture
def bb(tmp_path):
    """
    Fixture providing a Blackboard instance for claim chain tests.

    Creates a fresh Blackboard in a temporary directory and cleans up after.
    Used by: tests/test_claim_chains_comprehensive.py
    """
    try:
        from blackboard import Blackboard
    except ImportError:
        pytest.skip("blackboard module not available")
        return

    blackboard = Blackboard(project_root=str(tmp_path))
    blackboard.reset()

    yield blackboard

    # Cleanup
    blackboard.reset()


@pytest.fixture
def test_dir(tmp_path):
    """
    Provide a temporary directory with a test project for dependency graph tests.

    Creates a test project structure with various import patterns:
    - Simple imports (stdlib only)
    - Complex imports (local modules)
    - Nested modules (utils/*)
    - No imports
    - Circular imports
    - Relative imports
    - Syntax error files (for error handling)

    Uses pytest's tmp_path fixture internally for automatic cleanup.
    Returns a Path object pointing to the temporary directory.
    """
    temp_dir = tmp_path

    # Test file 1: Simple imports
    (temp_dir / "simple.py").write_text("""
import os
import sys
from pathlib import Path
""")

    # Test file 2: Complex imports
    (temp_dir / "complex.py").write_text("""
import simple
from utils import helper
from utils.advanced import AdvancedHelper
import complex_lib as cl
from typing import Dict, List
""")

    # Test file 3: Utils module (to be imported)
    utils_dir = temp_dir / "utils"
    utils_dir.mkdir()
    (utils_dir / "__init__.py").write_text("")
    (utils_dir / "helper.py").write_text("""
import os
from pathlib import Path
""")
    (utils_dir / "advanced.py").write_text("""
from utils.helper import helper_func
import simple
""")

    # Test file 4: No imports
    (temp_dir / "no_imports.py").write_text("""
def standalone_function():
    return 42
""")

    # Test file 5: Circular imports (A imports B, B imports A)
    (temp_dir / "circular_a.py").write_text("""
import circular_b
def func_a():
    pass
""")
    (temp_dir / "circular_b.py").write_text("""
import circular_a
def func_b():
    pass
""")

    # Test file 6: Relative imports
    pkg_dir = temp_dir / "package"
    pkg_dir.mkdir()
    (pkg_dir / "__init__.py").write_text("")
    (pkg_dir / "module1.py").write_text("""
from . import module2
from ..simple import something
""")
    (pkg_dir / "module2.py").write_text("""
from . import module1
""")

    # Non-Python file (should be ignored)
    (temp_dir / "README.md").write_text("# Test Project")

    # File with syntax error (should be handled gracefully)
    (temp_dir / "syntax_error.py").write_text("""
def broken(
    missing closing paren
""")

    return temp_dir


@pytest.fixture
def runner():
    """
    Fixture providing a TestRunner instance for stress tests.

    This fixture creates a TestRunner from test_stress.py that manages
    temporary directories and test result collection. Cleanup happens
    automatically after the test completes.

    Used by: tests/test_stress.py
    """
    # Add tests directory to path so we can import test_stress
    tests_dir = Path(__file__).parent
    if str(tests_dir) not in sys.path:
        sys.path.insert(0, str(tests_dir))

    # Import TestRunner from test_stress module
    from test_stress import TestRunner

    test_runner = TestRunner()
    yield test_runner

    # Cleanup temporary directories
    test_runner.cleanup()
