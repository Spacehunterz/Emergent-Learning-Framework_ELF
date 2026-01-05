# Emergent Learning Dashboard - Backend Tests

Comprehensive test suite for the Emergent Learning Dashboard backend, covering:
- Security testing (authentication, authorization, attack prevention)
- Concurrency and race conditions
- Data integrity and transactions
- WebSocket communication

## Overview

This test suite includes:

### Security Tests (NEW)
- **Authentication & Authorization**: Session management, token validation
- **Attack Prevention**: SQL injection, XSS, CORS bypass, rate limiting
- **Cryptography**: Session encryption, secure token generation
- **Coverage**: 95%+ on security-critical code

See [SECURITY_TEST_STRATEGY.md](SECURITY_TEST_STRATEGY.md) for comprehensive security testing documentation.

### Concurrency Tests (Existing)
Verifies fixes for critical bugs identified in `CRITICAL_BUGS_QUICKREF.md`:

- **CRITICAL #1**: WebSocket reconnect race condition
- **CRITICAL #2**: Database corruption in auto-capture
- **CRITICAL #6**: Broadcast list modification race

## Test Files

### Security Tests

#### `unit/test_session_encryption.py`
Unit tests for session encryption and decryption.

**Test Classes:**
- `TestSessionEncryption`: Encryption/decryption, token generation
- `TestSessionStorage`: Redis vs in-memory storage
- `TestTokenGeneration`: Cryptographic randomness

**Key Tests:**
- Session data is actually encrypted (not plaintext)
- Tokens are unique and cryptographically secure
- Corrupted data handled gracefully
- Redis TTL set correctly (7 days)

#### `unit/test_token_validation.py`
Unit tests for token validation and authentication.

**Test Classes:**
- `TestTokenValidation`: require_auth, get_user_id
- `TestRateLimiting`: Rate limit configuration
- `TestSessionRetrieval`: User ID extraction

**Key Tests:**
- Valid sessions return user ID
- Invalid sessions raise 401
- Rate limiters configured correctly

#### `integration/test_auth_flow.py`
Integration tests for complete authentication flows.

**Test Classes:**
- `TestAuthenticationFlow`: End-to-end login/logout
- `TestSessionPersistence`: Session across requests
- `TestUserDataStorage`: Database user management
- `TestConcurrentSessions`: Multiple simultaneous sessions

**Key Tests:**
- Complete dev login flow works
- Logout invalidates session
- Session cookies have secure attributes
- User data persisted correctly

#### `security/test_sql_injection.py`
Security tests for SQL injection prevention.

**Test Classes:**
- `TestSQLInjectionPrevention`: Parameterized queries
- `TestBlindSQLInjection`: Time-based injection
- `TestUnionBasedInjection`: UNION attacks

**Key Tests:**
- SQL injection payloads safely handled
- Parameterized queries used (not string formatting)
- Special characters stored safely

#### `security/test_cors_attacks.py`
Security tests for CORS policy enforcement.

**Test Classes:**
- `TestCORSAttacks`: CORS violation prevention
- `TestOriginValidation`: Origin header validation
- `TestCORSBypass`: CORS bypass prevention

**Key Tests:**
- Allowed origins work (localhost:3001)
- Malicious origins blocked
- Wildcard not used with credentials
- Origin reflection attacks prevented

### Concurrency Tests

#### `test_websocket_stress.py`

Tests WebSocket connection handling under stress conditions.

**Test Classes:**
- `TestWebSocketConcurrentConnections`: Concurrent connection/disconnection safety
- `TestWebSocketReconnectionStress`: Reconnection logic and timeout handling
- `TestBroadcastRaceConditions`: Message ordering and race conditions
- `TestWebSocketStressIntegration`: Realistic load scenarios

**Key Tests:**
- `test_concurrent_connections_no_race`: 50 clients connecting concurrently
- `test_no_duplicate_reconnect_timeouts`: Verifies fix for CRITICAL #1
- `test_broadcast_during_concurrent_disconnect`: Tests broadcast safety
- `test_high_connection_churn`: 100 rapid connect/disconnect cycles

**Coverage:**
- Concurrent WebSocket connections
- Reconnection timeout management
- Message ordering under stress
- Connection list safety

### `test_auto_capture_rollback.py`

Tests database transaction safety in the auto-capture background job.

**Test Classes:**
- `TestAutoCaptureDatabaseRollback`: Transaction atomicity and rollback
- `TestAutoCaptureConcurrentUpdates`: Concurrent update safety
- `TestAutoCaptureLearningCapture`: Learning capture transaction safety

