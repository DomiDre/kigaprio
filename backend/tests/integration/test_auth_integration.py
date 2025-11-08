"""
Integration tests for authentication routes.

Tests the full authentication flow with real Redis and PocketBase.
"""

import re
import pytest
from fastapi.testclient import TestClient

@pytest.mark.integration
class TestAuthenticationIntegration:
    """Integration tests for auth endpoints."""

    def test_user_registration_and_login_flow(
        self, test_app: TestClient, pocketbase_url: str
    ):
        """
        Test complete user registration and login flow.

        This tests:
        - User registration
        - Login with credentials
        - Session creation in Redis
        - Cookie management
        """
        print("!!!", pocketbase_url)
        # Register a new user
        registration_data = {
            "username": "testuser",
            "password": "SecurePassword123!",
            "name": "Test User",
            "magic_word": "test"
        }

        # registration of user: magic word + register
        verify_magic_word_response = test_app.post(
            "/api/v1/auth/verify-magic-word",
            json={
                "magic_word": registration_data["magic_word"]
            },
        )
        assert verify_magic_word_response.status_code == 200, "Failed to assert magic word"
        magic_word_body = verify_magic_word_response.json()
        assert "token" in magic_word_body
        registration_data["reg_token"] = magic_word_body["token"]

        register_response = test_app.post(
            "/api/v1/auth/register",
            json={
                "identity": registration_data["username"],
                "password": registration_data["password"],
                "passwordConfirm": registration_data["password"],
                "name": registration_data["name"],
                "registration_token": registration_data["reg_token"]
            },
        )
        assert register_response.status_code == 200, "Registrierung fehlgeschlagen"

        # Login via API
        login_response = test_app.post(
            "/api/v1/auth/login",
            json={
                "identity": registration_data["username"],
                "password": registration_data["password"],
            },
        )

        assert login_response.status_code == 200

        # Extract cookies from Set-Cookie headers
        # TestClient doesn't automatically handle httpOnly cookies, so we need to extract them manually
        set_cookie_headers = login_response.headers.get_list("set-cookie")

        cookies = {}
        for cookie_header in set_cookie_headers:
            # Parse cookie name and value from "name=value; attributes..."
            cookie_match = re.match(r'([^=]+)=([^;]+)', cookie_header)
            if cookie_match:
                cookies[cookie_match.group(1)] = cookie_match.group(2)

        assert "auth_token" in cookies, "auth_token cookie not found"
        assert "dek" in cookies, "dek cookie not found"

        # Verify session endpoint - manually pass cookies
        test_app.cookies = cookies
        verify_response = test_app.get(
            "/api/v1/auth/verify",
        )
        assert verify_response.status_code == 200, f"Verification failed: {verify_response.text}"
        data = verify_response.json()
        assert data["username"] == registration_data["username"]
        assert data["authenticated"] is True

    def test_login_with_invalid_credentials(self, test_app: TestClient):
        """Test login with invalid credentials fails appropriately."""
        login_response = test_app.post(
            "/api/v1/auth/login",
            json={
                "identity": "nonexistent",
                "password": "WrongPassword123!",
            },
        )

        assert login_response.status_code in [400, 401]

        # Check Set-Cookie headers to ensure no auth_token was set
        set_cookie_headers = login_response.headers.get_list("set-cookie")
        cookies = {}
        for cookie_header in set_cookie_headers:
            cookie_match = re.match(r'([^=]+)=([^;]+)', cookie_header)
            if cookie_match:
                cookies[cookie_match.group(1)] = cookie_match.group(2)

        assert "auth_token" not in cookies

    def test_logout_clears_session(self, test_app: TestClient):
        """Test that logout properly clears session and cookies."""
        # Register a new user
        registration_data = {
            "username": "logoutuser",
            "password": "Password123!",
            "name": "Logout User",
            "magic_word": "test"
        }

        # Verify magic word and get registration token
        verify_magic_word_response = test_app.post(
            "/api/v1/auth/verify-magic-word",
            json={
                "magic_word": registration_data["magic_word"]
            },
        )
        assert verify_magic_word_response.status_code == 200
        magic_word_body = verify_magic_word_response.json()
        registration_data["reg_token"] = magic_word_body["token"]

        # Register user
        register_response = test_app.post(
            "/api/v1/auth/register",
            json={
                "identity": registration_data["username"],
                "password": registration_data["password"],
                "passwordConfirm": registration_data["password"],
                "name": registration_data["name"],
                "registration_token": registration_data["reg_token"]
            },
        )
        assert register_response.status_code == 200

        # Login
        login_response = test_app.post(
            "/api/v1/auth/login",
            json={
                "identity": registration_data["username"],
                "password": registration_data["password"],
            },
        )

        assert login_response.status_code == 200

        # Extract cookies from login
        set_cookie_headers = login_response.headers.get_list("set-cookie")
        cookies = {}
        for cookie_header in set_cookie_headers:
            cookie_match = re.match(r'([^=]+)=([^;]+)', cookie_header)
            if cookie_match:
                cookies[cookie_match.group(1)] = cookie_match.group(2)

        assert "auth_token" in cookies
        test_app.cookies = cookies

        # Logout - pass the cookies
        logout_response = test_app.post("/api/v1/auth/logout")
        assert logout_response.status_code == 200

        # Verify session is invalid - try to use the old cookies
        verify_response = test_app.get("/api/v1/auth/verify")
        assert verify_response.status_code in [401, 403]
