# Testing Guide

Comprehensive guide to testing in the Emergent Learning Framework (ELF).

**Last Updated:** 2026-01-05
**Status:** Production
**Audience:** Developers, Contributors, QA Engineers

---

## Table of Contents

- [Overview](#overview)
- [Test Organization](#test-organization)
- [Running Tests](#running-tests)
- [Writing New Tests](#writing-new-tests)
- [Fixture Patterns](#fixture-patterns)
- [Mocking Strategies](#mocking-strategies)
- [Coverage Requirements](#coverage-requirements)
- [CI/CD Integration](#ci-cd-integration)
- [Test Categories](#test-categories)
- [Advanced Patterns](#advanced-patterns)

---

## Overview

ELF uses a comprehensive testing strategy with multiple test categories:

- **Unit Tests**: Individual component testing
- **Integration Tests**: Multi-component interaction testing
- **Edge Case Tests**: Boundary conditions and error handling
- **Stress Tests**: Concurrency and performance testing
- **Destructive Tests**: Data corruption and recovery testing

### Testing Philosophy

1. **Test real behavior**: Mock only external dependencies
2. **Test edge cases**: Don't just test happy paths
3. **Test concurrency**: ELF is multi-threaded
4. **Test recovery**: Systems fail - test how we recover
5. **Keep tests fast**: Use temporary directories and cleanup

---

## Test Organization

### Directory Structure

```
emergent-learning/
├── tests/                          # Root test directory
│   ├── conftest.py                 # Pytest fixtures and configuration
│   ├── __init__.py                 # Test package marker
│   │
│   ├── test_blackboard_v2.py       # Dual-write system tests
│   ├── test_integration_multiagent.py # Multi-agent workflows
│   ├── test_claim_chains*.py       # Claim chain atomicity
│   ├── test_event_log*.py          # Event log consistency
│   │
│   ├── test_sqlite_edge_cases.py   # Database edge cases
│   ├── test_stress.py              # Concurrency stress tests
│   ├── test_destructive_edge_cases.py # Recovery tests
│   │
│   ├── test_fraud_*.py             # Fraud detection system
│   ├── test_lifecycle_*.py         # Lifecycle management
│   └── test_meta_observer.py       # Meta-learning observer
│
├── src/query/tests/                # Query system tests
│   ├── test_query.py
│   ├── test_improvements.py
│   └── test_regression.py
│
└── src/conductor/tests/            # Conductor tests
    ├── test_integration.py
    └── test_validation.py
```

### Naming Conventions

- **Test files**: `test_<feature>.py`
- **Test functions**: `test_<behavior>()`
- **Test classes**: `Test<Feature>` (optional)
- **Fixtures**: `<resource>` (e.g., `bb`, `runner`, `test_dir`)

---

## Running Tests

### Quick Start

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_blackboard_v2.py

# Run specific test function
pytest tests/test_stress.py::test_blackboard_concurrent_access

# Run tests matching pattern
pytest -k "claim_chain"

# Run with coverage report
pytest --cov=src --cov-report=html

# Run in parallel (requires pytest-xdist)
pytest -n auto
```

### Test Discovery

Pytest automatically discovers tests based on:

```python
# From pyproject.toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = "test_*.py"
python_classes = "Test*"
python_functions = "test_*"
addopts = "-v --tb=short"
```

### Environment Variables

```bash
# Set ELF base path for tests
export ELF_BASE_PATH=/path/to/test/installation

# Enable debug output
export ELF_DEBUG=1

# Set session ID for query logging tests
export CLAUDE_SESSION_ID=test-session-123
```

---

## Writing New Tests

### Basic Test Structure

```python
#!/usr/bin/env python3
"""
Test module description.

Tests cover:
1. Feature A
2. Feature B
3. Edge case C
"""

import pytest
from pathlib import Path


def test_basic_operation():
    """Test that basic operation works correctly."""
    # Arrange
    input_data = "test"

    # Act
    result = process(input_data)

    # Assert
    assert result == "expected"
```

### Using Fixtures

```python
def test_with_blackboard(bb):
    """Test using the blackboard fixture from conftest.py."""
    # Fixture provides a fresh Blackboard instance in temp directory
    bb.register_agent("test-agent", "Test task")

    agents = bb.get_active_agents()
    assert len(agents) == 1
    assert agents[0]["id"] == "test-agent"
```

### Parameterized Tests

```python
import pytest

@pytest.mark.parametrize("input,expected", [
    ("failure", True),
    ("success", True),
    ("invalid", False),
])
def test_learning_type_validation(input, expected):
    """Test learning type validation with multiple inputs."""
    result = is_valid_learning_type(input)
    assert result == expected
```

### Async Tests

```python
import pytest

@pytest.mark.asyncio
async def test_async_query():
    """Test async query system."""
    from query.core import QuerySystem

    qs = await QuerySystem.create()
    try:
        result = await qs.build_context("test")
        assert result is not None
    finally:
        await qs.cleanup()
```

### Testing Exceptions

```python
def test_invalid_domain_raises_error():
    """Test that invalid domain raises ValidationError."""
    from query.exceptions import ValidationError

    with pytest.raises(ValidationError, match="Domain name too long"):
        validate_domain("x" * 256)
```

---

## Fixture Patterns

Fixtures are defined in `tests/conftest.py` and provide reusable test resources.

### Available Fixtures

#### `results` - Test Result Tracker

Legacy test adapter for tests that use `results.pass_test()` pattern:

```python
def test_with_results_tracker(results):
    """Test using legacy results tracker."""
    try:
        # Do something
        result = perform_operation()
        assert result == expected
        results.record_pass("operation succeeds")
    except Exception as e:
        results.record_fail("operation succeeds", str(e))
```

#### `bb` - Blackboard Instance

Provides a fresh Blackboard instance in a temporary directory:

```python
def test_claim_chain(bb):
    """Test claim chain functionality."""
    chain = bb.claim_chain(
        agent_id="agent1",
        files=["file1.txt", "file2.txt"],
        reason="Testing"
    )
    assert chain is not None
    assert len(chain.files) == 2
```

#### `test_dir` - Temporary Test Directory

Provides a populated test directory for dependency graph tests:

```python
def test_dependency_graph(test_dir):
    """Test dependency graph construction."""
    from coordinator.dependency_graph import DependencyGraph

    graph = DependencyGraph(str(test_dir))
    graph.build_graph()

    # Test that files were discovered
    assert len(graph.files) > 0
```

#### `runner` - Test Runner (Stress Tests)

Provides a TestRunner instance for stress tests with automatic cleanup:

```python
def test_custom_stress_scenario(runner):
    """Test custom stress scenario."""
    project_root = runner.create_temp_project()

    # Run test operations
    # ...

    # Cleanup happens automatically
```

### Creating Custom Fixtures

Add to `tests/conftest.py`:

```python
import pytest
import tempfile
from pathlib import Path

@pytest.fixture
def temp_learning_db(tmp_path):
    """Provide a temporary learning database."""
    from query.models import initialize_database_sync

    db_path = tmp_path / "test.db"
    manager = initialize_database_sync(str(db_path))

    yield manager

    # Cleanup happens automatically with tmp_path
```

Usage:

```python
def test_with_custom_db(temp_learning_db):
    """Test using custom database fixture."""
    from query.models import Learning

    # Database is ready to use
    learning = Learning.create(
        type='test',
        filepath='test.md',
        title='Test'
    )
    assert learning.id is not None
```

---

## Mocking Strategies

### Mock External Dependencies Only

**DO:** Mock external systems (network, files outside test dir)

```python
from unittest.mock import Mock, patch

def test_with_mocked_api():
    """Test with mocked external API."""
    with patch('requests.get') as mock_get:
        mock_get.return_value.json.return_value = {'status': 'ok'}

        result = fetch_external_data()
        assert result['status'] == 'ok'
```

**DON'T:** Mock internal ELF components (test real behavior)

```python
# BAD - don't mock internal components
with patch('blackboard.Blackboard.register_agent'):
    # This doesn't test real behavior!
    pass

# GOOD - use real components with temp directories
def test_agent_registration(bb):
    bb.register_agent("test", "task")  # Real call
    assert len(bb.get_active_agents()) == 1
```

### Mocking SQLite for Edge Cases

When testing SQLite-specific edge cases, use real SQLite:

```python
def test_database_locking():
    """Test database locking behavior."""
    import sqlite3
    import tempfile

    with tempfile.NamedTemporaryFile(suffix='.db') as tmp:
        # Create real database
        conn1 = sqlite3.connect(tmp.name)
        conn2 = sqlite3.connect(tmp.name)

        # Test actual locking behavior
        cursor1 = conn1.cursor()
        cursor1.execute("BEGIN EXCLUSIVE TRANSACTION")

        # This should timeout or fail
        with pytest.raises(sqlite3.OperationalError):
            cursor2 = conn2.cursor()
            cursor2.execute("BEGIN EXCLUSIVE TRANSACTION")
```

### Mocking Time for Expiration Tests

```python
from unittest.mock import patch
from datetime import datetime, timedelta

def test_claim_expiration():
    """Test that claims expire after TTL."""
    with patch('blackboard.datetime') as mock_dt:
        # Set current time
        now = datetime(2026, 1, 1, 12, 0, 0)
        mock_dt.utcnow.return_value = now

        # Create claim with 5 minute TTL
        chain = bb.claim_chain("agent", ["file"], "test", ttl_minutes=5)

        # Advance time by 6 minutes
        mock_dt.utcnow.return_value = now + timedelta(minutes=6)

        # Claim should be expired
        assert bb.is_chain_expired(chain.chain_id)
```

---

## Coverage Requirements

### Coverage Targets

- **Overall**: 80% minimum
- **Core modules**: 90% minimum
  - `src/query/core.py`
  - `coordinator/blackboard.py`
  - `coordinator/blackboard_v2.py`
  - `coordinator/event_log.py`
- **Critical paths**: 100%
  - Data persistence
  - Concurrency control
  - Error handling

### Generating Coverage Reports

```bash
# Run tests with coverage
pytest --cov=src --cov=coordinator --cov-report=html --cov-report=term

# Open HTML report
open htmlcov/index.html

# Generate XML for CI
pytest --cov=src --cov-report=xml

# Check coverage percentage
pytest --cov=src --cov-report=term-missing --cov-fail-under=80
```

### Coverage Configuration

Add to `pyproject.toml`:

```toml
[tool.coverage.run]
source = ["src", "coordinator"]
omit = [
    "*/tests/*",
    "*/test_*.py",
    "*/__pycache__/*",
    "*/venv/*",
]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "raise AssertionError",
    "raise NotImplementedError",
    "if __name__ == .__main__.:",
    "if TYPE_CHECKING:",
]
```

### Identifying Untested Code

```bash
# Show lines not covered
pytest --cov=src --cov-report=term-missing

# Example output:
Name                    Stmts   Miss  Cover   Missing
-----------------------------------------------------
src/query/core.py         245     15    94%   89-92, 156-159
coordinator/blackboard.py 389     23    94%   445-448, 502-506
```

---

## CI/CD Integration

### GitHub Actions

Create `.github/workflows/test.yml`:

```yaml
name: Test Suite

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest

    strategy:
      matrix:
        python-version: [3.8, 3.9, "3.10", "3.11", "3.12"]

    steps:
    - uses: actions/checkout@v3

    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}

    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -e ".[dev]"

    - name: Run tests with coverage
      run: |
        pytest --cov=src --cov=coordinator \
               --cov-report=xml \
               --cov-report=term \
               --cov-fail-under=80

    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
        fail_ci_if_error: true
```

### Pre-commit Hooks

Create `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: local
    hooks:
      - id: pytest-check
        name: pytest
        entry: pytest
        language: system
        pass_filenames: false
        always_run: true
        stages: [commit]
```

### Running Tests Before Commit

```bash
# Run quick test suite
pytest -x --ff  # Stop on first failure, run failures first

# Run only fast tests
pytest -m "not slow"

# Skip integration tests
pytest -m "not integration"
```

---

## Test Categories

### Unit Tests

Test individual components in isolation:

```python
def test_heuristic_confidence_update():
    """Test that heuristic confidence updates correctly."""
    from query.models import Heuristic

    h = Heuristic.create(
        domain="testing",
        rule="Always test updates",
        confidence=0.5
    )

    # Validate increases confidence
    h.times_validated += 1
    new_confidence = calculate_confidence(h)
    assert new_confidence > 0.5
```

### Integration Tests

Test component interactions:

```python
def test_multiagent_coordination(tmp_path):
    """Test multiple agents coordinating through blackboard."""
    from blackboard_v2 import BlackboardV2

    bb = BlackboardV2(str(tmp_path))

    # Agent 1 registers and adds finding
    bb.register_agent("agent-1", "Task 1", interests=["auth"])
    bb.add_finding("agent-1", "fact", "Finding about auth")

    # Agent 2 queries findings by interest
    bb.register_agent("agent-2", "Task 2", interests=["auth"])
    findings = bb.get_findings(tags=["auth"])

    # Verify dual-write consistency
    result = bb.validate_state_consistency()
    assert result["consistent"]
```

### Edge Case Tests

Test boundary conditions and error handling:

```python
def test_null_handling_in_required_fields():
    """Test that NULL in required fields raises error."""
    import sqlite3

    conn = sqlite3.connect(":memory:")
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE test (
            id INTEGER PRIMARY KEY,
            required_field TEXT NOT NULL
        )
    """)

    # Should raise IntegrityError
    with pytest.raises(sqlite3.IntegrityError):
        cursor.execute(
            "INSERT INTO test (required_field) VALUES (NULL)"
        )
```

### Stress Tests

Test concurrency and performance:

```python
def test_concurrent_blackboard_access(runner):
    """Test 10 threads performing concurrent operations."""
    import threading

    project_root = runner.create_temp_project()
    bb = BlackboardV2(project_root)

    errors = []

    def worker(thread_id):
        try:
            bb.register_agent(f"agent-{thread_id}", "Task")
            bb.add_finding(f"agent-{thread_id}", "test", "Finding")
        except Exception as e:
            errors.append(str(e))

    # Start 10 threads
    threads = [threading.Thread(target=worker, args=(i,))
               for i in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # Verify no errors
    assert len(errors) == 0
```

---

## Advanced Patterns

### Testing Claim Chain Atomicity

```python
def test_atomic_claim_failure(bb):
    """Test that claim chain is all-or-nothing."""
    # Agent 1 claims file A
    bb.claim_chain("agent-1", ["fileA.txt"], "First claim")

    # Agent 2 tries to claim A and B (should fail atomically)
    from blackboard import BlockedError

    with pytest.raises(BlockedError) as exc_info:
        bb.claim_chain("agent-2", ["fileA.txt", "fileB.txt"], "Second claim")

    # Verify fileB was NOT claimed (atomic failure)
    claim = bb.get_claim_for_file("fileB.txt")
    assert claim is None

    # Verify error includes conflict info
    assert "fileA.txt" in str(exc_info.value.conflicting_files)
```

### Testing Event Log Consistency

```python
def test_event_log_sequence_monotonicity():
    """Test that event sequence numbers are strictly increasing."""
    from event_log import EventLog

    log = EventLog(tmp_path)

    sequences = []
    for i in range(100):
        seq = log.append_event("test.event", {"index": i})
        sequences.append(seq)

    # Verify monotonic increase
    assert sequences == sorted(sequences)
    assert len(sequences) == len(set(sequences))  # No duplicates
```

### Testing Recovery from Corruption

```python
def test_database_corruption_detection():
    """Test that corrupted database is detected."""
    import sqlite3

    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        # Create valid database
        conn = sqlite3.connect(tmp.name)
        conn.execute("CREATE TABLE test (id INTEGER)")
        conn.close()

        # Corrupt header
        with open(tmp.name, 'r+b') as f:
            f.seek(0)
            f.write(b'CORRUPTED_HEADER')

        # Should raise DatabaseError
        with pytest.raises(sqlite3.DatabaseError,
                          match="corrupt|malformed|not a database"):
            conn = sqlite3.connect(tmp.name)
            conn.execute("PRAGMA integrity_check")
```

### Testing Cleanup and Resource Management

```python
def test_resource_cleanup_on_failure():
    """Test that resources are cleaned up even on failure."""
    import weakref

    # Track object lifecycle
    bb = BlackboardV2(tmp_path)
    ref = weakref.ref(bb)

    try:
        # Simulate failure during operation
        raise RuntimeError("Simulated failure")
    except RuntimeError:
        pass
    finally:
        del bb

    # Force garbage collection
    import gc
    gc.collect()

    # Verify object was destroyed
    assert ref() is None
```

---

## Best Practices

### 1. Test Names Should Describe Behavior

```python
# GOOD
def test_claim_chain_releases_files_on_timeout():
    """Test that expired claims are automatically released."""
    pass

# BAD
def test_claim_chain():
    """Test claim chain."""
    pass
```

### 2. One Assertion Per Test (When Possible)

```python
# GOOD - focused tests
def test_agent_registration_creates_agent():
    bb.register_agent("agent-1", "task")
    assert len(bb.get_active_agents()) == 1

def test_agent_registration_sets_correct_id():
    bb.register_agent("agent-1", "task")
    assert bb.get_active_agents()[0]["id"] == "agent-1"

# ACCEPTABLE - related assertions
def test_agent_registration():
    bb.register_agent("agent-1", "task")
    agents = bb.get_active_agents()

    assert len(agents) == 1
    assert agents[0]["id"] == "agent-1"
    assert agents[0]["status"] == "active"
```

### 3. Use Descriptive Variable Names

```python
# GOOD
expected_agent_count = 1
actual_agent_count = len(bb.get_active_agents())
assert actual_agent_count == expected_agent_count

# BAD
x = 1
y = len(bb.get_active_agents())
assert y == x
```

### 4. Clean Up Resources

```python
def test_with_manual_cleanup():
    """Test that properly cleans up resources."""
    conn = sqlite3.connect(db_path)
    try:
        # Test operations
        pass
    finally:
        conn.close()  # Always clean up

# Better: use context managers
def test_with_context_manager():
    """Test using context manager for automatic cleanup."""
    with sqlite3.connect(db_path) as conn:
        # Test operations
        pass
    # Connection closed automatically
```

### 5. Test Error Messages

```python
def test_error_message_is_helpful():
    """Test that error messages guide users to fix issues."""
    with pytest.raises(ValidationError) as exc_info:
        validate_domain("x" * 256)

    # Verify error message is helpful
    error_msg = str(exc_info.value)
    assert "Domain name too long" in error_msg
    assert "max 255 characters" in error_msg
```

---

## Troubleshooting

### Tests Pass Locally But Fail in CI

**Common Causes:**

1. **Timing Issues**: CI may be slower
   ```python
   # Add timeouts
   import time
   time.sleep(0.1)  # Give async operations time to complete
   ```

2. **File Permissions**: CI environments have different permissions
   ```python
   # Ensure test files are created with correct permissions
   import os
   os.chmod(test_file, 0o644)
   ```

3. **Environment Variables**: CI may not have same env vars
   ```python
   # Set defaults in tests
   os.environ.setdefault("ELF_BASE_PATH", str(tmp_path))
   ```

### Database Locked Errors

**Solution**: Ensure connections are properly closed

```python
# Use context managers
with sqlite3.connect(db_path) as conn:
    # Operations
    pass  # Connection auto-closed

# Or explicit cleanup in fixtures
@pytest.fixture
def db_conn(tmp_path):
    conn = sqlite3.connect(tmp_path / "test.db")
    yield conn
    conn.close()
```

### Tests Are Too Slow

**Solutions:**

1. **Use pytest-xdist for parallel execution**
   ```bash
   pip install pytest-xdist
   pytest -n auto
   ```

2. **Mark slow tests**
   ```python
   import pytest

   @pytest.mark.slow
   def test_long_running_operation():
       pass
   ```

   ```bash
   # Skip slow tests
   pytest -m "not slow"
   ```

3. **Use smaller datasets in tests**
   ```python
   # Instead of 1000 iterations
   for i in range(10):  # Use 10 in tests
       pass
   ```

---

## Resources

- **Pytest Documentation**: https://docs.pytest.org/
- **Coverage.py**: https://coverage.readthedocs.io/
- **Testing Best Practices**: https://docs.python-guide.org/writing/tests/
- **ELF Test Examples**: `tests/` directory

---

**Next Steps:**

- Read [Performance Guide](performance.md) for optimization strategies
- Check [Architecture Documentation](../DOCUMENTATION_ARCHITECTURE_ANALYSIS.md) for system design
- Review existing tests in `tests/` for patterns and examples
