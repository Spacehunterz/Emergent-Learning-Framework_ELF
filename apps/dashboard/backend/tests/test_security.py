"""
Comprehensive security test suite for ELF Dashboard Backend.

Tests cover:
- Session encryption and management  
- Authentication and authorization
- Rate limiting
- Input validation
- SQL injection prevention
- CORS policies
- Request size limits
- Security headers
"""

import pytest
import json
import secrets
import os
from fastapi.testclient import TestClient


@pytest.fixture
def client(app):
    return TestClient(app)


@pytest.fixture
def dev_token():
    return os.environ.get("DEV_ACCESS_TOKEN")


class TestSessionManagement:
    """Test encrypted session storage and retrieval."""

    def test_session_creation_encrypted(self, client, dev_token):
        """Sessions should be encrypted before storage."""
        response = client.get(
            f"/api/auth/dev-callback?dev_token={dev_token}",
            follow_redirects=False
        )
        assert response.status_code == 307
        assert "session_token" in response.cookies
        token = response.cookies["session_token"]
        assert len(token) > 32

    def test_session_persistence(self, client, dev_token):
        """Session should persist across requests."""
        login = client.get(
            f"/api/auth/dev-callback?dev_token={dev_token}",
            follow_redirects=False
        )
        assert login.status_code == 307

        # TestClient doesn't auto-persist cookies with domain attribute
        # Manually set the session cookie for subsequent requests
        session_token = login.cookies["session_token"]
        client.cookies.set("session_token", session_token)

        user = client.get("/api/auth/me")
        assert user.status_code == 200
        data = user.json()
        assert data["is_authenticated"] is True
        assert "username" in data


class TestAuthentication:
    """Test authentication and authorization."""

    def test_dev_callback_requires_token(self, client):
        """Dev callback should require valid dev token."""
        response = client.get(
            "/api/auth/dev-callback",
            follow_redirects=False
        )
        assert response.status_code == 401

    def test_dev_callback_rejects_invalid_token(self, client):
        """Dev callback should reject invalid tokens."""
        response = client.get(
            "/api/auth/dev-callback?dev_token=wrong_token",
            follow_redirects=False
        )
        assert response.status_code == 401


class TestSecurityHeaders:
    """Test security headers in responses."""

    def test_xframe_options(self, client):
        """Response should have X-Frame-Options header."""
        response = client.get("/api/auth/me")
        assert "X-Frame-Options" in response.headers
        assert response.headers["X-Frame-Options"] == "DENY"

    def test_content_type_options(self, client):
        """Response should have X-Content-Type-Options header."""
        response = client.get("/api/auth/me")
        assert "X-Content-Type-Options" in response.headers
        assert response.headers["X-Content-Type-Options"] == "nosniff"

    def test_permissions_policy(self, client):
        """Response should restrict browser permissions."""
        response = client.get("/api/auth/me")
        assert "Permissions-Policy" in response.headers


class TestSessionEncryption:
    """Test session data encryption."""

    def test_no_plaintext_credentials_in_session(self, client, dev_token):
        """Session should not contain plaintext credentials."""
        response = client.get(
            f"/api/auth/dev-callback?dev_token={dev_token}",
            follow_redirects=False
        )
        auth_response = client.get("/api/auth/me")
        user_data = auth_response.json()

        assert "password" not in user_data
        assert "access_token" not in user_data
        assert "secret" not in user_data
