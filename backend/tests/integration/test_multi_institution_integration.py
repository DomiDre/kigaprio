"""
Integration tests for multi-institution functionality.

These tests verify the end-to-end flow of multi-institution features
using real PocketBase and Redis containers.
"""

import pytest
import httpx


@pytest.mark.integration
class TestMultiInstitutionSetup:
    """Test multi-institution setup in PocketBase."""

    def test_can_create_institutions(self, pocketbase_admin_client):
        """Test creating institutions via PocketBase API."""
        # Create first institution
        response = pocketbase_admin_client.post(
            "/api/collections/institutions/records",
            json={
                "name": "Test University A",
                "short_code": "TEST_A",
                "registration_magic_word": "MagicA123",
                "active": True,
            },
        )
        assert response.status_code == 200
        inst_a = response.json()
        assert inst_a["short_code"] == "TEST_A"

        # Create second institution
        response = pocketbase_admin_client.post(
            "/api/collections/institutions/records",
            json={
                "name": "Test University B",
                "short_code": "TEST_B",
                "registration_magic_word": "MagicB456",
                "active": True,
            },
        )
        assert response.status_code == 200
        inst_b = response.json()
        assert inst_b["short_code"] == "TEST_B"

        # Verify institutions are different
        assert inst_a["id"] != inst_b["id"]

    def test_can_query_institutions_by_short_code(self, pocketbase_admin_client):
        """Test querying institutions by short code."""
        # Create institution
        pocketbase_admin_client.post(
            "/api/collections/institutions/records",
            json={
                "name": "Query Test University",
                "short_code": "QUERY_TEST",
                "registration_magic_word": "QueryMagic",
                "active": True,
            },
        )

        # Query by short code
        response = pocketbase_admin_client.get(
            "/api/collections/institutions/records",
            params={"filter": 'short_code="QUERY_TEST"'},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["short_code"] == "QUERY_TEST"


@pytest.mark.integration
class TestPublicInstitutionEndpoints:
    """Test public institution API endpoints with real infrastructure."""

    def test_list_institutions_endpoint(self, test_app, pocketbase_admin_client):
        """Test listing institutions through the API."""
        # Create test institutions
        pocketbase_admin_client.post(
            "/api/collections/institutions/records",
            json={
                "name": "Public Test A",
                "short_code": "PUB_A",
                "registration_magic_word": "Secret123",
                "active": True,
            },
        )
        pocketbase_admin_client.post(
            "/api/collections/institutions/records",
            json={
                "name": "Public Test B",
                "short_code": "PUB_B",
                "registration_magic_word": "Secret456",
                "active": True,
            },
        )

        # Call API endpoint
        response = test_app.get("/api/v1/institutions")
        assert response.status_code == 200

        data = response.json()
        assert len(data) >= 2

        # Verify sensitive fields are not exposed
        for inst in data:
            assert "registration_magic_word" not in inst
            assert "admin_public_key" not in inst
            assert "settings" not in inst

    def test_get_institution_by_short_code_endpoint(
        self, test_app, pocketbase_admin_client
    ):
        """Test getting institution by short code through the API."""
        # Create test institution
        pocketbase_admin_client.post(
            "/api/collections/institutions/records",
            json={
                "name": "Short Code Test",
                "short_code": "SC_TEST",
                "registration_magic_word": "SCSecret",
                "active": True,
            },
        )

        # Call API endpoint
        response = test_app.get("/api/v1/institutions/SC_TEST")
        assert response.status_code == 200

        data = response.json()
        assert data["short_code"] == "SC_TEST"
        assert data["name"] == "Short Code Test"

        # Verify sensitive fields are not exposed
        assert "registration_magic_word" not in data


@pytest.mark.integration
class TestMagicWordVerification:
    """Test magic word verification with real infrastructure."""

    def test_verify_correct_magic_word(
        self, test_app, pocketbase_admin_client, clean_redis
    ):
        """Test verifying correct magic word."""
        # Create institution
        pocketbase_admin_client.post(
            "/api/collections/institutions/records",
            json={
                "name": "Magic Test University",
                "short_code": "MAGIC_TEST",
                "registration_magic_word": "CorrectMagic123",
                "active": True,
            },
        )

        # Verify magic word
        response = test_app.post(
            "/api/v1/auth/verify-magic-word",
            json={
                "magic_word": "CorrectMagic123",
                "institution_short_code": "MAGIC_TEST",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "token" in data

        # Verify token is stored in Redis with institution_id
        import json
        token = data["token"]
        token_data_str = clean_redis.get(f"reg_token:{token}")
        assert token_data_str is not None
        token_data = json.loads(token_data_str)
        assert "institution_id" in token_data

    def test_verify_wrong_magic_word(self, test_app, pocketbase_admin_client):
        """Test verifying wrong magic word."""
        # Create institution
        pocketbase_admin_client.post(
            "/api/collections/institutions/records",
            json={
                "name": "Wrong Magic Test",
                "short_code": "WRONG_TEST",
                "registration_magic_word": "CorrectMagic",
                "active": True,
            },
        )

        # Try wrong magic word
        response = test_app.post(
            "/api/v1/auth/verify-magic-word",
            json={
                "magic_word": "WrongMagic",
                "institution_short_code": "WRONG_TEST",
            },
        )

        assert response.status_code == 403

    def test_verify_magic_word_inactive_institution(
        self, test_app, pocketbase_admin_client
    ):
        """Test verifying magic word for inactive institution."""
        # Create inactive institution
        pocketbase_admin_client.post(
            "/api/collections/institutions/records",
            json={
                "name": "Inactive Test",
                "short_code": "INACTIVE_TEST",
                "registration_magic_word": "InactiveMagic",
                "active": False,
            },
        )

        # Try to verify magic word
        response = test_app.post(
            "/api/v1/auth/verify-magic-word",
            json={
                "magic_word": "InactiveMagic",
                "institution_short_code": "INACTIVE_TEST",
            },
        )

        assert response.status_code == 403


@pytest.mark.integration
class TestUserRegistrationWithInstitutions:
    """Test user registration flow with real infrastructure."""

    def test_register_user_with_qr_and_institution(
        self, test_app, pocketbase_admin_client, clean_redis
    ):
        """Test complete QR registration flow with institution."""
        # Create institution
        create_response = pocketbase_admin_client.post(
            "/api/collections/institutions/records",
            json={
                "name": "Registration Test University",
                "short_code": "REG_TEST",
                "registration_magic_word": "RegMagic123",
                "active": True,
            },
        )
        assert create_response.status_code == 200
        institution = create_response.json()

        # Register user via API
        response = test_app.post(
            "/api/v1/auth/register-qr",
            json={
                "identity": "testuser@regtest.edu",
                "password": "TestPass123!",
                "passwordConfirm": "TestPass123!",
                "name": "Test User",
                "magic_word": "RegMagic123",
                "institution_short_code": "REG_TEST",
                "keep_logged_in": False,
            },
        )

        assert response.status_code == 200
        user_data = response.json()

        # Verify user was created with correct institution
        assert "user" in user_data
        user = user_data["user"]
        assert user["institution_id"] == institution["id"]

    def test_users_from_different_institutions_isolated(
        self, test_app, pocketbase_admin_client
    ):
        """Test that users from different institutions are isolated."""
        # Create two institutions
        inst_a_response = pocketbase_admin_client.post(
            "/api/collections/institutions/records",
            json={
                "name": "Institution A",
                "short_code": "INST_A",
                "registration_magic_word": "MagicA",
                "active": True,
            },
        )
        inst_a = inst_a_response.json()

        inst_b_response = pocketbase_admin_client.post(
            "/api/collections/institutions/records",
            json={
                "name": "Institution B",
                "short_code": "INST_B",
                "registration_magic_word": "MagicB",
                "active": True,
            },
        )
        inst_b = inst_b_response.json()

        # Register user in Institution A
        test_app.post(
            "/api/v1/auth/register-qr",
            json={
                "identity": "userA@insta.edu",
                "password": "PassA123!",
                "passwordConfirm": "PassA123!",
                "name": "User A",
                "magic_word": "MagicA",
                "institution_short_code": "INST_A",
                "keep_logged_in": False,
            },
        )

        # Register user in Institution B
        test_app.post(
            "/api/v1/auth/register-qr",
            json={
                "identity": "userB@instb.edu",
                "password": "PassB123!",
                "passwordConfirm": "PassB123!",
                "name": "User B",
                "magic_word": "MagicB",
                "institution_short_code": "INST_B",
                "keep_logged_in": False,
            },
        )

        # Verify users exist in different institutions
        users_a = pocketbase_admin_client.get(
            "/api/collections/users/records",
            params={"filter": f'institution_id="{inst_a["id"]}"'},
        ).json()

        users_b = pocketbase_admin_client.get(
            "/api/collections/users/records",
            params={"filter": f'institution_id="{inst_b["id"]}"'},
        ).json()

        assert len(users_a["items"]) >= 1
        assert len(users_b["items"]) >= 1

        # Verify they're in different institutions
        assert users_a["items"][0]["institution_id"] == inst_a["id"]
        assert users_b["items"][0]["institution_id"] == inst_b["id"]
        assert users_a["items"][0]["institution_id"] != users_b["items"][0]["institution_id"]
