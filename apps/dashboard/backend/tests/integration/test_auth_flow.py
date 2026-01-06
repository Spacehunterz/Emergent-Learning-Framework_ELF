"""
Integration tests for complete authentication flows.

Tests end-to-end login, logout, session persistence,
and protected endpoint access.
"""

import pytest
import sys
import sqlite3
from pathlib import Path
from contextlib import contextmanager
from unittest.mock import patch

# Ensure backend is in path
backend_path = Path(__file__).parent.parent.parent
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))


class TestAuthenticationFlow:
    """Test end-to-end authentication."""

    def test_dev_login_flow_complete(self, client, dev_token):
        """Complete dev mode login flow."""
        # Step 1: Login with dev token
        login_response = client.get(
            f"/api/auth/dev-callback?dev_token={dev_token}",
            follow_redirects=False
        )

        assert login_response.status_code == 307, "Should redirect after login"
        assert "session_token" in login_response.cookies, "Should set session cookie"

        # Step 2: Verify session is valid
        session_token = login_response.cookies["session_token"]
        client.cookies.set("session_token", session_token)

        me_response = client.get("/api/auth/me")
        assert me_response.status_code == 200

        user_data = me_response.json()
        assert user_data["is_authenticated"] is True, "User should be authenticated"
        assert user_data["username"] == "DevUser", "Username should be DevUser"
        assert user_data["github_id"] == 999999, "GitHub ID should match dev mock"

    def test_dev_login_requires_valid_token(self, client):
        """Dev login should reject invalid tokens."""
        response = client.get(
            "/api/auth/dev-callback?dev_token=wrong_token",
            follow_redirects=False
        )

        assert response.status_code == 401, "Should reject invalid token"

    def test_dev_login_requires_token_parameter(self, client):
        """Dev login should reject requests without token."""
        response = client.get(
            "/api/auth/dev-callback",
            follow_redirects=False
        )

        assert response.status_code == 401, "Should require token parameter"

    def test_logout_invalidates_session(self, authenticated_client):
        """Logout should invalidate session."""
        # Verify authenticated
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
        for i in range(5):
            response = authenticated_client.get("/api/auth/me")
            assert response.status_code == 200, f"Request {i} should succeed"
            assert response.json()["is_authenticated"] is True, f"Request {i} should be authenticated"

    def test_session_cookie_attributes(self, client, dev_token):
        """Session cookie should have secure attributes."""
        response = client.get(
            f"/api/auth/dev-callback?dev_token={dev_token}",
            follow_redirects=False
        )

        # Check cookie attributes
        set_cookie = response.headers.get("set-cookie")
        assert set_cookie is not None, "Should have Set-Cookie header"
        set_cookie_lower = set_cookie.lower()
        assert "httponly" in set_cookie_lower, "Cookie should be HttpOnly"
        assert "secure" in set_cookie_lower, "Cookie should be Secure"
        assert "samesite=strict" in set_cookie_lower, "Cookie should use SameSite=strict"

    def test_unauthenticated_user_info(self, client):
        """Unauthenticated requests should return is_authenticated=false."""
        response = client.get("/api/auth/me")

        assert response.status_code == 200
        data = response.json()
        assert data["is_authenticated"] is False, "Should not be authenticated"


class TestRedirectBehavior:
    """Test redirect behavior after authentication."""

    def test_login_redirects_to_frontend(self, client, dev_token):
        """Successful login should redirect to frontend."""
        response = client.get(
            f"/api/auth/dev-callback?dev_token={dev_token}",
            follow_redirects=False
        )

        assert response.status_code == 307, "Should return redirect status"
        assert "location" in response.headers, "Should have Location header"
        # Should redirect to frontend (localhost:3001)
        assert "3001" in response.headers["location"] or "localhost" in response.headers["location"]


class TestUserDataStorage:
    """Test that user data is properly stored in database."""

    @pytest.fixture
    def test_db_path(self, temp_db):
        """Get path to temp database and initialize tables."""
        conn = sqlite3.connect(str(temp_db), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        from utils.database import init_game_tables
        init_game_tables(conn)
        conn.close()
        return temp_db

    @pytest.fixture
    def patched_db(self, test_db_path):
        """Patch get_db to use the test database path."""
        @contextmanager
        def mock_get_db(scope="global"):
            conn = sqlite3.connect(str(test_db_path), check_same_thread=False)
            conn.row_factory = sqlite3.Row
            try:
                yield conn
            finally:
                conn.close()
        return mock_get_db

    def test_user_created_on_first_login(self, client, dev_token, test_db_path, patched_db):
        """First login should create user in database."""
        with patch("routers.auth.get_db", patched_db):
            client.get(
                f"/api/auth/dev-callback?dev_token={dev_token}",
                follow_redirects=False
            )

        conn = sqlite3.connect(str(test_db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE github_id = ?", (999999,))
        user = cursor.fetchone()
        conn.close()

        assert user is not None, "User should be created"
        assert user["username"] == "DevUser"

    def test_user_updated_on_subsequent_login(self, client, dev_token, test_db_path, patched_db):
        """Subsequent logins should update user data."""
        with patch("routers.auth.get_db", patched_db):
            client.get(
                f"/api/auth/dev-callback?dev_token={dev_token}",
                follow_redirects=False
            )

        conn = sqlite3.connect(str(test_db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET username = ? WHERE github_id = ?", ("OldUsername", 999999))
        conn.commit()
        conn.close()

        with patch("routers.auth.get_db", patched_db):
            client.get(
                f"/api/auth/dev-callback?dev_token={dev_token}",
                follow_redirects=False
            )

        conn = sqlite3.connect(str(test_db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT username FROM users WHERE github_id = ?", (999999,))
        user = cursor.fetchone()
        conn.close()

        assert user["username"] == "DevUser", "Username should be updated"


class TestConcurrentSessions:
    """Test multiple simultaneous sessions."""

    def test_multiple_sessions_independent(self, client, dev_token):
        """Multiple users should have independent sessions."""
        # Create first session
        response1 = client.get(
            f"/api/auth/dev-callback?dev_token={dev_token}",
            follow_redirects=False
        )
        token1 = response1.cookies["session_token"]

        # Create second session (simulates different user, but using same dev token)
        response2 = client.get(
            f"/api/auth/dev-callback?dev_token={dev_token}",
            follow_redirects=False
        )
        token2 = response2.cookies["session_token"]

        # Tokens should be different
        assert token1 != token2, "Different login attempts should get different tokens"

        # Both should be valid
        from routers.auth import get_session
        assert get_session(token1) is not None
        assert get_session(token2) is not None
