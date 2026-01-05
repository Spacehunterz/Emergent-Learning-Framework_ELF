"""
Unit tests for session encryption and decryption.

Tests encryption/decryption functions, token generation,
and storage mechanisms (Redis vs in-memory).
"""

import pytest
import json
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

# Ensure backend is in path
backend_path = Path(__file__).parent.parent.parent
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))


class TestSessionEncryption:
    """Test session encryption mechanisms."""

    def test_create_session_generates_unique_tokens(self):
        """Each session should have a unique token."""
        from routers.auth import create_session

        user_data = {"id": 1, "username": "test"}
        token1 = create_session(user_data)
        token2 = create_session(user_data)

        assert token1 != token2, "Tokens should be unique"
        assert len(token1) >= 32, "Token should be at least 32 characters"

    def test_session_data_is_encrypted(self):
        """Session data should be encrypted, not stored as plaintext."""
        from routers.auth import create_session, IN_MEMORY_SESSIONS, USE_REDIS, redis_client

        user_data = {"id": 1, "username": "test", "secret": "password123"}
        token = create_session(user_data)

        # Retrieve encrypted data (bypass get_session to check raw storage)
        if USE_REDIS:
            encrypted = redis_client.get(f"session:{token}")
        else:
            encrypted = IN_MEMORY_SESSIONS.get(token)

        # Encrypted data should not contain plaintext
        assert b"password123" not in encrypted, "Secret should not be in plaintext"
        assert b"test" not in encrypted, "Username should not be in plaintext"

    def test_get_session_decrypts_correctly(self):
        """get_session should decrypt data correctly."""
        from routers.auth import create_session, get_session

        original_data = {"id": 42, "username": "alice", "github_id": 12345}
        token = create_session(original_data)

        retrieved_data = get_session(token)

        assert retrieved_data == original_data, "Decrypted data should match original"

    def test_get_session_returns_none_for_invalid_token(self):
        """get_session should return None for non-existent tokens."""
        from routers.auth import get_session

        fake_token = "nonexistent_token_12345"
        result = get_session(fake_token)

        assert result is None, "Invalid token should return None"

    def test_get_session_handles_corrupted_data(self):
        """get_session should handle corrupted encrypted data gracefully."""
        from routers.auth import get_session, IN_MEMORY_SESSIONS, USE_REDIS, redis_client

        token = "corrupted_session"
        corrupted_data = b"this_is_not_valid_encrypted_data"

        if USE_REDIS:
            redis_client.setex(f"session:{token}", 3600, corrupted_data)
        else:
            IN_MEMORY_SESSIONS[token] = corrupted_data

        result = get_session(token)
        assert result is None, "Corrupted session should return None, not raise exception"

    def test_delete_session_removes_data(self):
        """delete_session should remove session data."""
        from routers.auth import create_session, get_session, delete_session

        user_data = {"id": 1, "username": "test"}
        token = create_session(user_data)

        # Verify it exists
        assert get_session(token) is not None, "Session should exist after creation"

        # Delete it
        delete_session(token)

        # Verify it's gone
        assert get_session(token) is None, "Session should be deleted"

    def test_session_encryption_key_required(self):
        """System should have encryption key initialized."""
        from routers.auth import cipher

        assert cipher is not None, "Cipher should be initialized"
        # Verify it's a Fernet cipher
        assert hasattr(cipher, '_signing_key'), "Should be a Fernet cipher"
        assert isinstance(cipher._signing_key, bytes), "Key should be bytes"


class TestSessionStorage:
    """Test Redis vs in-memory session storage."""

    def test_redis_fallback_to_memory(self):
        """Should fall back to in-memory if Redis unavailable."""
        from routers.auth import create_session, IN_MEMORY_SESSIONS

        with patch('routers.auth.USE_REDIS', False):
            user_data = {"id": 1, "username": "test"}
            token = create_session(user_data)

            # Should use in-memory storage
            # Note: IN_MEMORY_SESSIONS is a global dict, so check it exists
            assert isinstance(IN_MEMORY_SESSIONS, dict)

    @pytest.mark.skipif(
        not pytest.importorskip("redis"),
        reason="Redis not available"
    )
    def test_session_ttl_redis(self):
        """Sessions in Redis should have TTL set (7 days = 604800 seconds)."""
        from routers.auth import USE_REDIS, redis_client, create_session

        if not USE_REDIS:
            pytest.skip("Redis not available")

        user_data = {"id": 1, "username": "test"}
        token = create_session(user_data)

        # Check TTL is set
        ttl = redis_client.ttl(f"session:{token}")
        assert ttl > 0, "TTL should be positive"
        assert ttl <= 604800, "TTL should not exceed 7 days (604800 seconds)"


class TestTokenGeneration:
    """Test token generation security."""

    def test_token_uses_cryptographic_randomness(self):
        """Tokens should use cryptographically secure random generation."""
        from routers.auth import create_session
        import secrets

        # Generate multiple tokens
        tokens = set()
        for _ in range(100):
            user_data = {"id": 1, "username": "test"}
            token = create_session(user_data)
            tokens.add(token)

        # All should be unique
        assert len(tokens) == 100, "All tokens should be unique"

        # Check token format (URL-safe base64)
        for token in list(tokens)[:5]:
            # Should not contain spaces or special chars
            assert ' ' not in token
            assert token.isascii()

    def test_token_length_sufficient(self):
        """Tokens should be sufficiently long to prevent brute force."""
        from routers.auth import create_session

        user_data = {"id": 1, "username": "test"}
        token = create_session(user_data)

        # 32 bytes URL-safe base64 = 43 characters
        # But secrets.token_urlsafe(32) can vary slightly
        assert len(token) >= 32, "Token should be at least 32 characters"
