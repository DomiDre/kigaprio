"""
Tests for multi-institution auth endpoints.
"""

import json
import pytest
from unittest.mock import AsyncMock, patch, MagicMock


class TestMagicWordVerificationWithInstitution:
    """Test magic word verification with institution selection."""

    @patch("priotag.api.routes.auth.InstitutionService.get_by_short_code")
    @patch("priotag.api.routes.auth.get_redis")
    def test_verify_magic_word_with_institution_success(
        self, mock_get_redis, mock_get_institution, sample_institution_data, fake_redis
    ):
        """Test magic word verification with valid institution."""
        from priotag.models.pocketbase_schemas import InstitutionRecord

        # Mock institution service
        mock_get_institution.return_value = InstitutionRecord(**sample_institution_data)

        # Mock Redis
        mock_get_redis.return_value = fake_redis

        # Test
        response = client.post(
            "/api/v1/auth/verify-magic-word",
            json={
                "magic_word": "TestMagic123",
                "institution_short_code": "TEST_UNIV",
            },
        )

        # Verify
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "token" in data

        # Verify token contains institution_id
        token = data["token"]
        token_data = fake_redis.get(f"reg_token:{token}")
        assert token_data is not None
        token_info = json.loads(token_data)
        assert token_info["institution_id"] == "institution_123"

    @patch("priotag.api.routes.auth.InstitutionService.get_by_short_code")
    @patch("priotag.api.routes.auth.get_redis")
    def test_verify_magic_word_institution_not_found(
        self, mock_get_redis, mock_get_institution, fake_redis
    ):
        """Test magic word verification with non-existent institution."""
        from fastapi import HTTPException

        # Mock institution not found
        mock_get_institution.side_effect = HTTPException(
            status_code=404, detail="Not found"
        )
        mock_get_redis.return_value = fake_redis

        # Test
        response = client.post(
            "/api/v1/auth/verify-magic-word",
            json={
                "magic_word": "SomeMagic",
                "institution_short_code": "NONEXISTENT",
            },
        )

        # Verify
        assert response.status_code == 404

    @patch("priotag.api.routes.auth.InstitutionService.get_by_short_code")
    @patch("priotag.api.routes.auth.get_redis")
    def test_verify_magic_word_inactive_institution(
        self, mock_get_redis, mock_get_institution, sample_institution_data, fake_redis
    ):
        """Test magic word verification with inactive institution."""
        from priotag.models.pocketbase_schemas import InstitutionRecord

        # Mock inactive institution
        inactive_data = sample_institution_data.copy()
        inactive_data["active"] = False
        mock_get_institution.return_value = InstitutionRecord(**inactive_data)
        mock_get_redis.return_value = fake_redis

        # Test
        response = client.post(
            "/api/v1/auth/verify-magic-word",
            json={
                "magic_word": "TestMagic123",
                "institution_short_code": "TEST_UNIV",
            },
        )

        # Verify
        assert response.status_code == 403
        assert "nicht aktiv" in response.json()["detail"]

    @patch("priotag.api.routes.auth.InstitutionService.get_by_short_code")
    @patch("priotag.api.routes.auth.get_redis")
    def test_verify_magic_word_wrong_magic_word(
        self, mock_get_redis, mock_get_institution, sample_institution_data, fake_redis
    ):
        """Test magic word verification with incorrect magic word."""
        from priotag.models.pocketbase_schemas import InstitutionRecord

        mock_get_institution.return_value = InstitutionRecord(**sample_institution_data)
        mock_get_redis.return_value = fake_redis

        # Test with wrong magic word
        response = client.post(
            "/api/v1/auth/verify-magic-word",
            json={
                "magic_word": "WrongMagic",
                "institution_short_code": "TEST_UNIV",
            },
        )

        # Verify
        assert response.status_code == 403
        assert "Ungültiges Zauberwort" in response.json()["detail"]

    @patch("priotag.api.routes.auth.InstitutionService.get_by_short_code")
    @patch("priotag.api.routes.auth.get_redis")
    def test_verify_magic_word_case_insensitive(
        self, mock_get_redis, mock_get_institution, sample_institution_data, fake_redis
    ):
        """Test magic word verification is case-insensitive."""
        from priotag.models.pocketbase_schemas import InstitutionRecord

        mock_get_institution.return_value = InstitutionRecord(**sample_institution_data)
        mock_get_redis.return_value = fake_redis

        # Test with different case
        response = client.post(
            "/api/v1/auth/verify-magic-word",
            json={
                "magic_word": "testmagic123",  # lowercase
                "institution_short_code": "TEST_UNIV",
            },
        )

        # Verify
        assert response.status_code == 200


