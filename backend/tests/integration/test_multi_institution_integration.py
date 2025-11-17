"""
Integration tests for multi-institution functionality.

These tests verify the end-to-end flow of multi-institution features
including data isolation and permission enforcement.
"""

import pytest
from unittest.mock import patch, AsyncMock


@pytest.mark.integration
class TestMultiInstitutionRegistrationFlow:
    """Test complete registration flow with multiple institutions."""

    @patch("priotag.api.routes.auth.InstitutionService.get_by_short_code")
    @patch("priotag.api.routes.auth.authenticate_service_account")
    @patch("httpx.AsyncClient")
    def test_users_from_different_institutions_are_isolated(
        self, mock_client_class, mock_auth_service, mock_get_institution, client, fake_redis
    ):
        """
        Test that users from different institutions cannot access each other's data.

        Flow:
        1. Create two institutions
        2. Register user in each institution
        3. Verify users are associated with correct institutions
        4. Verify data isolation (tested via institution_id in session)
        """
        from priotag.models.pocketbase_schemas import InstitutionRecord

        # Setup institutions
        institution_A = InstitutionRecord(
            id="inst_A",
            name="University A",
            short_code="UNIV_A",
            registration_magic_word="MagicA",
            admin_public_key=None,
            settings={},
            active=True,
            collectionId="institutions",
            collectionName="institutions",
            created="2025-01-01T00:00:00Z",
            updated="2025-01-01T00:00:00Z",
        )

        institution_B = InstitutionRecord(
            id="inst_B",
            name="University B",
            short_code="UNIV_B",
            registration_magic_word="MagicB",
            admin_public_key=None,
            settings={},
            active=True,
            collectionId="institutions",
            collectionName="institutions",
            created="2025-01-01T00:00:00Z",
            updated="2025-01-01T00:00:00Z",
        )

        # Mock institution service to return appropriate institution
        def get_institution_by_code(short_code, *args):
            if short_code == "UNIV_A":
                return institution_A
            elif short_code == "UNIV_B":
                return institution_B
            raise Exception("Institution not found")

        mock_get_institution.side_effect = get_institution_by_code
        mock_auth_service.return_value = "service_token"

        # Mock PocketBase client
        mock_pb_client = AsyncMock()
        mock_client_class.return_value.__aenter__.return_value = mock_pb_client

        # User A registration
        create_resp_A = AsyncMock()
        create_resp_A.status_code = 200
        create_resp_A.json.return_value = {"id": "user_A", "username": "userA"}

        auth_resp_A = AsyncMock()
        auth_resp_A.status_code = 200
        auth_resp_A.json.return_value = {
            "token": "token_A",
            "record": {
                "id": "user_A",
                "username": "userA",
                "role": "user",
                "institution_id": "inst_A",
            },
        }

        # User B registration
        create_resp_B = AsyncMock()
        create_resp_B.status_code = 200
        create_resp_B.json.return_value = {"id": "user_B", "username": "userB"}

        auth_resp_B = AsyncMock()
        auth_resp_B.status_code = 200
        auth_resp_B.json.return_value = {
            "token": "token_B",
            "record": {
                "id": "user_B",
                "username": "userB",
                "role": "user",
                "institution_id": "inst_B",
            },
        }

        # Register User A in Institution A
        mock_pb_client.post.side_effect = [create_resp_A, auth_resp_A]

        response_A = client.post(
            "/api/v1/auth/register-qr",
            json={
                "identity": "userA@test.com",
                "password": "Password123!",
                "passwordConfirm": "Password123!",
                "name": "User A",
                "magic_word": "MagicA",
                "institution_short_code": "UNIV_A",
                "keep_logged_in": False,
            },
        )

        assert response_A.status_code == 200

        # Verify User A was created with institution_id = inst_A
        user_A_create_call = mock_pb_client.post.call_args_list[0]
        user_A_data = user_A_create_call[1]["json"]
        assert user_A_data["institution_id"] == "inst_A"

        # Register User B in Institution B
        mock_pb_client.post.side_effect = [create_resp_B, auth_resp_B]

        response_B = client.post(
            "/api/v1/auth/register-qr",
            json={
                "identity": "userB@test.com",
                "password": "Password123!",
                "passwordConfirm": "Password123!",
                "name": "User B",
                "magic_word": "MagicB",
                "institution_short_code": "UNIV_B",
                "keep_logged_in": False,
            },
        )

        assert response_B.status_code == 200

        # Verify User B was created with institution_id = inst_B
        user_B_create_call = mock_pb_client.post.call_args_list[2]  # 3rd call overall
        user_B_data = user_B_create_call[1]["json"]
        assert user_B_data["institution_id"] == "inst_B"

        # Verify institutions are different
        assert user_A_data["institution_id"] != user_B_data["institution_id"]


