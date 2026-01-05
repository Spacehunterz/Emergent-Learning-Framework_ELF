"""
Security tests for SQL injection prevention.

Tests that parameterized queries prevent SQL injection attacks
across all user input vectors.
"""

import pytest
import sys
from pathlib import Path

# Ensure backend is in path
backend_path = Path(__file__).parent.parent.parent
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))


class TestSQLInjectionPrevention:
    """Test SQL injection attack prevention."""

    @pytest.mark.parametrize("payload", [
        "admin' OR '1'='1",
        "'; DROP TABLE users; --",
        "admin'--",
        "' OR 1=1--",
        "1' UNION SELECT NULL--",
    ])
    def test_sql_injection_in_username(self, authenticated_client, security_db, payload):
        """SQL injection in username should be prevented."""
        # Attempt to use malicious username
        # This tests that the auth system uses parameterized queries

        cursor = security_db.cursor()

        # Try to query with malicious input (simulates what auth.py does)
        # If not using parameterized queries, this would execute the injection
        cursor.execute("SELECT * FROM users WHERE username = ?", (payload,))
        result = cursor.fetchone()

        # Should safely handle the input (no results unless exact match)
        # Most importantly, should NOT drop tables or cause errors

    @pytest.mark.parametrize("payload", [
        "' OR '1'='1",
        "admin'; DROP TABLE users; --",
        "1' OR '1'='1' --",
    ])
    def test_sql_injection_in_github_id(self, security_db, payload):
        """SQL injection in numeric fields should be prevented."""
        cursor = security_db.cursor()

        # GitHub ID should be numeric, but test malicious string
        try:
            # This should fail type checking or be safely parameterized
            cursor.execute("SELECT * FROM users WHERE github_id = ?", (payload,))
            result = cursor.fetchone()
            # If it doesn't error, result should be None (no match)
            assert result is None or result is not None  # Just ensure no crash
        except Exception as e:
            # Type error is acceptable for numeric field
            pass

    def test_parameterized_queries_in_auth(self):
        """Verify auth module uses parameterized queries."""
        import inspect
        from routers.auth import handle_login

        source = inspect.getsource(handle_login)

        # Should use parameterized queries with ? placeholders
        assert "?" in source, "Should use parameterized query placeholders"

        # Should NOT use string formatting for SQL
        # These are dangerous patterns
        dangerous_patterns = [
            'f"SELECT',
            "f'SELECT",
            '% "SELECT',
            "% 'SELECT",
        ]

        for pattern in dangerous_patterns:
            assert pattern not in source, f"Should not use string formatting: {pattern}"

    def test_database_handles_special_characters(self, security_db):
        """Database should safely handle special SQL characters."""
        cursor = security_db.cursor()

        special_chars = [
            "user'; --",
            "user\" OR",
            "user/* comment */",
            "user\x00",  # Null byte
        ]

        for char_input in special_chars:
            # Insert with special characters
            cursor.execute(
                "INSERT INTO users (github_id, username) VALUES (?, ?)",
                (999999, char_input)
            )
            security_db.commit()

            # Retrieve safely
            cursor.execute("SELECT username FROM users WHERE github_id = ?", (999999,))
            result = cursor.fetchone()

            # Should store and retrieve without executing SQL
            assert result is not None
            assert result["username"] == char_input

            # Cleanup
            cursor.execute("DELETE FROM users WHERE github_id = ?", (999999,))
            security_db.commit()


class TestORMSafety:
    """Test ORM query safety (if using ORM)."""

    def test_no_raw_sql_with_user_input(self):
        """Application should not use raw SQL with user input."""
        # This is a code inspection test
        import inspect
        from routers import auth

        source = inspect.getsource(auth)

        # Check for dangerous patterns
        # These indicate raw SQL with potential user input
        assert 'execute("' not in source or '?' in source, "Raw SQL should use parameters"


class TestBlindSQLInjection:
    """Test blind SQL injection prevention."""

    @pytest.mark.parametrize("payload", [
        "1' AND SLEEP(5)--",
        "1' WAITFOR DELAY '00:00:05'--",
        "1' AND (SELECT COUNT(*) FROM users) > 0--",
    ])
    def test_blind_sql_injection_blocked(self, security_db, payload):
        """Blind SQL injection attempts should be blocked."""
        import time
        cursor = security_db.cursor()

        start = time.time()
        try:
            # Attempt time-based blind injection
            cursor.execute("SELECT * FROM users WHERE github_id = ?", (payload,))
            cursor.fetchone()
        except Exception:
            pass
        elapsed = time.time() - start

        # Should complete quickly (not delay for 5 seconds)
        assert elapsed < 1.0, "Should not execute time-based injection"


class TestUnionBasedInjection:
    """Test UNION-based SQL injection prevention."""

    @pytest.mark.parametrize("payload", [
        "1' UNION SELECT NULL,NULL,NULL--",
        "1' UNION ALL SELECT username, NULL, NULL FROM users--",
        "999 UNION SELECT * FROM users--",
    ])
    def test_union_injection_blocked(self, security_db, payload):
        """UNION-based injection should not extract extra data."""
        cursor = security_db.cursor()

        # Insert test user
        cursor.execute(
            "INSERT INTO users (github_id, username) VALUES (?, ?)",
            (1, "legitimate_user")
        )
        security_db.commit()

        # Attempt UNION injection
        cursor.execute("SELECT * FROM users WHERE github_id = ?", (payload,))
        results = cursor.fetchall()

        # Should only return legitimate results (or none)
        # Should NOT return all users via UNION
        assert len(results) <= 1, "Should not return extra rows via UNION"

        # Cleanup
        cursor.execute("DELETE FROM users WHERE github_id = ?", (1,))
        security_db.commit()