class TestRegistrationWithInstitution:
    """Test user registration with institution."""

    @patch("priotag.api.routes.auth.authenticate_service_account")
    @patch("priotag.api.routes.auth.get_redis")
    def test_register_with_institution_token(
        self,
        mock_get_redis,
        mock_auth_service,
        fake_redis,
        sample_institution_data,
    ):
        """Test registration with valid institution token."""
        # Setup mocks
        mock_auth_service.return_value = "service_token"
        mock_get_redis.return_value = fake_redis

        # Create registration token with institution_id
        reg_token = "test_reg_token_123"
        token_data = {
            "created_at": "2025-01-01T00:00:00",
            "ip": "127.0.0.1",
            "institution_id": "institution_123",
        }
        fake_redis.setex(f"reg_token:{reg_token}", 600, json.dumps(token_data))

        # Mock PocketBase responses
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client

            # Mock user creation response
            create_response = AsyncMock()
            create_response.status_code = 200
            create_response.json.return_value = {
                "id": "new_user_123",
                "username": "newuser",
            }

            # Mock auth response
            auth_response = AsyncMock()
            auth_response.status_code = 200
            auth_response.json.return_value = {
                "token": "new_auth_token",
                "record": {
                    "id": "new_user_123",
                    "username": "newuser",
                    "role": "user",
                    "institution_id": "institution_123",
                },
            }

            mock_client.post.side_effect = [create_response, auth_response]
            mock_client_class.return_value = mock_client

            # Test
            response = client.post(
                "/api/v1/auth/register",
                json={
                    "identity": "newuser@test.com",
                    "password": "TestPassword123!",
                    "passwordConfirm": "TestPassword123!",
                    "name": "New User",
                    "registration_token": reg_token,
                    "keep_logged_in": False,
                },
            )

            # Verify
            assert response.status_code == 200

            # Verify institution_id was included in user creation
            user_create_call = mock_client.post.call_args_list[0]
            user_data = user_create_call[1]["json"]
            assert user_data["institution_id"] == "institution_123"


class TestQRRegistrationWithInstitution:
    """Test QR code registration with institution."""

    @patch("priotag.api.routes.auth.InstitutionService.get_by_short_code")
    @patch("priotag.api.routes.auth.authenticate_service_account")
    @patch("priotag.api.routes.auth.get_redis")
    def test_register_qr_with_institution_success(
        self,
        mock_get_redis,
        mock_auth_service,
        mock_get_institution,
        fake_redis,
        sample_institution_data,
    ):
        """Test QR registration with institution short code."""
        from priotag.models.pocketbase_schemas import InstitutionRecord

        # Setup mocks
        mock_get_institution.return_value = InstitutionRecord(**sample_institution_data)
        mock_auth_service.return_value = "service_token"
        mock_get_redis.return_value = fake_redis

        # Mock PocketBase responses
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client

            # Mock user creation response
            create_response = AsyncMock()
            create_response.status_code = 200
            create_response.json.return_value = {
                "id": "qr_user_123",
                "username": "qruser",
            }

            # Mock auth response
            auth_response = AsyncMock()
            auth_response.status_code = 200
            auth_response.json.return_value = {
                "token": "qr_auth_token",
                "record": {
                    "id": "qr_user_123",
                    "username": "qruser",
                    "role": "user",
                    "institution_id": "institution_123",
                },
            }

            mock_client.post.side_effect = [create_response, auth_response]
            mock_client_class.return_value = mock_client

            # Test
            response = client.post(
                "/api/v1/auth/register-qr",
                json={
                    "identity": "qruser@test.com",
                    "password": "TestPassword123!",
                    "passwordConfirm": "TestPassword123!",
                    "name": "QR User",
                    "magic_word": "TestMagic123",
                    "institution_short_code": "TEST_UNIV",
                    "keep_logged_in": False,
                },
            )

            # Verify
            assert response.status_code == 200

            # Verify institution_id was included
            user_create_call = mock_client.post.call_args_list[0]
            user_data = user_create_call[1]["json"]
            assert user_data["institution_id"] == "institution_123"


class TestSessionInfoWithInstitution:
    """Test session info includes institution data."""

    def test_extract_session_info_with_institution(self, sample_user_data):
        """Test extracting session info includes institution_id."""
        from priotag.models.pocketbase_schemas import UsersResponse
        from priotag.utils import extract_session_info_from_record

        user = UsersResponse(**sample_user_data)
        session = extract_session_info_from_record(user)

        assert session.id == "test_user_123"
        assert session.username == "testuser"
        assert session.role == "user"
        assert session.institution_id == "institution_123"
        assert session.is_admin is False

    def test_extract_session_info_institution_admin(self, sample_admin_data):
        """Test extracting session info for institution admin."""
        from priotag.models.pocketbase_schemas import UsersResponse
        from priotag.utils import extract_session_info_from_record

        admin = UsersResponse(**sample_admin_data)
        session = extract_session_info_from_record(admin)

        assert session.role == "institution_admin"
        assert session.institution_id == "institution_123"
        assert session.is_admin is True

    def test_extract_session_info_super_admin(self, sample_super_admin_data):
        """Test extracting session info for super admin."""
        from priotag.models.pocketbase_schemas import UsersResponse
        from priotag.utils import extract_session_info_from_record

        super_admin = UsersResponse(**sample_super_admin_data)
        session = extract_session_info_from_record(super_admin)

        assert session.role == "super_admin"
        assert session.institution_id is None  # Super admin has no institution
        assert session.is_admin is True
