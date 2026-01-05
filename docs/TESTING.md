# Testing Guide

Complete guide to writing, running, and debugging tests in the Emergent Learning Framework.

## Quick Start

```bash
# Run all tests
make test

# Run with coverage report
make test-coverage

# Run fast tests only
make test-fast

# Watch mode (auto-re-run on changes)
make test-watch

# Run specific test file
pytest tests/test_example.py -v

# Run specific test function
pytest tests/test_example.py::TestClass::test_method -v
```

## Test Organization

Tests are organized by type and feature:

```
tests/
├── conftest.py                 # Shared fixtures
├── test_baseline_refresh.py    # Baseline system tests
├── test_conductors.py          # Conductor tests
├── test_learning_patterns.py   # Learning loop tests
├── unit/                       # Fast, isolated tests
│   ├── test_heuristic.py
│   └── test_validators.py
├── integration/                # Multi-component tests
│   ├── test_learning_flow.py
│   └── test_db_operations.py
└── dashboard/                  # Dashboard-specific tests
    ├── backend/
    └── frontend/
```

## Running Tests

### All tests
```bash
make test
```

Output:
```
================================ test session starts ================================
platform linux -- Python 3.11.0, pytest-9.0.1
collected 192 items

tests/test_baseline_refresh.py::test_database_schema PASSED [ 0%]
tests/test_baseline_refresh.py::test_refresh_schedule PASSED [ 1%]
...

================================ 192 passed in 12.34s ================================
```

### Fast tests (skip slow ones)
```bash
make test-fast
```

Skips tests marked with `@pytest.mark.slow`.

### Tests with coverage
```bash
make test-coverage
```

Generates:
- Terminal output with missing line counts
- HTML report at `htmlcov/index.html`

### Watch mode
```bash
make test-watch
```

Re-runs tests whenever you save a file. Press `q` to quit.

### Specific tests

Run one test file:
```bash
pytest tests/test_baseline_refresh.py -v
```

Run one test function:
```bash
pytest tests/test_baseline_refresh.py::test_database_schema -v
```

Run tests matching a pattern:
```bash
pytest tests/ -k "database" -v
```

Run only integration tests:
```bash
pytest tests/ -m integration -v
```

## Test Coverage

### View coverage report

```bash
# Generate coverage
make test-coverage

# Open HTML report
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
start htmlcov/index.html  # Windows
```

### Coverage targets

| Area | Target | Current |
|------|--------|---------|
| Overall | 80% | ~75% |
| Learning loop | 95% | ~90% |
| Invariants | 95% | ~88% |
| Golden rules | 85% | ~82% |

### Increase coverage

1. Find uncovered lines: `htmlcov/index.html` → click file
2. Write tests for those lines
3. Run `make test-coverage` to verify

Example of low-coverage function:
```python
# src/heuristics.py (uncovered lines shown in red)
def parse_heuristic(data: dict) -> Heuristic:
    """Parse heuristic from dict. Only 40% covered."""
    if not data.get('rule'):  # Not covered
        raise ValueError()

    # ... rest of function
```

Write test:
```python
# tests/test_heuristics.py
def test_parse_heuristic_missing_rule():
    """Test parsing heuristic without rule raises."""
    with pytest.raises(ValueError):
        parse_heuristic({})
```

## Writing Tests

### Basic test structure

```python
import pytest
from src.heuristics import Heuristic, validate_heuristic

class TestHeuristicValidation:
    """Tests for heuristic validation."""

    def test_valid_heuristic(self):
        """Test that valid heuristic passes validation."""
        heuristic = Heuristic(
            rule="Always use type hints",
            explanation="Makes code safer",
            domain="python",
            confidence=0.9
        )
        assert validate_heuristic(heuristic) is True

    def test_invalid_heuristic_missing_rule(self):
        """Test that heuristic without rule fails."""
        with pytest.raises(ValueError):
            Heuristic(rule="", explanation="x", domain="y")
```

### Fixtures (reusable test data)

```python
@pytest.fixture
def sample_heuristic():
    """Provide a heuristic for testing."""
    return Heuristic(
        rule="Test rule",
        explanation="Test explanation",
        domain="test",
        confidence=0.8
    )

def test_with_fixture(sample_heuristic):
    """Test using fixture."""
    assert sample_heuristic.rule == "Test rule"
```

### Mocking external dependencies

```python
from unittest.mock import patch

def test_with_mock():
    """Test with mocked dependency."""
    with patch('src.database.save') as mock_save:
        mock_save.return_value = True

        result = save_heuristic(...)

        assert result is True
        mock_save.assert_called_once()
```

### Parametrized tests (test multiple inputs)

```python
@pytest.mark.parametrize("domain,valid", [
    ("python", True),
    ("javascript", True),
    ("", False),
    ("invalid_lang", False),
])
def test_valid_domains(domain, valid):
    """Test validation for different domains."""
    assert is_valid_domain(domain) == valid
```

### Async tests

```python
@pytest.mark.asyncio
async def test_async_operation():
    """Test async function."""
    result = await async_fetch_heuristics()
    assert len(result) > 0
```

## Test Categories

### Unit tests (Fast, isolated)

Test individual functions/classes without dependencies:

```python
# tests/unit/test_heuristic.py

@pytest.mark.unit
def test_heuristic_score_calculation():
    """Test confidence score calculation."""
    h1 = Heuristic(..., confidence=0.9)
    h2 = Heuristic(..., confidence=0.5)

    assert h1.score > h2.score
```

Run only unit tests:
```bash
pytest tests/unit/ -v
```

### Integration tests (Slower, multi-component)

Test components working together:

