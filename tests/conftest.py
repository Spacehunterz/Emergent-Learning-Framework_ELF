"""
Pytest configuration for ELF test suite.

Fixtures and configuration for testing the Emergent Learning Framework.
"""
from pathlib import Path
import sys
import tempfile
import shutil

import pytest

# Add src directory to path for imports
src_path = Path(__file__).parent.parent / "src" / "emergent-learning"
sys.path.insert(0, str(src_path))

# Add coordinator directory to path for imports
coordinator_path = Path(__file__).parent.parent / "coordinator"
sys.path.insert(0, str(coordinator_path))


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
