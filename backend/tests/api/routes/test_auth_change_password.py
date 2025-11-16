"""
Tests for password change endpoint in auth routes.

Tests cover:
- Change password success flow
- Current password verification
- Encryption data re-wrapping
- Session invalidation
- New token generation
- Cookie updates
- Error cases (wrong password, network errors, etc.)
"""

import base64
import json
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi import HTTPException

from priotag.models.auth import SessionInfo


@pytest.mark.unit
class TestChangePasswordEndpoint:
    """Test /api/v1/auth/change-password endpoint."""

    @pytest.mark.asyncio
    async def test_change_password_success(self, fake_redis, sample_user_data):
        """Should successfully change password and invalidate old sessions."""
        from priotag.api.routes.auth import change_password
        from priotag.models.auth import ChangePasswordRequest

        # Setup
        session_info = SessionInfo(
            id="user123", username="testuser", is_admin=False
        )
        token = "current_token_123"
        request_data = ChangePasswordRequest(
            current_password="OldPassword123!",
            new_password="NewPassword456!",
        )

        # Mock response object
        mock_response = Mock()
        mock_response.headers = {}

        # Create encryption data for the user
        from priotag.services.encryption import EncryptionManager
        encryption_data = EncryptionManager.create_user_encryption_data(
            request_data.current_password
        )

        user_data_with_encryption = {
            **sample_user_data,
            "salt": encryption_data["salt"],
            "user_wrapped_dek": encryption_data["user_wrapped_dek"],
            "admin_wrapped_dek": encryption_data["admin_wrapped_dek"],
        }

        # Mock httpx.AsyncClient
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            # Mock getting user record
            mock_get_response = Mock()
            mock_get_response.status_code = 200
            mock_get_response.json.return_value = user_data_with_encryption
            mock_client.get.return_value = mock_get_response

            # Mock updating user record
            mock_patch_response = Mock()
            mock_patch_response.status_code = 200
            mock_client.patch.return_value = mock_patch_response

            # Mock re-authentication with new password
            mock_auth_response = Mock()
            mock_auth_response.status_code = 200
            mock_auth_response.json.return_value = {
                "token": "new_token_456",
                "record": user_data_with_encryption,
            }
            mock_client.post.return_value = mock_auth_response

            # Add some existing sessions to Redis
            fake_redis.setex(
                "session:old_token_1",
                3600,
                json.dumps({"user_id": "user123", "username": "testuser"}),
            )
            fake_redis.setex(
                "session:old_token_2",
                3600,
                json.dumps({"user_id": "user123", "username": "testuser"}),
            )
            fake_redis.setex(
                f"session:{token}",
                3600,
                json.dumps({"user_id": "user123", "username": "testuser"}),
            )

            # Call the endpoint
            result = await change_password(
                request_data, mock_response, session_info, token, fake_redis
            )

            # Assertions
            assert result["success"] is True
            assert "Passwort erfolgreich geändert" in result["message"]

            # Old sessions should be deleted
            assert fake_redis.get("session:old_token_1") is None
            assert fake_redis.get("session:old_token_2") is None
            assert fake_redis.get(f"session:{token}") is None

            # New session should exist
            new_session = fake_redis.get("session:new_token_456")
            assert new_session is not None

    @pytest.mark.asyncio
    async def test_change_password_wrong_current_password(
        self, fake_redis, sample_user_data
    ):
        """Should reject password change if current password is wrong."""
        from priotag.api.routes.auth import change_password
        from priotag.models.auth import ChangePasswordRequest

        session_info = SessionInfo(
            id="user123", username="testuser", is_admin=False
        )
        token = "current_token_123"
        request_data = ChangePasswordRequest(
            current_password="WrongPassword!!!",
            new_password="NewPassword456!",
        )

        mock_response = Mock()
        mock_response.headers = {}

        # Create encryption data with a different password
        from priotag.services.encryption import EncryptionManager
        encryption_data = EncryptionManager.create_user_encryption_data(
            "ActualPassword123!"
        )

        user_data_with_encryption = {
            **sample_user_data,
            "salt": encryption_data["salt"],
            "user_wrapped_dek": encryption_data["user_wrapped_dek"],
        }

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            mock_get_response = Mock()
            mock_get_response.status_code = 200
            mock_get_response.json.return_value = user_data_with_encryption
            mock_client.get.return_value = mock_get_response

            # Should raise 400 error
            with pytest.raises(HTTPException) as exc_info:
                await change_password(
                    request_data, mock_response, session_info, token, fake_redis
                )

            assert exc_info.value.status_code == 400
            assert "Aktuelles Passwort ist falsch" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_change_password_get_user_fails(self, fake_redis):
        """Should handle failure to retrieve user record."""
        from priotag.api.routes.auth import change_password
        from priotag.models.auth import ChangePasswordRequest

        session_info = SessionInfo(
            id="user123", username="testuser", is_admin=False
        )
        token = "current_token_123"
        request_data = ChangePasswordRequest(
            current_password="OldPassword123!",
            new_password="NewPassword456!",
        )

        mock_response = Mock()
        mock_response.headers = {}

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            # Mock failed user retrieval
            mock_get_response = Mock()
            mock_get_response.status_code = 404
            mock_client.get.return_value = mock_get_response

            with pytest.raises(HTTPException) as exc_info:
                await change_password(
                    request_data, mock_response, session_info, token, fake_redis
                )

            assert exc_info.value.status_code == 500
            assert "Benutzerdaten konnten nicht abgerufen werden" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_change_password_update_fails(self, fake_redis, sample_user_data):
        """Should handle failure to update user record."""
        from priotag.api.routes.auth import change_password
        from priotag.models.auth import ChangePasswordRequest

        session_info = SessionInfo(
            id="user123", username="testuser", is_admin=False
        )
        token = "current_token_123"
        request_data = ChangePasswordRequest(
            current_password="OldPassword123!",
            new_password="NewPassword456!",
        )

        mock_response = Mock()
        mock_response.headers = {}

        from priotag.services.encryption import EncryptionManager
        encryption_data = EncryptionManager.create_user_encryption_data(
            request_data.current_password
        )

        user_data_with_encryption = {
            **sample_user_data,
            "salt": encryption_data["salt"],
            "user_wrapped_dek": encryption_data["user_wrapped_dek"],
        }

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            # Mock successful get
            mock_get_response = Mock()
            mock_get_response.status_code = 200
            mock_get_response.json.return_value = user_data_with_encryption
            mock_client.get.return_value = mock_get_response

            # Mock failed update
            mock_patch_response = Mock()
            mock_patch_response.status_code = 500
            mock_client.patch.return_value = mock_patch_response

            with pytest.raises(HTTPException) as exc_info:
                await change_password(
                    request_data, mock_response, session_info, token, fake_redis
                )

            assert exc_info.value.status_code == 500
            assert "Passwort konnte nicht aktualisiert werden" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_change_password_reauth_fails(self, fake_redis, sample_user_data):
        """Should handle failure to re-authenticate with new password."""
        from priotag.api.routes.auth import change_password
        from priotag.models.auth import ChangePasswordRequest

        session_info = SessionInfo(
            id="user123", username="testuser", is_admin=False
        )
        token = "current_token_123"
        request_data = ChangePasswordRequest(
            current_password="OldPassword123!",
            new_password="NewPassword456!",
        )

        mock_response = Mock()
        mock_response.headers = {}

        from priotag.services.encryption import EncryptionManager
        encryption_data = EncryptionManager.create_user_encryption_data(
            request_data.current_password
        )

        user_data_with_encryption = {
            **sample_user_data,
            "salt": encryption_data["salt"],
            "user_wrapped_dek": encryption_data["user_wrapped_dek"],
        }

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            mock_get_response = Mock()
            mock_get_response.status_code = 200
            mock_get_response.json.return_value = user_data_with_encryption
            mock_client.get.return_value = mock_get_response

            mock_patch_response = Mock()
            mock_patch_response.status_code = 200
            mock_client.patch.return_value = mock_patch_response

            # Mock failed re-authentication
            mock_auth_response = Mock()
            mock_auth_response.status_code = 401
            mock_client.post.return_value = mock_auth_response

            with pytest.raises(HTTPException) as exc_info:
                await change_password(
                    request_data, mock_response, session_info, token, fake_redis
                )

            assert exc_info.value.status_code == 500
            assert "Authentifizierung mit neuem Passwort fehlgeschlagen" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_change_password_admin_shorter_ttl(
        self, fake_redis, sample_user_data
    ):
        """Admin users should get shorter session TTL after password change."""
        from priotag.api.routes.auth import change_password
        from priotag.models.auth import ChangePasswordRequest

        session_info = SessionInfo(
            id="admin123", username="admin", is_admin=True
        )
        token = "admin_token_123"
        request_data = ChangePasswordRequest(
            current_password="AdminPassword123!",
            new_password="NewAdminPassword456!",
        )

        mock_response = Mock()
        mock_response.headers = {}

        from priotag.services.encryption import EncryptionManager
        encryption_data = EncryptionManager.create_user_encryption_data(
            request_data.current_password
        )

        admin_data = {
            **sample_user_data,
            "id": "admin123",
            "username": "admin",
            "role": "admin",
            "salt": encryption_data["salt"],
            "user_wrapped_dek": encryption_data["user_wrapped_dek"],
            "admin_wrapped_dek": encryption_data["admin_wrapped_dek"],
        }

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            mock_get_response = Mock()
            mock_get_response.status_code = 200
            mock_get_response.json.return_value = admin_data
            mock_client.get.return_value = mock_get_response

            mock_patch_response = Mock()
            mock_patch_response.status_code = 200
            mock_client.patch.return_value = mock_patch_response

            mock_auth_response = Mock()
            mock_auth_response.status_code = 200
            mock_auth_response.json.return_value = {
                "token": "new_admin_token",
                "record": admin_data,
            }
            mock_client.post.return_value = mock_auth_response

            await change_password(
                request_data, mock_response, session_info, token, fake_redis
            )

            # Check new session has admin TTL (900 seconds = 15 minutes)
            new_session_key = "session:new_admin_token"
            ttl = fake_redis.ttl(new_session_key)
            assert ttl <= 900

    @pytest.mark.asyncio
    async def test_change_password_handles_network_error(self, fake_redis):
        """Should handle network errors gracefully."""
        from priotag.api.routes.auth import change_password
        from priotag.models.auth import ChangePasswordRequest

        session_info = SessionInfo(
            id="user123", username="testuser", is_admin=False
        )
        token = "current_token_123"
        request_data = ChangePasswordRequest(
            current_password="OldPassword123!",
            new_password="NewPassword456!",
        )

        mock_response = Mock()
        mock_response.headers = {}

        import httpx

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            # Simulate network error
            mock_client.get.side_effect = httpx.RequestError("Network error")

            with pytest.raises(HTTPException) as exc_info:
                await change_password(
                    request_data, mock_response, session_info, token, fake_redis
                )

            assert exc_info.value.status_code == 500
            assert "Ein unerwarteter Fehler ist aufgetreten" in exc_info.value.detail