```python
# tests/integration/test_learning_flow.py

@pytest.mark.integration
def test_complete_learning_cycle(db, conductor):
    """Test full: record → query → learn → apply."""
    # 1. Record a heuristic
    h = record_heuristic(...)

    # 2. Query conductor for it
    result = conductor.query(...)

    # 3. Verify it learned
    assert h.id in result.heuristics
```

Run only integration tests:
```bash
pytest tests/integration/ -v
```

### Slow tests (Mark for skipping)

```python
@pytest.mark.slow
def test_large_dataset_processing():
    """Test with 100k records - takes 30 seconds."""
    # ...
    assert result is not None
```

Skip in quick test runs:
```bash
make test-fast  # Skips @pytest.mark.slow
```

### Dashboard tests

#### Backend tests
```bash
make test-backend
```

#### Frontend tests
```bash
make test-frontend
```

## Debugging Tests

### Print output during test
```python
def test_with_debug():
    result = some_function()
    print(f"Result: {result}")  # Use print() or
    assert result is not None
```

Run with output visible:
```bash
pytest tests/test_example.py -v -s  # -s shows print output
```

### Drop into debugger
```python
def test_with_debugger():
    x = some_function()
    breakpoint()  # Python debugger stops here
    assert x is not None
```

Or use pdb:
```python
import pdb

def test_with_pdb():
    x = some_function()
    pdb.set_trace()  # Debugger stops here
    assert x is not None
```

Run test:
```bash
pytest tests/test_example.py -v -s
```

Debugger commands:
```
n         Next line
s         Step into function
c         Continue
l         List code
w         Show stack
h         Help
q         Quit
```

### Verbose output
```bash
pytest tests/ -vv          # Very verbose
pytest tests/ -vv -s       # Plus print statements
pytest tests/ -vv --tb=long  # Plus full tracebacks
```

### Timing info
```bash
pytest tests/ --durations=10  # Show 10 slowest tests
pytest tests/ --durations=0   # Show all test times
```

## Common Patterns

### Testing database operations

```python
@pytest.fixture
def db():
    """Provide clean database for test."""
    db = Database(":memory:")  # In-memory SQLite
    db.init_schema()
    yield db
    db.close()

def test_save_heuristic(db):
    h = Heuristic(...)
    db.save(h)

    retrieved = db.get(h.id)
    assert retrieved.rule == h.rule
```

### Testing with file I/O

```python
@pytest.fixture
def tmp_dir(tmp_path):
    """Provide temporary directory."""
    return tmp_path

def test_write_file(tmp_dir):
    filepath = tmp_dir / "test.txt"
    filepath.write_text("test content")

    assert filepath.read_text() == "test content"
```

### Testing error handling

```python
def test_error_handling():
    """Test that errors are handled gracefully."""
    with pytest.raises(ValueError) as exc_info:
        invalid_heuristic = Heuristic(rule="")

    assert "rule" in str(exc_info.value).lower()
```

### Testing state changes

```python
def test_state_change():
    """Test object state changes correctly."""
    obj = StatefulObject()
    assert obj.is_initialized is False

    obj.initialize()

    assert obj.is_initialized is True
```

## CI/CD Integration

Tests run automatically on:
- **Push to any branch**: GitHub Actions runs tests
- **Pull requests**: Must pass before merging
- **Scheduled nightly**: Full test suite runs

To verify locally before pushing:
```bash
make lint  # Check style
make test-coverage  # Run with coverage
```

## Best Practices

1. **Test behavior, not implementation**
   ```python
   # Good: Tests public behavior
   def test_save_saves_to_database():
       save(heuristic)
       assert get(heuristic.id) is not None

   # Bad: Tests internal details
   def test_save_calls_internal_method():
       with patch('...._internal_save'):
           save(...)
   ```

2. **Use descriptive names**
   ```python
   # Good
   def test_heuristic_with_empty_rule_raises_value_error()

   # Bad
   def test_heuristic()
   ```

3. **One assertion per test (or related assertions)**
   ```python
   # Good
   def test_save_and_retrieve():
       save(item)
       assert get(item.id) == item

   # Avoid multiple unrelated assertions
   ```

4. **Use fixtures for setup/teardown**
   ```python
   # Good: Clean, reusable
   @pytest.fixture
   def db():
       db = Database()
       yield db
       db.close()

   # Avoid: Setup in every test
   def test_something():
       db = Database()
       # test
       db.close()
   ```

5. **Test edge cases**
   ```python
   def test_empty_input():
   def test_none_value():
   def test_very_large_input():
   def test_special_characters():
   ```

## Getting Help

**Test failing but not sure why?**
```bash
# Run with maximum verbosity
pytest tests/test_example.py::test_function -vv -s --tb=long
```

**Need to debug test execution?**
```bash
# Use pdb debugger
pytest tests/test_example.py -vv -s --pdb
```

**Tests pass locally but fail in CI?**
- Check Python version: `python --version`
- Check dependencies: `pip list`
- Try on clean venv: `rm -rf .venv && make setup`

## Further Reading

- Pytest docs: https://docs.pytest.org/
- Python unittest: https://docs.python.org/3/library/unittest.html
- Testing best practices: https://testdriven.io/

---

## Quick Reference

```bash
# Most common commands
make test               # Run all tests
make test-coverage      # With coverage
make test-fast          # Skip slow
make test-watch         # Auto-re-run
pytest tests/test_X.py  # Single file
pytest tests/ -k "name" # By pattern
pytest --pdb            # Debug mode

# Troubleshooting
pytest -vv              # Verbose
pytest -s               # Show prints
pytest --tb=long        # Full traceback
pytest --durations=10   # Slowest tests
```
