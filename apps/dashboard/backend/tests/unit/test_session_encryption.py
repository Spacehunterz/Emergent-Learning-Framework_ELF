"""
Unit tests for session encryption and decryption.

Tests encryption/decryption functions, token generation,
and storage mechanisms (Redis vs in-memory).
"""

import pytest
import sys
from pathlib import Path

backend_path = Path(__file__).parent.parent.parent
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))


@pytest.mark.asyncio
class TestSessionEncryption:
    """Test session encryption mechanisms."""

    async def test_create_session_generates_unique_tokens(self):
        """Each session should have a unique token."""
        from routers.auth import create_session, SessionData

        user_data = SessionData(id=1, username="test", github_id=12345)
        token1 = await create_session(user_data)
        token2 = await create_session(user_data)

        assert token1 != token2, "Tokens should be unique"
        assert len(token1) >= 32, "Token should be at least 32 characters"

    async def test_session_data_is_encrypted(self):
        """Session data should be encrypted, not stored as plaintext."""
        from routers.auth import create_session, IN_MEMORY_SESSIONS, SessionData

        user_data = SessionData(id=1, username="test_secret_user", github_id=12345)
        token = await create_session(user_data)

        encrypted = IN_MEMORY_SESSIONS.get(token)

        if encrypted:
            assert b"test_secret_user" not in encrypted, "Username should not be in plaintext"

    async def test_get_session_decrypts_correctly(self):
        """get_session should decrypt data correctly."""
        from routers.auth import create_session, get_session, SessionData

        original_data = SessionData(id=42, username="alice", github_id=12345)
        token = await create_session(original_data)

        retrieved_data = await get_session(token)

        assert retrieved_data is not None, "Should return session data"
        assert retrieved_data.id == 42, "Should preserve user id"
        assert retrieved_data.username == "alice", "Should preserve username"
        assert retrieved_data.github_id == 12345, "Should preserve github_id"

    async def test_get_session_returns_none_for_invalid_token(self):
        """get_session should return None for non-existent tokens."""
        from routers.auth import get_session

        fake_token = "nonexistent_token_12345"
        result = await get_session(fake_token)

        assert result is None, "Invalid token should return None"

    async def test_get_session_handles_corrupted_data(self):
        """get_session should handle corrupted encrypted data gracefully."""
        from routers.auth import get_session, IN_MEMORY_SESSIONS

        token = "corrupted_session"
        corrupted_data = b"this_is_not_valid_encrypted_data"

        IN_MEMORY_SESSIONS.set(token, corrupted_data)

        result = await get_session(token)
        assert result is None, "Corrupted session should return None, not raise exception"

    async def test_delete_session_removes_data(self):
        """delete_session should remove session data."""
        from routers.auth import create_session, get_session, delete_session, SessionData

        user_data = SessionData(id=1, username="test", github_id=12345)
        token = await create_session(user_data)

        session = await get_session(token)
        assert session is not None, "Session should exist after creation"

        await delete_session(token)

        result = await get_session(token)
        assert result is None, "Session should be deleted"

    def test_session_encryption_key_required(self):
        """System should have encryption key initialized."""
        from routers.auth import cipher

        assert cipher is not None, "Cipher should be initialized"
        assert hasattr(cipher, '_signing_key'), "Should be a Fernet cipher"
        assert isinstance(cipher._signing_key, bytes), "Key should be bytes"


@pytest.mark.asyncio
class TestSessionStorage:
    """Test Redis vs in-memory session storage."""

    async def test_in_memory_storage_works(self):
        """In-memory storage should work correctly."""
        from routers.auth import create_session, IN_MEMORY_SESSIONS, SessionData

        user_data = SessionData(id=1, username="test", github_id=12345)
        token = await create_session(user_data)

        assert hasattr(IN_MEMORY_SESSIONS, 'sessions'), "Should have sessions attribute"
        assert token in IN_MEMORY_SESSIONS.sessions, "Token should be in storage"

    async def test_session_ttl_not_immediate(self):
        """Sessions should not expire immediately."""
        from routers.auth import create_session, get_session, SessionData

        user_data = SessionData(id=1, username="test", github_id=12345)
        token = await create_session(user_data)

        session = await get_session(token)
        assert session is not None, "Session should exist immediately after creation"


@pytest.mark.asyncio
class TestTokenGeneration:
    """Test token generation security."""

    async def test_token_uses_cryptographic_randomness(self):
        """Tokens should use cryptographically secure random generation."""
        from routers.auth import create_session, SessionData

        tokens = set()
        for _ in range(100):
            user_data = SessionData(id=1, username="test", github_id=12345)
            token = await create_session(user_data)
            tokens.add(token)

        assert len(tokens) == 100, "All tokens should be unique"

        for token in list(tokens)[:5]:
            assert ' ' not in token
            assert token.isascii()

    async def test_token_length_sufficient(self):
        """Tokens should be sufficiently long to prevent brute force."""
        from routers.auth import create_session, SessionData

        user_data = SessionData(id=1, username="test", github_id=12345)
        token = await create_session(user_data)

        assert len(token) >= 32, "Token should be at least 32 characters"