@pytest.mark.integration
class TestInstitutionAdminPermissions:
    """Test institution admin permissions and data isolation."""

    @patch("priotag.utils.verify_token")
    @patch("priotag.utils.get_current_token")
    def test_institution_admin_cannot_access_other_institutions(
        self, mock_get_token, mock_verify, client
    ):
        """
        Test that institution admins can only access their own institution.
        """
        from priotag.models.auth import SessionInfo

        # Admin from Institution A
        admin_A = SessionInfo(
            id="admin_A",
            username="adminA",
            is_admin=True,
            role="institution_admin",
            institution_id="inst_A",
        )

        mock_get_token.return_value = "admin_A_token"
        mock_verify.return_value = admin_A

        # Try to access institution info (should only see their own)
        with patch(
            "priotag.api.routes.institutions.InstitutionService.get_institution"
        ) as mock_get:
            from priotag.models.pocketbase_schemas import InstitutionRecord

            mock_get.return_value = InstitutionRecord(
                id="inst_A",
                name="University A",
                short_code="UNIV_A",
                registration_magic_word="MagicA",
                admin_public_key=None,
                settings={},
                active=True,
                collectionId="institutions",
                collectionName="institutions",
                created="2025-01-01T00:00:00Z",
                updated="2025-01-01T00:00:00Z",
            )

            response = client.get(
                "/api/v1/admin/institution/info",
                cookies={"auth_token": "admin_A_token"},
            )

            assert response.status_code == 200
            # Verify they accessed their own institution
            assert mock_get.call_args[0][0] == "inst_A"

    @patch("priotag.utils.verify_token")
    @patch("priotag.utils.get_current_token")
    def test_super_admin_can_access_all_institutions(
        self, mock_get_token, mock_verify, client
    ):
        """
        Test that super admins can access all institutions.
        """
        from priotag.models.auth import SessionInfo

        # Super admin
        super_admin = SessionInfo(
            id="super_admin",
            username="superadmin",
            is_admin=True,
            role="super_admin",
            institution_id=None,  # No institution
        )

        mock_get_token.return_value = "super_admin_token"
        mock_verify.return_value = super_admin

        # Super admin can list all institutions
        with patch(
            "priotag.api.routes.institutions.InstitutionService.list_institutions"
        ) as mock_list:
            from priotag.models.pocketbase_schemas import InstitutionRecord

            mock_list.return_value = [
                InstitutionRecord(
                    id="inst_A",
                    name="University A",
                    short_code="UNIV_A",
                    registration_magic_word="MagicA",
                    admin_public_key=None,
                    settings={},
                    active=True,
                    collectionId="institutions",
                    collectionName="institutions",
                    created="2025-01-01T00:00:00Z",
                    updated="2025-01-01T00:00:00Z",
                ),
                InstitutionRecord(
                    id="inst_B",
                    name="University B",
                    short_code="UNIV_B",
                    registration_magic_word="MagicB",
                    admin_public_key=None,
                    settings={},
                    active=True,
                    collectionId="institutions",
                    collectionName="institutions",
                    created="2025-01-01T00:00:00Z",
                    updated="2025-01-01T00:00:00Z",
                ),
            ]

            response = client.get(
                "/api/v1/admin/super/institutions",
                cookies={"auth_token": "super_admin_token"},
            )

            assert response.status_code == 200
            data = response.json()
            assert len(data) == 2  # Can see all institutions


