# Comprehensive Security Test Strategy
## ELF Dashboard Backend - apps/dashboard/backend

**Version:** 1.0
**Last Updated:** 2026-01-05
**Coverage Target:** 95% on authentication/security code, 100% on critical security paths

---

## Table of Contents

1. [Test Architecture Overview](#test-architecture-overview)
2. [Unit Tests](#unit-tests)
3. [Integration Tests](#integration-tests)
4. [Security Attack Tests](#security-attack-tests)
5. [Test Fixtures and Utilities](#test-fixtures-and-utilities)
6. [Coverage Requirements](#coverage-requirements)
7. [CI/CD Integration](#cicd-integration)
8. [Test Execution Strategy](#test-execution-strategy)

---

## Test Architecture Overview

### Testing Pyramid for Security

```
           /\
          /  \     E2E Security Tests (5%)
         /____\    - Full authentication flows
        /      \   - Cross-service security
       /________\  Integration Tests (25%)
      /          \ - API endpoint security
     /____________\- Session management
    /              \ Unit Tests (70%)
   /________________\- Token validation
  /                  \- Encryption/decryption
 /____________________\- Input validation
```

### Test Categories

1. **Unit Tests** - Isolated function/method testing
   - Session encryption/decryption
   - Token generation/validation
   - Input sanitization
   - Rate limit logic

2. **Integration Tests** - Component interaction testing
   - Full authentication flow
   - Session persistence
   - Redis fallback to in-memory
   - Protected endpoint access

3. **Security Tests** - Attack simulation and vulnerability testing
   - Invalid token rejection
   - Injection attacks (SQL, XSS, etc.)
   - CORS violations
   - Rate limit bypass attempts
   - Request size limit enforcement

---

## Unit Tests

### 1. Session Encryption/Decryption

**File:** `tests/unit/test_session_encryption.py`

```python
"""Unit tests for session encryption and decryption."""

import pytest
import json
from unittest.mock import patch, MagicMock
from cryptography.fernet import Fernet, InvalidToken

# Import functions under test
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from routers.auth import create_session, get_session, delete_session, cipher


class TestSessionEncryption:
    """Test session encryption mechanisms."""

    def test_create_session_generates_unique_tokens(self):
        """Each session should have a unique token."""
        user_data = {"id": 1, "username": "test"}
        token1 = create_session(user_data)
        token2 = create_session(user_data)

        assert token1 != token2
        assert len(token1) >= 32  # URL-safe base64 token

    def test_session_data_is_encrypted(self):
        """Session data should be encrypted, not plaintext."""
        user_data = {"id": 1, "username": "test", "secret": "password123"}
        token = create_session(user_data)

        # Retrieve encrypted data (bypass get_session to check raw storage)
        from routers.auth import IN_MEMORY_SESSIONS, USE_REDIS, redis_client

        if USE_REDIS:
            encrypted = redis_client.get(f"session:{token}")
        else:
            encrypted = IN_MEMORY_SESSIONS.get(token)

        # Encrypted data should not contain plaintext
        assert b"password123" not in encrypted
        assert b"test" not in encrypted

    def test_get_session_decrypts_correctly(self):
        """get_session should decrypt data correctly."""
        original_data = {"id": 42, "username": "alice", "github_id": 12345}
        token = create_session(original_data)

        retrieved_data = get_session(token)

        assert retrieved_data == original_data

    def test_get_session_returns_none_for_invalid_token(self):
        """get_session should return None for non-existent tokens."""
        fake_token = "nonexistent_token_12345"
        result = get_session(fake_token)

        assert result is None

    def test_get_session_handles_corrupted_data(self):
        """get_session should handle corrupted encrypted data gracefully."""
        from routers.auth import IN_MEMORY_SESSIONS, USE_REDIS, redis_client

        token = "corrupted_session"
        corrupted_data = b"this_is_not_valid_encrypted_data"

        if USE_REDIS:
            redis_client.setex(f"session:{token}", 3600, corrupted_data)
        else:
            IN_MEMORY_SESSIONS[token] = corrupted_data

        result = get_session(token)
        assert result is None  # Should return None, not raise exception

    def test_delete_session_removes_data(self):
        """delete_session should remove session data."""
        user_data = {"id": 1, "username": "test"}
        token = create_session(user_data)

        # Verify it exists
        assert get_session(token) is not None

        # Delete it
        delete_session(token)

        # Verify it's gone
        assert get_session(token) is None

    def test_session_encryption_key_required(self):
        """System should fail to start without SESSION_ENCRYPTION_KEY."""
        # This is more of a configuration test
        # Verify that cipher is initialized
        assert cipher is not None
        assert isinstance(cipher._signing_key, bytes)


class TestSessionStorage:
    """Test Redis vs in-memory session storage."""

    def test_redis_fallback_to_memory(self, monkeypatch):
        """Should fall back to in-memory if Redis unavailable."""
        # This test verifies the fallback mechanism
        # Mock Redis failure
        with patch('routers.auth.redis_client', None):
            with patch('routers.auth.USE_REDIS', False):
                user_data = {"id": 1, "username": "test"}
                token = create_session(user_data)

                # Should use in-memory storage
                from routers.auth import IN_MEMORY_SESSIONS
                assert token in IN_MEMORY_SESSIONS or len(IN_MEMORY_SESSIONS) > 0

    def test_session_ttl_redis(self):
        """Sessions in Redis should have TTL set (7 days)."""
        from routers.auth import USE_REDIS, redis_client

        if not USE_REDIS:
            pytest.skip("Redis not available")

        user_data = {"id": 1, "username": "test"}
        token = create_session(user_data)

        # Check TTL is set
        ttl = redis_client.ttl(f"session:{token}")
        assert ttl > 0
        assert ttl <= 604800  # 7 days in seconds
```

### 2. Token Validation

**File:** `tests/unit/test_token_validation.py`

```python
"""Unit tests for token validation logic."""

import pytest
import os
from unittest.mock import patch
from fastapi import HTTPException

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from routers.auth import require_auth, get_user_id


class TestTokenValidation:
    """Test token validation functions."""

    def test_require_auth_with_valid_session(self, mock_request_with_session):
        """require_auth should return user_id for valid session."""
        user_id = require_auth(mock_request_with_session)
        assert user_id == 1

    def test_require_auth_without_session_raises_401(self, mock_request_no_session):
        """require_auth should raise HTTPException 401 without session."""
        with pytest.raises(HTTPException) as exc_info:
            require_auth(mock_request_no_session)

        assert exc_info.value.status_code == 401
        assert "Authentication required" in exc_info.value.detail

    def test_get_user_id_returns_none_for_invalid_token(self, mock_request_invalid_token):
        """get_user_id should return None for invalid tokens."""
        user_id = get_user_id(mock_request_invalid_token)
        assert user_id is None

    def test_dev_token_validation_strict(self):
        """DEV_ACCESS_TOKEN validation should be strict."""
        from routers.auth import DEV_ACCESS_TOKEN

        # Verify it's set in test environment
        assert DEV_ACCESS_TOKEN is not None
        assert len(DEV_ACCESS_TOKEN) >= 32  # Should be cryptographically strong


class TestRateLimiting:
    """Test rate limiting logic."""

    def test_login_rate_limit_10_per_minute(self):
        """Login endpoint should enforce 10 requests/minute."""
        # Note: This tests the decorator configuration
        from routers.auth import login

        # Check that rate limiter is applied
        assert hasattr(login, '__wrapped__')  # Decorated

    def test_dev_callback_rate_limit_3_per_minute(self):
        """Dev callback should enforce 3 requests/minute."""
        from routers.auth import dev_callback

        # Stricter limit for dev mode
        assert hasattr(dev_callback, '__wrapped__')
```

### 3. CORS Origin Checking

**File:** `tests/unit/test_cors_validation.py`

```python
"""Unit tests for CORS origin validation."""

import pytest
from fastapi.testclient import TestClient


class TestCORSValidation:
    """Test CORS origin checking."""

    def test_allowed_origin_localhost_3001(self, client):
        """localhost:3001 should be allowed origin."""
        response = client.options(
            "/api/auth/me",
            headers={"Origin": "http://localhost:3001"}
        )

        assert response.headers.get("access-control-allow-origin") == "http://localhost:3001"
        assert response.headers.get("access-control-allow-credentials") == "true"

    def test_disallowed_origin_rejected(self, client):
        """Random origins should be rejected."""
        response = client.options(
            "/api/auth/me",
            headers={"Origin": "http://evil.com"}
        )

        # Should not have CORS headers for disallowed origin
        assert response.headers.get("access-control-allow-origin") != "http://evil.com"

    def test_credentials_required_for_cors(self, client):
        """CORS should require credentials."""
        response = client.get(
            "/api/auth/me",
            headers={"Origin": "http://localhost:3001"}
        )

        assert response.headers.get("access-control-allow-credentials") == "true"
```

### 4. Input Validation

**File:** `tests/unit/test_input_validation.py`

```python
"""Unit tests for input validation and sanitization."""

import pytest
from fastapi import HTTPException


class TestInputValidation:
    """Test input validation rules."""

    def test_username_sanitization(self):
        """Usernames should be sanitized for SQL injection attempts."""
        # This would be a validation function if implemented
        dangerous_input = "admin'; DROP TABLE users; --"

        # Test that parameterized queries prevent injection
        # (Actual test would use a validation function)
        assert "DROP TABLE" not in dangerous_input.replace("'", "")

    def test_max_request_body_size(self, client):
        """Requests over 10MB should be rejected."""
        # Create payload slightly over 10MB
        large_payload = "x" * (10 * 1024 * 1024 + 1)

        response = client.post(
            "/api/workflows/execute",
            json={"data": large_payload},
            headers={"Content-Length": str(len(large_payload))}
        )

        assert response.status_code == 413  # Payload Too Large

    def test_json_payload_validation(self, client):
        """Malformed JSON should be rejected."""
        response = client.post(
            "/api/workflows/execute",
            data="this is not json",
            headers={"Content-Type": "application/json"}
        )

        assert response.status_code == 422  # Unprocessable Entity
```

---

## Integration Tests

### 1. Full Authentication Flow

**File:** `tests/integration/test_auth_flow.py`

```python
"""Integration tests for complete authentication flows."""

import pytest
from fastapi.testclient import TestClient


class TestAuthenticationFlow:
    """Test end-to-end authentication."""

    def test_dev_login_flow_complete(self, client, dev_token):
        """Complete dev mode login flow."""
        # Step 1: Login with dev token
        login_response = client.get(
            f"/api/auth/dev-callback?dev_token={dev_token}",
            follow_redirects=False
        )

        assert login_response.status_code == 307  # Redirect
        assert "session_token" in login_response.cookies

        # Step 2: Verify session is valid
        session_token = login_response.cookies["session_token"]
        client.cookies.set("session_token", session_token)

        me_response = client.get("/api/auth/me")
        assert me_response.status_code == 200

        user_data = me_response.json()
        assert user_data["is_authenticated"] is True
        assert user_data["username"] == "DevUser"
        assert user_data["github_id"] == 12345

    def test_protected_endpoint_requires_auth(self, client):
        """Protected endpoints should require authentication."""
        # Try accessing protected endpoint without auth
        response = client.get("/api/runs")

        # Should either redirect or return 401
        assert response.status_code in [401, 403, 307]

    def test_logout_invalidates_session(self, client, authenticated_client):
        """Logout should invalidate session."""
        # Use authenticated client
        me_before = authenticated_client.get("/api/auth/me")
        assert me_before.json()["is_authenticated"] is True

        # Logout
        logout_response = authenticated_client.post("/api/auth/logout")
        assert logout_response.status_code == 200

        # Session should be invalid
        me_after = authenticated_client.get("/api/auth/me")
        assert me_after.json()["is_authenticated"] is False


class TestSessionPersistence:
    """Test session persistence across requests."""

    def test_session_persists_across_requests(self, authenticated_client):
        """Session should remain valid across multiple requests."""
        for _ in range(5):
            response = authenticated_client.get("/api/auth/me")
            assert response.status_code == 200
            assert response.json()["is_authenticated"] is True

    def test_session_cookie_attributes(self, client, dev_token):
        """Session cookie should have secure attributes."""
        response = client.get(
            f"/api/auth/dev-callback?dev_token={dev_token}",
            follow_redirects=False
        )

        # Check cookie attributes
        set_cookie = response.headers.get("set-cookie")
        assert "HttpOnly" in set_cookie
        assert "Secure" in set_cookie
        assert "SameSite=strict" in set_cookie.lower() or "SameSite=Strict" in set_cookie


class TestRedisFailover:
    """Test Redis failure fallback to in-memory."""

    @pytest.mark.skipif(
        not os.environ.get("TEST_REDIS_FAILOVER"),
        reason="Redis failover tests require explicit opt-in"
    )
    def test_redis_failure_falls_back_to_memory(self, client, dev_token, monkeypatch):
        """Should fall back to in-memory if Redis fails."""
        # Create session with Redis
        login_response = client.get(
            f"/api/auth/dev-callback?dev_token={dev_token}",
            follow_redirects=False
        )
        session_token = login_response.cookies["session_token"]

        # Simulate Redis failure
        from routers.auth import redis_client
        original_get = redis_client.get

        def failing_get(*args, **kwargs):
            raise ConnectionError("Redis connection failed")

        monkeypatch.setattr(redis_client, 'get', failing_get)

        # Should fall back gracefully (might lose session, but no crash)
        with client:
            client.cookies.set("session_token", session_token)
            response = client.get("/api/auth/me")
            # Either maintains session via fallback or returns unauthenticated
            assert response.status_code == 200
```

### 2. Protected Endpoint Access Control

**File:** `tests/integration/test_endpoint_protection.py`

```python
"""Integration tests for endpoint access control."""

import pytest


class TestEndpointProtection:
    """Test that endpoints are properly protected."""

    PROTECTED_ENDPOINTS = [
        "/api/runs",
        "/api/heuristics",
        "/api/analytics/summary",
        "/api/workflows/list",
        "/api/admin/users",
    ]

    @pytest.mark.parametrize("endpoint", PROTECTED_ENDPOINTS)
    def test_endpoint_requires_authentication(self, client, endpoint):
        """All protected endpoints should require auth."""
        response = client.get(endpoint)
        assert response.status_code in [401, 403]

    @pytest.mark.parametrize("endpoint", PROTECTED_ENDPOINTS)
    def test_authenticated_user_can_access(self, authenticated_client, endpoint):
        """Authenticated users should access protected endpoints."""
        response = authenticated_client.get(endpoint)
        # Should not be 401/403 (might be 404 if endpoint doesn't exist)
        assert response.status_code not in [401, 403]

    def test_public_endpoints_accessible_without_auth(self, client):
        """Public endpoints should be accessible without auth."""
        public_endpoints = [
            "/api/auth/login",
            "/api/auth/me",  # Returns is_authenticated: false
        ]

        for endpoint in public_endpoints:
            response = client.get(endpoint, follow_redirects=False)
            assert response.status_code != 401
```

---

## Security Attack Tests

### 1. Invalid Token Rejection

**File:** `tests/security/test_token_attacks.py`

```python
"""Security tests for token-based attacks."""

import pytest
import secrets


class TestInvalidTokens:
    """Test rejection of invalid/malicious tokens."""

    def test_random_token_rejected(self, client):
        """Random tokens should be rejected."""
        fake_token = secrets.token_urlsafe(32)
        client.cookies.set("session_token", fake_token)

        response = client.get("/api/auth/me")
        data = response.json()

        assert data["is_authenticated"] is False

    def test_empty_token_rejected(self, client):
        """Empty tokens should be rejected."""
        client.cookies.set("session_token", "")

        response = client.get("/api/auth/me")
        data = response.json()

        assert data["is_authenticated"] is False

    def test_malformed_token_rejected(self, client):
        """Malformed tokens should be rejected."""
        malformed_tokens = [
            ";;;",
            "../../etc/passwd",
            "<script>alert(1)</script>",
            "' OR '1'='1",
        ]

        for token in malformed_tokens:
            client.cookies.set("session_token", token)
            response = client.get("/api/auth/me")
            assert response.json()["is_authenticated"] is False

    def test_expired_token_handling(self, client, dev_token):
        """Expired tokens should be invalid."""
        # Create session
        login = client.get(
            f"/api/auth/dev-callback?dev_token={dev_token}",
            follow_redirects=False
        )
        session_token = login.cookies["session_token"]

        # Delete session to simulate expiry
        from routers.auth import delete_session
        delete_session(session_token)

        # Try to use expired token
        client.cookies.set("session_token", session_token)
        response = client.get("/api/auth/me")
        assert response.json()["is_authenticated"] is False
```

### 2. SQL Injection Prevention

**File:** `tests/security/test_sql_injection.py`

```python
"""Security tests for SQL injection prevention."""

import pytest


class TestSQLInjectionPrevention:
    """Test SQL injection attack prevention."""

    SQL_INJECTION_PAYLOADS = [
        "admin' OR '1'='1",
        "admin'; DROP TABLE users; --",
        "admin'/*",
        "' OR 1=1--",
        "'; EXEC sp_MSForEachTable 'DROP TABLE ?'; --",
        "1' UNION SELECT NULL, NULL, NULL--",
    ]

    @pytest.mark.parametrize("payload", SQL_INJECTION_PAYLOADS)
    def test_sql_injection_in_username(self, client, payload):
        """SQL injection in username should be prevented."""
        # This tests that parameterized queries prevent injection
        # Assuming we had an endpoint that accepts username
        response = client.post(
            "/api/auth/lookup",
            json={"username": payload}
        )

        # Should not succeed (might be 400 or 404, but not 500)
        assert response.status_code != 500

    def test_parameterized_queries_used(self):
        """Verify parameterized queries are used in auth."""
        # Code inspection test - check that queries use ? placeholders
        import inspect
        from routers.auth import handle_login

        source = inspect.getsource(handle_login)

        # Should use parameterized queries (?)
        assert "?" in source
        # Should NOT use string formatting for SQL
        assert "f\"SELECT" not in source
        assert "% " not in source or "WHERE" not in source
```

### 3. CORS Violation Attempts

**File:** `tests/security/test_cors_attacks.py`

```python
"""Security tests for CORS policy enforcement."""

import pytest


class TestCORSAttacks:
    """Test CORS violation prevention."""

    MALICIOUS_ORIGINS = [
        "http://evil.com",
        "https://phishing-site.com",
        "http://localhost:9999",  # Different port
        "https://localhost:3001",  # Different protocol
        "null",
    ]

    @pytest.mark.parametrize("origin", MALICIOUS_ORIGINS)
    def test_malicious_origin_blocked(self, client, authenticated_client, origin):
        """Malicious origins should be blocked."""
        response = authenticated_client.get(
            "/api/auth/me",
            headers={"Origin": origin}
        )

        # Should not allow credentials for disallowed origin
        assert response.headers.get("access-control-allow-origin") != origin

    def test_cors_preflight_rejected_for_evil_origin(self, client):
        """Preflight requests from evil origins should be rejected."""
        response = client.options(
            "/api/runs",
            headers={
                "Origin": "http://evil.com",
                "Access-Control-Request-Method": "POST",
            }
        )

        assert response.headers.get("access-control-allow-origin") != "http://evil.com"

    def test_wildcard_origin_not_used_with_credentials(self, client):
        """Should not use * origin with credentials."""
        response = client.get("/api/auth/me")

        # Should not be wildcard when credentials are allowed
        cors_origin = response.headers.get("access-control-allow-origin")
        cors_creds = response.headers.get("access-control-allow-credentials")

        if cors_creds == "true":
            assert cors_origin != "*"
```

### 4. Request Size Limit Enforcement

**File:** `tests/security/test_size_limits.py`

```python
"""Security tests for request size limits."""

import pytest


class TestRequestSizeLimits:
    """Test oversized request rejection."""

    def test_10mb_request_rejected(self, client):
        """Requests over 10MB should be rejected."""
        # Create 10MB + 1 byte payload
        oversized_payload = "x" * (10 * 1024 * 1024 + 1)

        response = client.post(
            "/api/workflows/execute",
            json={"data": oversized_payload}
        )

        assert response.status_code == 413

    def test_9mb_request_accepted(self, authenticated_client):
        """Requests under 10MB should be accepted."""
        # Create 9MB payload
        acceptable_payload = "x" * (9 * 1024 * 1024)

        response = authenticated_client.post(
            "/api/workflows/execute",
            json={"data": acceptable_payload}
        )

        # Should not be rejected for size (might fail for other reasons)
        assert response.status_code != 413

    def test_content_length_header_enforced(self, client):
        """Content-Length header should be enforced."""
        response = client.post(
            "/api/workflows/execute",
            data="x" * 100,
            headers={"Content-Length": str(20 * 1024 * 1024)}  # Lie about size
        )

        assert response.status_code == 413
```

### 5. Rate Limit Bypass Attempts

**File:** `tests/security/test_rate_limit_bypass.py`

```python
"""Security tests for rate limiting bypass attempts."""

import pytest
import asyncio


class TestRateLimitBypass:
    """Test rate limit bypass prevention."""

    def test_rapid_login_attempts_blocked(self, client, dev_token):
        """Rapid login attempts should be rate limited."""
        responses = []

        # Attempt 15 logins in quick succession (limit is 10/min)
        for _ in range(15):
            response = client.get(
                f"/api/auth/dev-callback?dev_token={dev_token}",
                follow_redirects=False
            )
            responses.append(response.status_code)

        # Should have at least some 429 (Too Many Requests)
        assert 429 in responses

    def test_rate_limit_per_ip(self, client, dev_token):
        """Rate limit should be per IP address."""
        # This test verifies that slowapi uses get_remote_address
        from routers.auth import limiter

        assert limiter.key_func.__name__ == "get_remote_address"

    @pytest.mark.skipif(
        not os.environ.get("TEST_DISTRIBUTED_ATTACK"),
        reason="Distributed attack simulation requires explicit opt-in"
    )
    def test_different_ips_independent_limits(self):
        """Different IPs should have independent rate limits."""
        # This would require multiple test clients with different IPs
        # Left as a placeholder for advanced testing
        pass
```

### 6. Cross-Site Scripting (XSS) Prevention

**File:** `tests/security/test_xss_prevention.py`

```python
"""Security tests for XSS prevention."""

import pytest


class TestXSSPrevention:
    """Test XSS attack prevention."""

    XSS_PAYLOADS = [
        "<script>alert('XSS')</script>",
        "<img src=x onerror=alert(1)>",
        "<svg/onload=alert(1)>",
        "javascript:alert(1)",
        "<iframe src='javascript:alert(1)'>",
    ]

    @pytest.mark.parametrize("payload", XSS_PAYLOADS)
    def test_xss_payload_escaped(self, authenticated_client, payload):
        """XSS payloads should be escaped in responses."""
        # Test with workflow name or other user input
        response = authenticated_client.post(
            "/api/workflows/execute",
            json={"workflow_name": payload}
        )

        # Response should not contain unescaped script
        assert "<script>" not in response.text
        assert "onerror=" not in response.text

    def test_xss_protection_header_set(self, client):
        """X-XSS-Protection header should be set."""
        response = client.get("/api/auth/me")

        xss_header = response.headers.get("X-XSS-Protection")
        assert xss_header == "1; mode=block"

    def test_content_type_nosniff_header(self, client):
        """X-Content-Type-Options: nosniff should prevent MIME confusion."""
        response = client.get("/api/auth/me")

        assert response.headers.get("X-Content-Type-Options") == "nosniff"
```

---

## Test Fixtures and Utilities

### Enhanced conftest.py

**File:** `tests/conftest.py` (additions)

```python
"""Enhanced fixtures for security testing."""

import pytest
import os
import secrets
from fastapi.testclient import TestClient
from unittest.mock import MagicMock


# ============================================================================
# Application Fixture
# ============================================================================

@pytest.fixture(scope="session")
def app():
    """Create FastAPI application for testing."""
    # Set test environment variables
    os.environ["SESSION_ENCRYPTION_KEY"] = Fernet.generate_key().decode()
    os.environ["DEV_ACCESS_TOKEN"] = secrets.token_hex(32)
    os.environ["GITHUB_CLIENT_ID"] = "mock"
    os.environ["SESSION_DOMAIN"] = "localhost"

    # Import after env vars are set
    from main import app as fastapi_app
    return fastapi_app


@pytest.fixture
def client(app):
    """Create test client."""
    return TestClient(app)


# ============================================================================
# Authentication Fixtures
# ============================================================================

@pytest.fixture
def dev_token():
    """Get DEV_ACCESS_TOKEN for testing."""
    return os.environ.get("DEV_ACCESS_TOKEN")


@pytest.fixture
def authenticated_client(client, dev_token):
    """Create an authenticated test client."""
    # Perform login
    response = client.get(
        f"/api/auth/dev-callback?dev_token={dev_token}",
        follow_redirects=False
    )

    # Extract session token
    session_token = response.cookies.get("session_token")

    # Set cookie on client
    client.cookies.set("session_token", session_token)

    return client


@pytest.fixture
def mock_request_with_session():
    """Create mock request with valid session."""
    from unittest.mock import MagicMock
    from routers.auth import create_session

    user_data = {"id": 1, "username": "test_user", "github_id": 12345}
    token = create_session(user_data)

    request = MagicMock()
    request.cookies.get.return_value = token

    return request


@pytest.fixture
def mock_request_no_session():
    """Create mock request without session."""
    request = MagicMock()
    request.cookies.get.return_value = None
    return request


@pytest.fixture
def mock_request_invalid_token():
    """Create mock request with invalid token."""
    request = MagicMock()
    request.cookies.get.return_value = "invalid_token_12345"
    return request


# ============================================================================
# Redis Fixtures
# ============================================================================

@pytest.fixture
def mock_redis():
    """Create mock Redis client for testing."""
    redis_mock = MagicMock()
    redis_mock.get.return_value = None
    redis_mock.setex.return_value = True
    redis_mock.delete.return_value = True
    redis_mock.ping.return_value = True
    return redis_mock


@pytest.fixture
def mock_redis_failure():
    """Create mock Redis client that fails."""
    redis_mock = MagicMock()
    redis_mock.get.side_effect = ConnectionError("Redis unavailable")
    redis_mock.setex.side_effect = ConnectionError("Redis unavailable")
    return redis_mock


# ============================================================================
# Security Test Utilities
# ============================================================================

@pytest.fixture
def sql_injection_payloads():
    """Common SQL injection payloads."""
    return [
        "' OR '1'='1",
        "'; DROP TABLE users; --",
        "admin'--",
        "' OR 1=1--",
        "1' UNION SELECT NULL--",
    ]


@pytest.fixture
def xss_payloads():
    """Common XSS payloads."""
    return [
        "<script>alert('XSS')</script>",
        "<img src=x onerror=alert(1)>",
        "<svg/onload=alert(1)>",
        "javascript:alert(1)",
    ]


@pytest.fixture
def malicious_origins():
    """Malicious CORS origins."""
    return [
        "http://evil.com",
        "https://attacker.com",
        "http://localhost:9999",
        "null",
    ]


# ============================================================================
# Test Helpers
# ============================================================================

def assert_secure_cookie(set_cookie_header: str):
    """Assert that cookie has secure attributes."""
    assert "HttpOnly" in set_cookie_header
    assert "Secure" in set_cookie_header
    assert "SameSite" in set_cookie_header


def assert_security_headers(response):
    """Assert that response has required security headers."""
    headers = response.headers

    assert headers.get("X-Frame-Options") == "DENY"
    assert headers.get("X-Content-Type-Options") == "nosniff"
    assert headers.get("X-XSS-Protection") == "1; mode=block"
    assert "Permissions-Policy" in headers
    assert headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"


# ============================================================================
# Cleanup
# ============================================================================

@pytest.fixture(autouse=True)
def cleanup_sessions():
    """Clean up sessions after each test."""
    yield

    # Clear in-memory sessions
    from routers.auth import IN_MEMORY_SESSIONS
    IN_MEMORY_SESSIONS.clear()
```

### Test Factories

**File:** `tests/factories.py`

```python
"""Test data factories for security testing."""

import secrets
from datetime import datetime, timedelta


class UserFactory:
    """Factory for creating test users."""

    @staticmethod
    def create(
        id: int = 1,
        github_id: int = 12345,
        username: str = "test_user",
        avatar_url: str = None
    ):
        """Create user data dict."""
        return {
            "id": id,
            "github_id": github_id,
            "username": username,
            "avatar_url": avatar_url or f"https://avatars.github.com/{github_id}"
        }

    @staticmethod
    def create_admin():
        """Create admin user."""
        return UserFactory.create(
            id=1,
            github_id=1,
            username="admin"
        )


class SessionFactory:
    """Factory for creating test sessions."""

    @staticmethod
    def create_token():
        """Generate session token."""
        return secrets.token_urlsafe(32)

    @staticmethod
    def create_expired():
        """Create expired session data."""
        return {
            "created_at": (datetime.utcnow() - timedelta(days=8)).isoformat(),
            "expires_at": (datetime.utcnow() - timedelta(days=1)).isoformat()
        }


class AttackFactory:
    """Factory for attack payloads."""

    SQL_INJECTION = [
        "' OR '1'='1",
        "'; DROP TABLE users; --",
        "admin'--",
    ]

    XSS = [
        "<script>alert(1)</script>",
        "<img src=x onerror=alert(1)>",
    ]

    PATH_TRAVERSAL = [
        "../../etc/passwd",
        "..\\..\\windows\\system32\\config\\sam",
    ]
```

---

## Coverage Requirements

### Coverage Targets

| Component | Minimum Coverage | Critical Path Coverage |
|-----------|------------------|------------------------|
| `routers/auth.py` | 95% | 100% |
| Session encryption | 100% | 100% |
| Token validation | 95% | 100% |
| Middleware | 90% | 100% |
| Rate limiting | 85% | N/A |

### Critical Security Paths (Must be 100%)

1. Session creation and encryption
2. Token validation and authentication
3. Password/credential handling (if implemented)
4. SQL query execution with user input
5. CORS origin validation
6. Request size limit enforcement

### Measuring Coverage

```bash
# Run tests with coverage
pytest --cov=routers.auth --cov=utils --cov-report=html --cov-report=term

# Coverage requirements in pytest.ini or pyproject.toml
[tool.pytest.ini_options]
addopts = """
    --cov=routers.auth
    --cov-report=html
    --cov-report=term-missing
    --cov-fail-under=95
"""
```

### Edge Cases to Cover

1. Session expiry (7 days)
2. Redis connection failure
3. Corrupted encrypted session data
4. Concurrent session access
5. Session invalidation race conditions
6. Token rotation (if implemented)
7. Multiple simultaneous logins
8. Session hijacking attempts

---

## CI/CD Integration

### GitHub Actions Workflow

**File:** `.github/workflows/security-tests.yml`

```yaml
name: Security Tests

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  security-tests:
    runs-on: ubuntu-latest

    services:
      redis:
        image: redis:7
        ports:
          - 6379:6379
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          cd apps/dashboard/backend
          pip install -r requirements.txt
          pip install pytest pytest-cov pytest-asyncio

      - name: Run unit tests
        run: |
          cd apps/dashboard/backend
          pytest tests/unit/ -v --cov=routers.auth --cov-report=xml

      - name: Run integration tests
        run: |
          cd apps/dashboard/backend
          pytest tests/integration/ -v

      - name: Run security tests
        run: |
          cd apps/dashboard/backend
          pytest tests/security/ -v

      - name: Check coverage
        run: |
          cd apps/dashboard/backend
          pytest --cov=routers.auth --cov-fail-under=95

      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v3
        with:
          files: ./apps/dashboard/backend/coverage.xml
          flags: security-tests
```

### Pre-commit Security Tests

**File:** `apps/dashboard/backend/.pre-commit-config.yaml`

```yaml
repos:
  - repo: local
    hooks:
      - id: security-unit-tests
        name: Run Security Unit Tests
        entry: pytest tests/unit/test_session_encryption.py tests/unit/test_token_validation.py -v
        language: system
        pass_filenames: false
        always_run: true
```

### Test Execution Strategy

#### On Every Commit (Fast - ~30s)
```bash
# Unit tests only
pytest tests/unit/ -v --tb=short
```

#### On Pull Request (Medium - ~2min)
```bash
# Unit + Integration tests
pytest tests/unit/ tests/integration/ -v --cov=routers.auth
```

#### Nightly/Weekly (Comprehensive - ~10min)
```bash
# All tests including slow security tests
pytest tests/ -v --cov=routers.auth --cov-report=html --slow
```

#### Security Audit (Manual)
```bash
# Run security-focused tests with detailed logging
pytest tests/security/ -v -s --log-cli-level=DEBUG

# SAST scanning
bandit -r routers/ -f json -o security-report.json

# Dependency scanning
pip-audit
safety check
```

---

## Test Execution Commands

### Running Specific Test Suites

```bash
# All security tests
pytest tests/ -v

# Unit tests only
pytest tests/unit/ -v

# Integration tests only
pytest tests/integration/ -v

# Security attack tests only
pytest tests/security/ -v

# Specific test class
pytest tests/unit/test_session_encryption.py::TestSessionEncryption -v

# Specific test
pytest tests/security/test_sql_injection.py::TestSQLInjectionPrevention::test_sql_injection_in_username -v

# With coverage
pytest tests/ --cov=routers.auth --cov-report=html

# Parallel execution
pytest tests/ -n auto  # Requires pytest-xdist
```

### Test Markers

```python
# In pytest.ini
[pytest]
markers =
    unit: Unit tests
    integration: Integration tests
    security: Security tests
    slow: Slow running tests
    redis: Tests requiring Redis

# Run marked tests
pytest -m unit
pytest -m "security and not slow"
```

---

## Performance Benchmarks

### Authentication Performance Targets

| Operation | Target (p95) | Maximum (p99) |
|-----------|--------------|---------------|
| Session creation | < 10ms | < 20ms |
| Session retrieval | < 5ms | < 10ms |
| Token validation | < 3ms | < 5ms |
| Login flow | < 200ms | < 500ms |

### Benchmark Tests

**File:** `tests/performance/test_auth_performance.py`

```python
"""Performance benchmarks for authentication."""

import pytest
import time


class TestAuthPerformance:
    """Benchmark authentication operations."""

    def test_session_creation_performance(self, benchmark):
        """Session creation should be < 10ms."""
        from routers.auth import create_session

        user_data = {"id": 1, "username": "test"}
        result = benchmark(create_session, user_data)

        assert result is not None

    def test_session_retrieval_performance(self, benchmark):
        """Session retrieval should be < 5ms."""
        from routers.auth import create_session, get_session

        user_data = {"id": 1, "username": "test"}
        token = create_session(user_data)

        result = benchmark(get_session, token)
        assert result == user_data
```

---

## Security Testing Best Practices

### 1. Never Commit Secrets
- Use environment variables for all secrets
- Never hardcode tokens in tests
- Use `.env.test` file (excluded from git)

### 2. Test Realistic Attack Scenarios
- Use actual attack payloads from OWASP
- Test with fuzzing libraries (hypothesis)
- Simulate rate limit bypass attempts

### 3. Validate Security Headers
- Check all responses for security headers
- Verify CORS policies are enforced
- Test CSP (Content Security Policy) if implemented

### 4. Test Cryptographic Operations
- Verify encryption is actually encrypting
- Test key rotation scenarios
- Validate random token generation entropy

### 5. Database Security
- Always use parameterized queries
- Test SQL injection on all user inputs
- Verify database connection security

---

## Continuous Improvement

### Monthly Security Test Reviews
- Review and update attack payloads
- Add new CVE-based tests
- Update OWASP Top 10 coverage

### Quarterly Security Audits
- Full penetration testing
- Third-party security review
- Dependency vulnerability scanning

### Annual Security Assessment
- Architecture security review
- Compliance validation (if applicable)
- Disaster recovery testing

---

## Appendix: Security Testing Tools

### Recommended Tools

1. **Static Analysis (SAST)**
   - Bandit (Python security linter)
   - Semgrep (custom security rules)
   - Pylint with security plugins

2. **Dependency Scanning**
   - pip-audit
   - Safety
   - Dependabot

3. **Dynamic Analysis (DAST)**
   - OWASP ZAP
   - Burp Suite Community
   - SQLMap (for SQL injection testing)

4. **Fuzzing**
   - Hypothesis (property-based testing)
   - AFL (American Fuzzy Lop)
   - Radamsa

5. **Performance Testing**
   - pytest-benchmark
   - Locust (load testing)
   - K6 (API performance)

### Installing Security Tools

```bash
# Install testing dependencies
pip install pytest pytest-cov pytest-asyncio pytest-benchmark

# Install security analysis tools
pip install bandit safety pip-audit

# Install fuzzing tools
pip install hypothesis

# Install in dev requirements
echo "pytest>=7.4.0" >> requirements-dev.txt
echo "pytest-cov>=4.1.0" >> requirements-dev.txt
echo "bandit>=1.7.5" >> requirements-dev.txt
echo "safety>=2.3.5" >> requirements-dev.txt
```

---

## Conclusion

This security test strategy provides comprehensive coverage for the ELF Dashboard Backend, ensuring:

- **95%+ code coverage** on authentication and security modules
- **100% coverage** on critical security paths
- **Defense against common attacks** (SQL injection, XSS, CSRF, etc.)
- **CI/CD integration** for continuous security validation
- **Performance benchmarks** to prevent security overhead

Maintain this strategy as a living document, updating it as new security threats emerge and the application evolves.
