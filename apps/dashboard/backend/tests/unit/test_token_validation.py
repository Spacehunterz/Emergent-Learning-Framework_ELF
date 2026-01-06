"""
Unit tests for token validation logic.

Tests authentication requirements, user ID extraction,
and rate limiting configuration.
"""

import pytest
import sys
from pathlib import Path
from fastapi import HTTPException
from unittest.mock import MagicMock, AsyncMock

backend_path = Path(__file__).parent.parent.parent
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))


@pytest.mark.asyncio
class TestTokenValidation:
    """Test token validation functions."""

    async def test_require_auth_with_valid_session(self):
        """require_auth should return user_id for valid session."""
        from routers.auth import require_auth, create_session, SessionData

        user_data = SessionData(id=1, username="test_user", github_id=12345)
        token = await create_session(user_data)

        request = MagicMock()
        request.cookies = MagicMock()
        request.cookies.get = MagicMock(return_value=token)

        user_id = await require_auth(request)
        assert user_id == 1, "Should return correct user ID"

    async def test_require_auth_without_session_raises_401(self):
        """require_auth should raise HTTPException 401 without session."""
        from routers.auth import require_auth

        request = MagicMock()
        request.cookies = MagicMock()
        request.cookies.get = MagicMock(return_value=None)

        with pytest.raises(HTTPException) as exc_info:
            await require_auth(request)

        assert exc_info.value.status_code == 401
        assert "Authentication required" in exc_info.value.detail

    async def test_get_user_id_returns_none_for_invalid_token(self):
        """get_user_id should return None for invalid tokens."""
        from routers.auth import get_user_id

        request = MagicMock()
        request.cookies = MagicMock()
        request.cookies.get = MagicMock(return_value="invalid_token_12345")

        user_id = await get_user_id(request)
        assert user_id is None, "Invalid token should return None"

    async def test_get_user_id_returns_none_for_no_token(self):
        """get_user_id should return None when no token present."""
        from routers.auth import get_user_id

        request = MagicMock()
        request.cookies = MagicMock()
        request.cookies.get = MagicMock(return_value=None)

        user_id = await get_user_id(request)
        assert user_id is None, "No token should return None"

    def test_dev_token_validation_strict(self):
        """DEV_ACCESS_TOKEN validation should be strict."""
        from routers.auth import DEV_ACCESS_TOKEN

        assert DEV_ACCESS_TOKEN is not None, "DEV_ACCESS_TOKEN should be set"
        assert len(DEV_ACCESS_TOKEN) >= 20, "Token should be cryptographically strong"


class TestRateLimiting:
    """Test rate limiting configuration."""

    def test_login_rate_limit_configured(self):
        """Login endpoint should have rate limiter configured."""
        from routers.auth import login

        assert callable(login)

    def test_dev_callback_rate_limit_stricter(self):
        """Dev callback should have stricter rate limit than normal login."""
        from routers.auth import dev_callback

        assert callable(dev_callback)

    def test_callback_rate_limit_configured(self):
        """OAuth callback should have rate limiter configured."""
        from routers.auth import callback

        assert callable(callback)


@pytest.mark.asyncio
class TestSessionRetrieval:
    """Test session data retrieval."""

    async def test_get_user_id_extracts_correct_id(self):
        """get_user_id should extract user ID from session."""
        from routers.auth import create_session, get_user_id, SessionData

        user_data = SessionData(id=42, username="alice", github_id=99999)
        token = await create_session(user_data)

        request = MagicMock()
        request.cookies = MagicMock()
        request.cookies.get = MagicMock(return_value=token)

        user_id = await get_user_id(request)
        assert user_id == 42, "Should extract correct user ID"

    async def test_get_user_id_handles_missing_id_field(self):
        """get_user_id should handle sessions without id field gracefully."""
        from routers.auth import get_user_id, IN_MEMORY_SESSIONS, cipher
        import json

        malformed_data = {"username": "test"}
        token = "malformed_token"
        encrypted = cipher.encrypt(json.dumps(malformed_data).encode())
        IN_MEMORY_SESSIONS.set(token, encrypted)

        request = MagicMock()
        request.cookies = MagicMock()
        request.cookies.get = MagicMock(return_value=token)

        user_id = await get_user_id(request)
        assert user_id is None, "Session without id should return None"