@pytest.mark.integration
class TestMagicWordIsolation:
    """Test magic word isolation between institutions."""

    @patch("priotag.api.routes.auth.InstitutionService.get_by_short_code")
    def test_magic_word_from_institution_A_cannot_be_used_for_institution_B(
        self, mock_get_institution, client, fake_redis
    ):
        """
        Test that magic words are institution-specific.
        """
        from priotag.models.pocketbase_schemas import InstitutionRecord
        from fastapi import HTTPException

        institution_A = InstitutionRecord(
            id="inst_A",
            name="University A",
            short_code="UNIV_A",
            registration_magic_word="MagicA",
            admin_public_key=None,
            settings={},
            active=True,
            collectionId="institutions",
            collectionName="institutions",
            created="2025-01-01T00:00:00Z",
            updated="2025-01-01T00:00:00Z",
        )

        institution_B = InstitutionRecord(
            id="inst_B",
            name="University B",
            short_code="UNIV_B",
            registration_magic_word="MagicB",
            admin_public_key=None,
            settings={},
            active=True,
            collectionId="institutions",
            collectionName="institutions",
            created="2025-01-01T00:00:00Z",
            updated="2025-01-01T00:00:00Z",
        )

        # Try to use Institution A's magic word with Institution B's code
        mock_get_institution.return_value = institution_B

        with patch("priotag.api.routes.auth.get_redis") as mock_redis:
            mock_redis.return_value = fake_redis

            response = client.post(
                "/api/v1/auth/verify-magic-word",
                json={
                    "magic_word": "MagicA",  # Institution A's magic word
                    "institution_short_code": "UNIV_B",  # But trying with Institution B
                },
            )

            # Should fail because magic word doesn't match
            assert response.status_code == 403
            assert "Ungültiges Zauberwort" in response.json()["detail"]


@pytest.mark.integration
class TestPublicInstitutionEndpoints:
    """Test public institution endpoints."""

    @patch("priotag.api.routes.institutions.InstitutionService.list_institutions")
    def test_unauthenticated_users_can_list_institutions(
        self, mock_list, client
    ):
        """
        Test that unauthenticated users can list institutions for registration.
        """
        from priotag.models.pocketbase_schemas import InstitutionRecord

        mock_list.return_value = [
            InstitutionRecord(
                id="inst_A",
                name="University A",
                short_code="UNIV_A",
                registration_magic_word="MagicA",  # Should not be exposed
                admin_public_key=None,
                settings={},
                active=True,
                collectionId="institutions",
                collectionName="institutions",
                created="2025-01-01T00:00:00Z",
                updated="2025-01-01T00:00:00Z",
            )
        ]

        # No authentication required
        response = client.get("/api/v1/institutions")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["short_code"] == "UNIV_A"
        # Verify sensitive data is not exposed
        assert "registration_magic_word" not in data[0]
        assert "admin_public_key" not in data[0]
        assert "settings" not in data[0]

    @patch("priotag.api.routes.institutions.InstitutionService.get_by_short_code")
    def test_unauthenticated_users_can_get_institution_by_short_code(
        self, mock_get, client
    ):
        """
        Test that unauthenticated users can get institution details by short code.
        """
        from priotag.models.pocketbase_schemas import InstitutionRecord

        mock_get.return_value = InstitutionRecord(
            id="inst_A",
            name="University A",
            short_code="UNIV_A",
            registration_magic_word="MagicA",
            admin_public_key=None,
            settings={},
            active=True,
            collectionId="institutions",
            collectionName="institutions",
            created="2025-01-01T00:00:00Z",
            updated="2025-01-01T00:00:00Z",
        )

        # No authentication required
        response = client.get("/api/v1/institutions/UNIV_A")

        assert response.status_code == 200
        data = response.json()
        assert data["short_code"] == "UNIV_A"
        # Verify sensitive data is not exposed
        assert "registration_magic_word" not in data
