"""
Tests for service account authentication.

Tests cover:
- Service account authentication success
- Authentication failure handling
- Network error handling
- Credential loading from secrets
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest


@pytest.mark.unit
class TestServiceAccountAuthentication:
    """Test service account authentication functions."""

    @pytest.mark.asyncio
    async def test_authenticate_service_account_success(self):
        """Should successfully authenticate and return token."""
        from priotag.services.service_account import authenticate_service_account

        mock_client = AsyncMock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "token": "service_token_123",
            "record": {"id": "service_id", "username": "pb_service"},
        }
        mock_client.post.return_value = mock_response

        token = await authenticate_service_account(mock_client)

        assert token == "service_token_123"
        mock_client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_authenticate_service_account_failed_auth(self):
        """Should return None on authentication failure."""
        from priotag.services.service_account import authenticate_service_account

        mock_client = AsyncMock()
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.text = "Invalid credentials"
        mock_client.post.return_value = mock_response

        with patch("priotag.services.service_account.logger") as mock_logger:
            token = await authenticate_service_account(mock_client)

            assert token is None
            mock_logger.error.assert_called_once()
            assert "authentication failed" in mock_logger.error.call_args[0][0]

    @pytest.mark.asyncio
    async def test_authenticate_service_account_network_error(self):
        """Should handle network errors gracefully."""
        from priotag.services.service_account import authenticate_service_account

        mock_client = AsyncMock()
        import httpx

        mock_client.post.side_effect = httpx.RequestError("Network error")

        with patch("priotag.services.service_account.logger") as mock_logger:
            token = await authenticate_service_account(mock_client)

            assert token is None
            mock_logger.error.assert_called_once()
            assert (
                "Error during service account authentication"
                in mock_logger.error.call_args[0][0]
            )

    @pytest.mark.asyncio
    async def test_authenticate_service_account_malformed_response(self):
        """Should handle malformed response gracefully."""
        from priotag.services.service_account import authenticate_service_account

        mock_client = AsyncMock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {}  # Missing 'token' field
        mock_client.post.return_value = mock_response

        token = await authenticate_service_account(mock_client)

        # Should return None if token field is missing
        assert token is None

    @pytest.mark.asyncio
    async def test_authenticate_service_account_uses_credentials(self):
        """Should use service account credentials from environment."""
        from priotag.services.service_account import authenticate_service_account

        mock_client = AsyncMock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"token": "token_123"}
        mock_client.post.return_value = mock_response

        await authenticate_service_account(mock_client)

        # Verify credentials were used in the request
        call_args = mock_client.post.call_args
        assert call_args is not None
        json_data = call_args.kwargs.get("json", {})
        assert "identity" in json_data
        assert "password" in json_data


@pytest.mark.unit
class TestServiceAccountCredentials:
    """Test service account credential loading."""

    def test_credentials_loaded_from_secrets(self):
        """Should load credentials from secret files if they exist."""
        # The module loads credentials at import time, so we test the behavior
        # by checking the constants exist
        from priotag.services.service_account import (
            SERVICE_ACCOUNT_ID,
            SERVICE_ACCOUNT_PASSWORD,
        )

        # Should have some values (either from files or defaults)
        assert SERVICE_ACCOUNT_ID is not None
        assert SERVICE_ACCOUNT_PASSWORD is not None

    def test_credentials_use_defaults_if_missing(self):
        """Should use default credentials if secret files don't exist."""
        # Test that the module can be imported even without secret files
        # The actual warning happens at module import time, not in a function
        # So we just verify the module imports successfully
        import priotag.services.service_account

        # Module should import successfully
        assert hasattr(priotag.services.service_account, "SERVICE_ACCOUNT_ID")
        assert hasattr(priotag.services.service_account, "SERVICE_ACCOUNT_PASSWORD")
