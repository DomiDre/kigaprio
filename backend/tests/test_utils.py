"""
Tests for utility functions.

Tests cover:
- get_current_token (extract auth token from cookie)
- get_current_dek (extract DEK from cookie)
- verify_token (session verification)
- require_admin (admin authorization)
- extract_session_info_from_record
- get_client_ip
- update_last_seen
"""

import base64
import json

import pytest
from fastapi import HTTPException, Response

from kigaprio.models.auth import SessionInfo
from kigaprio.models.pocketbase_schemas import UsersResponse
from kigaprio.utils import (
    extract_session_info_from_record,
    get_client_ip,
    get_current_dek,
    get_current_token,
    require_admin,
    update_last_seen,
    verify_token,
)


@pytest.mark.unit
class TestGetCurrentToken:
    """Test auth token extraction from cookie."""

    @pytest.mark.asyncio
    async def test_get_current_token_success(self):
        """Should return token when present in cookie."""
        token = "test_token_value"
        result = await get_current_token(auth_token=token)
        assert result == token

    @pytest.mark.asyncio
    async def test_get_current_token_missing(self):
        """Should raise 401 when token is missing."""
        with pytest.raises(HTTPException) as exc_info:
            await get_current_token(auth_token=None)

        assert exc_info.value.status_code == 401
        assert "Nicht authentifiziert" in exc_info.value.detail


@pytest.mark.unit
class TestGetCurrentDek:
    """Test DEK extraction from cookie."""

    @pytest.mark.asyncio
    async def test_get_current_dek_success(self):
        """Should decode and return DEK when present."""
        dek_bytes = b"test_dek_32_bytes_long_value!!"
        dek_b64 = base64.b64encode(dek_bytes).decode("utf-8")

        result = await get_current_dek(dek=dek_b64)
        assert result == dek_bytes

    @pytest.mark.asyncio
    async def test_get_current_dek_missing(self):
        """Should raise 400 when DEK is missing."""
        with pytest.raises(HTTPException) as exc_info:
            await get_current_dek(dek=None)

        assert exc_info.value.status_code == 400
        assert "Verschlüsselungsschlüssel nicht gefunden" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_get_current_dek_invalid_base64(self):
        """Should raise 400 when DEK is not valid base64."""
        with pytest.raises(HTTPException) as exc_info:
            await get_current_dek(dek="not_valid_base64!!!")

        assert exc_info.value.status_code == 400
        assert "Ungültiger Verschlüsselungsschlüssel" in exc_info.value.detail


@pytest.mark.unit
class TestRequireAdmin:
    """Test admin authorization function."""

    @pytest.mark.asyncio
    async def test_require_admin_success(self, sample_admin_session_info):
        """Should allow admin users."""
        result = await require_admin(sample_admin_session_info)
        assert result.is_admin is True
        assert result.id == sample_admin_session_info.id

    @pytest.mark.asyncio
    async def test_require_admin_failure(self, sample_session_info):
        """Should reject non-admin users."""
        with pytest.raises(HTTPException) as exc_info:
            await require_admin(sample_session_info)

        assert exc_info.value.status_code == 403
        assert "Administratorrechte erforderlich" in exc_info.value.detail


@pytest.mark.unit
class TestExtractSessionInfo:
    """Test session info extraction from PocketBase record."""

    def test_extract_session_info_user(self, sample_user_data):
        """Should extract session info for regular user."""
        record = UsersResponse(**sample_user_data)
        result = extract_session_info_from_record(record)

        assert isinstance(result, SessionInfo)
        assert result.id == sample_user_data["id"]
        assert result.username == sample_user_data["username"]
        assert result.is_admin is False

    def test_extract_session_info_admin(self, sample_admin_data):
        """Should extract session info for admin user."""
        record = UsersResponse(**sample_admin_data)
        result = extract_session_info_from_record(record)

        assert isinstance(result, SessionInfo)
        assert result.id == sample_admin_data["id"]
        assert result.username == sample_admin_data["username"]
        assert result.is_admin is True