**Key Tests:**
- `test_partial_update_prevention_on_failure`: Verifies fix for CRITICAL #2
- `test_transaction_commit_on_success`: Validates successful transaction flow
- `test_concurrent_reanalysis_no_corruption`: Multiple concurrent updates
- `test_error_recovery_preserves_data_integrity`: Rollback preserves state

**Coverage:**
- Transaction rollback on failure
- Partial update prevention
- Error recovery mechanisms
- Database consistency

### `test_broadcast_race.py`

Tests broadcast operation thread safety and race condition handling.

**Test Classes:**
- `TestBroadcastListModification`: List modification safety
- `TestBroadcastAtomicity`: Broadcast operation atomicity
- `TestBroadcastErrorHandling`: Error handling in broadcasts
- `TestBroadcastPerformance`: Performance under load
- `TestBroadcastIntegration`: Realistic scenarios

**Key Tests:**
- `test_concurrent_disconnect_during_broadcast_no_error`: Verifies fix for CRITICAL #6
- `test_snapshot_prevents_iteration_modification`: Tests snapshot mechanism
- `test_lock_contention_handling`: Lock behavior under contention
- `test_large_connection_count`: 500 concurrent connections

**Coverage:**
- Concurrent disconnect during broadcast
- Connection list snapshot mechanism
- Lock contention handling
- Dead connection cleanup

## Setup

### Prerequisites

Install required dependencies:

```bash
cd apps/dashboard/backend
pip install -r requirements.txt
pip install pytest pytest-asyncio
```

### Running Tests

Run all tests:
```bash
pytest tests/ -v
```

Run security tests only:
```bash
# All security tests
pytest tests/unit/ tests/integration/ tests/security/ -v

# Just unit tests
pytest tests/unit/ -v

# Just integration tests
pytest tests/integration/ -v

# Just security attack tests
pytest tests/security/ -v
```

Run concurrency tests:
```bash
pytest tests/test_websocket_stress.py -v
pytest tests/test_auto_capture_rollback.py -v
pytest tests/test_broadcast_race.py -v
```

Run with coverage:
```bash
# Security module coverage
pytest tests/unit/ tests/integration/ tests/security/ --cov=routers.auth --cov-report=html

# Full backend coverage
pytest tests/ --cov=utils --cov=routers --cov-report=html
```

Run specific test class:
```bash
pytest tests/test_websocket_stress.py::TestWebSocketConcurrentConnections -v
```

Run specific test:
```bash
pytest tests/test_websocket_stress.py::TestWebSocketConcurrentConnections::test_concurrent_connections_no_race -v
```

Run with coverage:
```bash
pytest tests/ --cov=utils --cov-report=html
```

### Test Options

Run tests in parallel (faster):
```bash
pytest tests/ -n auto
```

Stop on first failure:
```bash
pytest tests/ -x
```

Show print statements:
```bash
pytest tests/ -s
```

Run only marked tests:
```bash
pytest tests/ -m asyncio
```

## Test Structure

### Fixtures (conftest.py)

**Database Fixtures:**
- `temp_db`: Temporary SQLite database for testing
- `db_connection`: Database connection with test schema
- `sample_workflow_run`: Sample completed workflow run
- `sample_failed_run`: Sample failed workflow run

**WebSocket Fixtures:**
- `mock_websocket`: Mock WebSocket connection
- `mock_websocket_broken`: Mock WebSocket that simulates failures

**Event Loop:**
- `event_loop`: Shared event loop for async tests

## Test Scenarios

### Concurrency Tests

**50+ Concurrent Connections**
- Simulates real-world load with many simultaneous clients
- Tests lock contention and connection tracking
- Validates no race conditions in connect/disconnect

**100 Rapid Reconnections**
- Tests reconnection timeout management
- Verifies no duplicate timeouts scheduled
- Validates exponential backoff logic

**500 Broadcast Recipients**
- Stress tests broadcast performance
- Tests snapshot mechanism under load
- Validates message delivery reliability

### Race Condition Tests

**Concurrent Disconnect During Broadcast**
- Tests the snapshot fix for list modification
- Simulates clients disconnecting mid-broadcast
- Validates no ValueError exceptions

**Mixed Connect/Disconnect Operations**
- Tests concurrent modifications to connection list
- Validates lock prevents corruption
- Tests dead connection cleanup

**Multiple Concurrent Broadcasts**
- Tests broadcast isolation
- Validates message ordering
- Tests snapshot consistency

### Database Integrity Tests

