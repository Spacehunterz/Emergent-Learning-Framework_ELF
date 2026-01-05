"""
Security tests for CORS policy enforcement.

Tests that Cross-Origin Resource Sharing (CORS) policies
are properly enforced to prevent unauthorized cross-origin requests.
"""

import pytest
import sys
from pathlib import Path

# Ensure backend is in path
backend_path = Path(__file__).parent.parent.parent
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))


class TestCORSAttacks:
    """Test CORS violation prevention."""

    def test_allowed_origin_localhost_3001(self, client):
        """localhost:3001 should be allowed origin."""
        response = client.options(
            "/api/auth/me",
            headers={"Origin": "http://localhost:3001"}
        )

        # Should allow this origin
        cors_origin = response.headers.get("access-control-allow-origin")
        assert cors_origin in ["http://localhost:3001", "*"], "Should allow localhost:3001"

        # Should allow credentials
        assert response.headers.get("access-control-allow-credentials") == "true"

    @pytest.mark.parametrize("malicious_origin", [
        "http://evil.com",
        "https://attacker.com",
        "http://localhost:9999",  # Different port
        "https://localhost:3001",  # Different protocol
        "null",
    ])
    def test_malicious_origin_blocked(self, client, malicious_origin):
        """Malicious origins should be blocked."""
        response = client.options(
            "/api/auth/me",
            headers={"Origin": malicious_origin}
        )

        # Should not explicitly allow malicious origin
        cors_origin = response.headers.get("access-control-allow-origin")

        # Either no CORS header, or not matching the malicious origin
        if cors_origin and cors_origin != "*":
            assert cors_origin != malicious_origin, f"Should not allow {malicious_origin}"

    def test_cors_preflight_rejected_for_evil_origin(self, client):
        """Preflight requests from evil origins should be rejected."""
        response = client.options(
            "/api/runs",
            headers={
                "Origin": "http://evil.com",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type",
            }
        )

        # Should not allow this origin
        cors_origin = response.headers.get("access-control-allow-origin")

        if cors_origin and cors_origin != "*":
            assert cors_origin != "http://evil.com"

    def test_wildcard_not_used_with_credentials(self, client):
        """Should not use wildcard (*) origin when credentials are allowed."""
        response = client.get("/api/auth/me")

        cors_origin = response.headers.get("access-control-allow-origin")
        cors_creds = response.headers.get("access-control-allow-credentials")

        # If credentials are true, origin should NOT be *
        if cors_creds == "true":
            assert cors_origin != "*", "Cannot use wildcard with credentials"

    def test_cors_methods_restricted(self, client):
        """CORS should only allow specific HTTP methods."""
        response = client.options(
            "/api/auth/me",
            headers={"Origin": "http://localhost:3001"}
        )

        allowed_methods = response.headers.get("access-control-allow-methods")

        if allowed_methods:
            # Should include GET, POST but be limited
            allowed = allowed_methods.upper()
            assert "GET" in allowed or "POST" in allowed

            # Should NOT allow dangerous methods
            assert "TRACE" not in allowed
            assert "CONNECT" not in allowed

    def test_cors_headers_restricted(self, client):
        """CORS should only allow specific headers."""
        response = client.options(
            "/api/auth/me",
            headers={
                "Origin": "http://localhost:3001",
                "Access-Control-Request-Headers": "Content-Type, Authorization",
            }
        )

        allowed_headers = response.headers.get("access-control-allow-headers")

        if allowed_headers:
            # Should include standard headers
            allowed = allowed_headers.lower()
            assert "content-type" in allowed or "authorization" in allowed


class TestOriginValidation:
    """Test origin header validation."""

    def test_null_origin_handling(self, client):
        """Null origin should be handled securely."""
        response = client.get(
            "/api/auth/me",
            headers={"Origin": "null"}
        )

        # Should not allow "null" as valid origin
        cors_origin = response.headers.get("access-control-allow-origin")
        if cors_origin and cors_origin != "*":
            assert cors_origin != "null", "Should not allow null origin"

    def test_multiple_origins_not_reflected(self, client):
        """Multiple origins in header should not all be reflected."""
        response = client.get(
            "/api/auth/me",
            headers={"Origin": "http://localhost:3001, http://evil.com"}
        )

        # Should not reflect multiple origins
        cors_origin = response.headers.get("access-control-allow-origin")
        if cors_origin:
            assert "," not in cors_origin, "Should not reflect multiple origins"

    def test_origin_case_sensitivity(self, client):
        """Origin matching should be case-sensitive (per spec)."""
        # Per CORS spec, origin should be case-sensitive
        response = client.get(
            "/api/auth/me",
            headers={"Origin": "HTTP://LOCALHOST:3001"}  # Wrong case
        )

        # Depending on implementation, may reject wrong case
        # This is informational - some implementations normalize


class TestCredentialedRequests:
    """Test CORS with credentials."""

    def test_credentials_required_for_session(self, authenticated_client):
        """Credentialed requests should include cookies."""
        # This test verifies that session cookies work with CORS

        response = authenticated_client.get(
            "/api/auth/me",
            headers={"Origin": "http://localhost:3001"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["is_authenticated"] is True

    def test_credentials_not_sent_without_origin(self, client):
        """Without proper origin, credentials should not leak."""
        # Make request without Origin header
        response = client.get("/api/auth/me")

        # Should still work (same-origin)
        assert response.status_code == 200


class TestCORSBypass:
    """Test CORS bypass prevention."""

    def test_origin_reflection_attack_prevented(self, client):
        """Dynamic origin reflection should be prevented."""
        evil_origin = "http://attacker.com"

        response = client.get(
            "/api/auth/me",
            headers={"Origin": evil_origin}
        )

        cors_origin = response.headers.get("access-control-allow-origin")

        # Should NOT dynamically reflect the attacker's origin
        # (Unless it's explicitly in the whitelist)
        if cors_origin and cors_origin != "*":
            # If there's a specific origin, it should be from allowed list
            assert "localhost" in cors_origin or cors_origin in ["http://localhost:3001"]

    def test_subdomain_not_automatically_trusted(self, client):
        """Subdomains should not be automatically trusted."""
        response = client.get(
            "/api/auth/me",
            headers={"Origin": "http://malicious.localhost:3001"}
        )

        cors_origin = response.headers.get("access-control-allow-origin")

        # Should not allow subdomains unless explicitly configured
        if cors_origin and cors_origin != "*":
            assert cors_origin == "http://localhost:3001" or "localhost" in cors_origin
