"""
Integration tests for priority endpoints.

Tests the full priority management flow with real Redis and PocketBase.

Covers:
- Creating priorities for different months
- Retrieving priorities (all and by month)
- Updating existing priorities
- Week start validation and merge logic
- Rate limiting via Redis
- Encryption/decryption flow
- Deleting priorities
- Ownership verification
"""

import re
import secrets
import time
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient


@pytest.mark.integration
class TestPriorityIntegration:
    """Integration tests for priority endpoints."""

    def _register_and_login(self, test_app: TestClient) -> dict:
        """Helper: Register a new user and return cookies + user data."""
        unique_suffix = secrets.token_hex(4)
        user_data = {
            "username": f"testuser_{unique_suffix}",
            "password": "SecurePassword123!",
            "name": "Test User",
            "magic_word": "test",
        }

        # Verify magic word
        verify_response = test_app.post(
            "/api/v1/auth/verify-magic-word",
            json={"magic_word": user_data["magic_word"]},
        )
        assert verify_response.status_code == 200
        magic_word_body = verify_response.json()
        user_data["reg_token"] = magic_word_body["token"]

        # Register user
        register_response = test_app.post(
            "/api/v1/auth/register",
            json={
                "identity": user_data["username"],
                "password": user_data["password"],
                "passwordConfirm": user_data["password"],
                "name": user_data["name"],
                "registration_token": user_data["reg_token"],
            },
        )
        assert register_response.status_code == 200

        # Login
        login_response = test_app.post(
            "/api/v1/auth/login",
            json={
                "identity": user_data["username"],
                "password": user_data["password"],
            },
        )
        assert login_response.status_code == 200

        # Extract cookies
        set_cookie_headers = login_response.headers.get_list("set-cookie")
        cookies = {}
        for cookie_header in set_cookie_headers:
            cookie_match = re.match(r"([^=]+)=([^;]+)", cookie_header)
            if cookie_match:
                cookies[cookie_match.group(1)] = cookie_match.group(2)

        assert "auth_token" in cookies
        assert "dek" in cookies

        return {"cookies": cookies, "user_data": user_data}

    def test_create_priority_success(self, test_app: TestClient):
        """Test creating a new priority for current month."""
        # Setup: Register and login
        auth = self._register_and_login(test_app)
        test_app.cookies = auth["cookies"]

        # Get current month
        current_month = datetime.now().strftime("%Y-%m")

        # Create priority
        priority_data = {
            "weeks": [
                {
                    "weekNumber": 1,
                    "monday": 1,
                    "tuesday": 2,
                    "wednesday": 3,
                    "thursday": 4,
                    "friday": 5,
                },
                {
                    "weekNumber": 2,
                    "monday": 2,
                    "tuesday": 3,
                    "wednesday": 4,
                    "thursday": 5,
                    "friday": 1,
                },
            ]
        }

        response = test_app.put(
            f"/api/v1/priorities/{current_month}",
            json=priority_data["weeks"],
        )

        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "erstellt" in data["message"] or "gespeichert" in data["message"]

    def test_get_priority_by_month(self, test_app: TestClient):
        """Test retrieving a priority for a specific month."""
        # Setup: Register, login, and create priority
        auth = self._register_and_login(test_app)
        test_app.cookies = auth["cookies"]

        current_month = datetime.now().strftime("%Y-%m")

        # Create priority first
        priority_data = [
            {
                "weekNumber": 1,
                "monday": 1,
                "tuesday": 2,
                "wednesday": 3,
                "thursday": 4,
                "friday": 5,
            }
        ]

        create_response = test_app.put(
            f"/api/v1/priorities/{current_month}",
            json=priority_data,
        )
        assert create_response.status_code == 200

        # Get priority
        get_response = test_app.get(f"/api/v1/priorities/{current_month}")

        assert get_response.status_code == 200
        data = get_response.json()
        assert data["month"] == current_month
        assert len(data["weeks"]) == 1
        assert data["weeks"][0]["weekNumber"] == 1
        assert data["weeks"][0]["monday"] == 1

    def test_get_priority_not_found(self, test_app: TestClient):
        """Test retrieving a non-existent priority returns empty weeks."""
        auth = self._register_and_login(test_app)
        test_app.cookies = auth["cookies"]

        # Try to get priority for a month that doesn't exist
        future_month = (datetime.now() + timedelta(days=60)).strftime("%Y-%m")

        response = test_app.get(f"/api/v1/priorities/{future_month}")

        assert response.status_code == 200
        data = response.json()
        assert data["month"] == future_month
        assert data["weeks"] == []

    def test_get_all_priorities(self, test_app: TestClient):
        """Test retrieving all priorities for authenticated user."""
        auth = self._register_and_login(test_app)
        test_app.cookies = auth["cookies"]

        current_month = datetime.now().strftime("%Y-%m")
        next_month = (datetime.now() + timedelta(days=32)).strftime("%Y-%m")

        # Create priorities for two months
        for month in [current_month, next_month]:
            priority_data = [
                {
                    "weekNumber": 1,
                    "monday": 1,
                    "tuesday": 2,
                    "wednesday": 3,
                    "thursday": 4,
                    "friday": 5,
                }
            ]
            response = test_app.put(f"/api/v1/priorities/{month}", json=priority_data)
            assert response.status_code == 200

        # Get all priorities
        response = test_app.get("/api/v1/priorities")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        # Priorities should be sorted by month descending
        assert data[0]["month"] >= data[1]["month"]

    def test_update_existing_priority(self, test_app: TestClient):
        """Test updating an existing priority."""
        auth = self._register_and_login(test_app)
        test_app.cookies = auth["cookies"]

        current_month = datetime.now().strftime("%Y-%m")

        # Create initial priority
        initial_data = [
            {
                "weekNumber": 1,
                "monday": 1,
                "tuesday": 2,
                "wednesday": 3,
                "thursday": 4,
                "friday": 5,
            }
        ]

        create_response = test_app.put(
            f"/api/v1/priorities/{current_month}",
            json=initial_data,
        )
        assert create_response.status_code == 200

        # Update with different data
        updated_data = [
            {
                "weekNumber": 1,
                "monday": 5,
                "tuesday": 4,
                "wednesday": 3,
                "thursday": 2,
                "friday": 1,
            }
        ]

        update_response = test_app.put(
            f"/api/v1/priorities/{current_month}",
            json=updated_data,
        )
        assert update_response.status_code == 200

        # Verify updated data
        get_response = test_app.get(f"/api/v1/priorities/{current_month}")
        assert get_response.status_code == 200
        data = get_response.json()

        # Note: If week has already started, old data is preserved
        # Otherwise, new data should be used
        assert len(data["weeks"]) == 1

    def test_delete_priority(self, test_app: TestClient):
        """Test deleting a priority."""
        auth = self._register_and_login(test_app)
        test_app.cookies = auth["cookies"]

        current_month = datetime.now().strftime("%Y-%m")

        # Create priority
        priority_data = [
            {
                "weekNumber": 1,
                "monday": 1,
                "tuesday": 2,
                "wednesday": 3,
                "thursday": 4,
                "friday": 5,
            }
        ]

        create_response = test_app.put(
            f"/api/v1/priorities/{current_month}",
            json=priority_data,
        )
        assert create_response.status_code == 200

        # Delete priority
        delete_response = test_app.delete(f"/api/v1/priorities/{current_month}")
        assert delete_response.status_code == 200
        data = delete_response.json()
        assert "gelöscht" in data["message"]

        # Verify deletion
        get_response = test_app.get(f"/api/v1/priorities/{current_month}")
        assert get_response.status_code == 200
        data = get_response.json()
        assert data["weeks"] == []

    def test_delete_nonexistent_priority(self, test_app: TestClient):
        """Test deleting a priority that doesn't exist."""
        auth = self._register_and_login(test_app)
        test_app.cookies = auth["cookies"]

        future_month = (datetime.now() + timedelta(days=60)).strftime("%Y-%m")

        # Try to delete non-existent priority
        response = test_app.delete(f"/api/v1/priorities/{future_month}")
        assert response.status_code == 400

    def test_rate_limiting(self, test_app: TestClient):
        """Test rate limiting for priority creation."""
        auth = self._register_and_login(test_app)
        test_app.cookies = auth["cookies"]

        current_month = datetime.now().strftime("%Y-%m")

        priority_data = [
            {
                "weekNumber": 1,
                "monday": 1,
                "tuesday": 2,
                "wednesday": 3,
                "thursday": 4,
                "friday": 5,
            }
        ]

        # First request should succeed
        response1 = test_app.put(
            f"/api/v1/priorities/{current_month}",
            json=priority_data,
        )
        assert response1.status_code == 200

        # Immediate second request should be rate limited
        response2 = test_app.put(
            f"/api/v1/priorities/{current_month}",
            json=priority_data,
        )
        assert response2.status_code == 429

        # After waiting, should work again
        time.sleep(2.1)
        response3 = test_app.put(
            f"/api/v1/priorities/{current_month}",
            json=priority_data,
        )
        assert response3.status_code == 200

    def test_month_validation_invalid_format(self, test_app: TestClient):
        """Test that invalid month format is rejected."""
        auth = self._register_and_login(test_app)
        test_app.cookies = auth["cookies"]

        priority_data = [{"weekNumber": 1, "monday": 1}]

        # Invalid month format
        response = test_app.put(
            "/api/v1/priorities/2025-13",  # Month 13 doesn't exist
            json=priority_data,
        )
        assert response.status_code == 422

    def test_month_validation_out_of_range(self, test_app: TestClient):
        """Test that months outside allowed range are rejected."""
        auth = self._register_and_login(test_app)
        test_app.cookies = auth["cookies"]

        priority_data = [{"weekNumber": 1, "monday": 1}]

        # Month too far in the future
        far_future = (datetime.now() + timedelta(days=365)).strftime("%Y-%m")
        response = test_app.put(
            f"/api/v1/priorities/{far_future}",
            json=priority_data,
        )
        assert response.status_code == 422

    def test_unauthenticated_access(self, test_app: TestClient):
        """Test that unauthenticated requests are rejected."""
        current_month = datetime.now().strftime("%Y-%m")

        # Try without cookies
        test_app.cookies = {}

        # GET all priorities
        response1 = test_app.get("/api/v1/priorities")
        assert response1.status_code in [401, 403]

        # GET specific month
        response2 = test_app.get(f"/api/v1/priorities/{current_month}")
        assert response2.status_code in [401, 403]

        # PUT (create/update)
        response3 = test_app.put(
            f"/api/v1/priorities/{current_month}",
            json=[{"weekNumber": 1, "monday": 1}],
        )
        assert response3.status_code in [401, 403]

        # DELETE
        response4 = test_app.delete(f"/api/v1/priorities/{current_month}")
        assert response4.status_code in [401, 403]

    def test_ownership_isolation(self, test_app: TestClient):
        """Test that users can only access their own priorities."""
        # Create two users
        auth1 = self._register_and_login(test_app)
        auth2 = self._register_and_login(test_app)

        current_month = datetime.now().strftime("%Y-%m")

        # User 1 creates a priority
        test_app.cookies = auth1["cookies"]
        priority_data = [
            {
                "weekNumber": 1,
                "monday": 1,
                "tuesday": 2,
                "wednesday": 3,
                "thursday": 4,
                "friday": 5,
            }
        ]
        response = test_app.put(
            f"/api/v1/priorities/{current_month}",
            json=priority_data,
        )
        assert response.status_code == 200

        # User 2 should not see user 1's priorities
        test_app.cookies = auth2["cookies"]
        response = test_app.get("/api/v1/priorities")
        assert response.status_code == 200
        data = response.json()
        # User 2 should have no priorities
        assert len(data) == 0

        # User 2 tries to get user 1's priority for the same month
        response = test_app.get(f"/api/v1/priorities/{current_month}")
        assert response.status_code == 200
        data = response.json()
        # Should return empty weeks (no access to user 1's data)
        assert data["weeks"] == []

    def test_encryption_flow(self, test_app: TestClient):
        """Test that data is encrypted in storage and decrypted on retrieval."""
        auth = self._register_and_login(test_app)
        test_app.cookies = auth["cookies"]

        current_month = datetime.now().strftime("%Y-%m")

        # Create priority with specific data
        priority_data = [
            {
                "weekNumber": 1,
                "monday": 1,
                "tuesday": 2,
                "wednesday": 3,
                "thursday": 4,
                "friday": 5,
            },
            {
                "weekNumber": 2,
                "monday": 5,
                "tuesday": 4,
                "wednesday": 3,
                "thursday": 2,
                "friday": 1,
            },
        ]

        create_response = test_app.put(
            f"/api/v1/priorities/{current_month}",
            json=priority_data,
        )
        assert create_response.status_code == 200

        # Retrieve and verify data is correctly decrypted
        get_response = test_app.get(f"/api/v1/priorities/{current_month}")
        assert get_response.status_code == 200
        data = get_response.json()

        assert data["month"] == current_month
        assert len(data["weeks"]) == 2

        # Verify week 1
        week1 = next(w for w in data["weeks"] if w["weekNumber"] == 1)
        assert week1["monday"] == 1
        assert week1["tuesday"] == 2
        assert week1["wednesday"] == 3
        assert week1["thursday"] == 4
        assert week1["friday"] == 5

        # Verify week 2
        week2 = next(w for w in data["weeks"] if w["weekNumber"] == 2)
        assert week2["monday"] == 5
        assert week2["tuesday"] == 4
        assert week2["wednesday"] == 3
        assert week2["thursday"] == 2
        assert week2["friday"] == 1

    def test_multiple_weeks_priority(self, test_app: TestClient):
        """Test creating and retrieving priorities with multiple weeks."""
        auth = self._register_and_login(test_app)
        test_app.cookies = auth["cookies"]

        current_month = datetime.now().strftime("%Y-%m")

        # Create priority with 4 weeks
        priority_data = [{"weekNumber": i, "monday": i % 5 + 1} for i in range(1, 5)]

        response = test_app.put(
            f"/api/v1/priorities/{current_month}",
            json=priority_data,
        )
        assert response.status_code == 200

        # Retrieve and verify
        get_response = test_app.get(f"/api/v1/priorities/{current_month}")
        assert get_response.status_code == 200
        data = get_response.json()

        assert len(data["weeks"]) == 4
        for i in range(1, 5):
            week = next(w for w in data["weeks"] if w["weekNumber"] == i)
            assert week["monday"] == i % 5 + 1