**Transaction Rollback on Failure**
- Simulates second UPDATE failing
- Validates first UPDATE is rolled back
- Tests atomic transaction behavior

**Concurrent Reanalysis**
- Multiple auto-capture instances running
- Tests database lock handling
- Validates no data corruption

**Error Recovery**
- Tests failed commit scenarios
- Validates data remains unchanged
- Tests rollback preserves state

## Expected Test Results

### Passing Criteria

All tests should pass with the fixes applied from `CRITICAL_BUGS_QUICKREF.md`.

**Expected Behavior:**
- No `ValueError: list.remove(x): x not in list` errors
- No partial database updates on transaction failure
- No duplicate reconnection timeouts
- All async operations complete without deadlock
- Database maintains consistency under concurrent load

### Common Issues

**If tests fail:**

1. **Import errors**: Ensure you're running from the correct directory
   ```bash
   cd apps/dashboard/backend
   PYTHONPATH=. pytest tests/
   ```

2. **Async warnings**: Install `pytest-asyncio`
   ```bash
   pip install pytest-asyncio
   ```

3. **Database locked**: Tests use isolated temp databases, but if issues occur:
   ```bash
   pytest tests/ --timeout=30
   ```

4. **Timing-sensitive failures**: Some race condition tests may occasionally fail on slow systems. Re-run to verify:
   ```bash
   pytest tests/ --count=3
   ```

## Performance Benchmarks

**Expected Test Duration:**
- `test_websocket_stress.py`: ~5-10 seconds
- `test_auto_capture_rollback.py`: ~3-5 seconds
- `test_broadcast_race.py`: ~8-12 seconds
- **Total**: ~15-30 seconds

**Load Test Metrics:**
- 500 concurrent connections: < 1 second
- 100 sequential broadcasts: < 0.5 seconds
- 100 concurrent updates: < 2 seconds

## Continuous Integration

### GitHub Actions

Add to `.github/workflows/test.yml`:

```yaml
name: Backend Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          cd apps/dashboard/backend
          pip install -r requirements.txt
          pip install pytest pytest-asyncio pytest-cov
      - name: Run tests
        run: |
          cd apps/dashboard/backend
          PYTHONPATH=. pytest tests/ -v --cov=utils --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v2
        with:
          file: ./apps/dashboard/backend/coverage.xml
```

## Test Coverage Goals

**Target Coverage:**
- `utils/broadcast.py`: 100% (critical path)
- `utils/auto_capture.py`: 95%+ (transaction paths)
- Overall backend utils: 85%+

**Coverage Reports:**
```bash
pytest tests/ --cov=utils --cov-report=html
open htmlcov/index.html
```

## Writing New Tests

### Test Naming Convention

```python
async def test_<what_is_being_tested>_<expected_outcome>():
    """
    Brief description of what this test validates.

    Include references to bug fixes or requirements if applicable.
    """
    # Arrange
    # Act
    # Assert
```

### Async Test Template

```python
import pytest

@pytest.mark.asyncio
async def test_new_feature():
    """Test description."""
    # Your test code
    assert expected == actual
```

### Using Fixtures

```python
async def test_with_database(db_connection, sample_workflow_run):
    """Test using database fixtures."""
    cursor = db_connection.cursor()
    cursor.execute("SELECT * FROM workflow_runs WHERE id = ?", (sample_workflow_run,))
    # Test logic
```

## Debugging Tests

### Verbose Output

```bash
pytest tests/test_websocket_stress.py -vv -s
```

### Debug Specific Test

```python
import pytest

@pytest.mark.asyncio
async def test_debug_example():
    # Add breakpoint
    import pdb; pdb.set_trace()
    # Test code
```

### Log Output

```bash
pytest tests/ -v --log-cli-level=DEBUG
```

## Contributing

When adding new tests:

1. **Follow naming conventions**: `test_<feature>_<scenario>.py`
2. **Add docstrings**: Explain what the test validates
3. **Use fixtures**: Leverage existing fixtures in `conftest.py`
4. **Test edge cases**: Include boundary conditions
5. **Document bug fixes**: Reference issue numbers or bug reports
6. **Run full suite**: Ensure new tests don't break existing ones

## References

- **Bug Reports**: `CRITICAL_BUGS_QUICKREF.md`
- **Implementation**:
  - `apps/dashboard/backend/utils/broadcast.py`
  - `apps/dashboard/backend/utils/auto_capture.py`
  - `apps/dashboard/frontend/src/hooks/useWebSocket.ts`

## License

Part of the Emergent Learning Framework (ELF) project.
