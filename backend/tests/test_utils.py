"""
Tests for utility functions.

Tests cover:
- get_current_token (extract auth token from cookie)
- get_current_dek (extract DEK from cookie)
- verify_token (session verification, Redis caching, PocketBase fallback)
- require_admin (admin authorization)
- extract_session_info_from_record
- get_client_ip (header parsing)
- update_last_seen (throttling and database updates)
"""

import base64
from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi import HTTPException, Response

from priotag.models.auth import SessionInfo
from priotag.models.pocketbase_schemas import UsersResponse
from priotag.utils import (
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


@pytest.mark.unit
class TestGetClientIP:
    """Test client IP extraction from request headers."""

    def test_get_client_ip_from_forwarded_for(self):
        """Should extract IP from X-Forwarded-For header."""
        mock_request = Mock()
        mock_request.headers.get.return_value = "192.168.1.100, 10.0.0.1"
        mock_request.client = None

        result = get_client_ip(mock_request)

        assert result == "192.168.1.100"

    def test_get_client_ip_from_real_ip(self):
        """Should extract IP from X-Real-IP header when X-Forwarded-For absent."""
        mock_request = Mock()

        def mock_get_header(header_name):
            if header_name == "X-Forwarded-For":
                return None
            if header_name == "X-Real-IP":
                return "203.0.113.42"
            return None

        mock_request.headers.get = mock_get_header
        mock_request.client = None

        result = get_client_ip(mock_request)

        assert result == "203.0.113.42"

    def test_get_client_ip_from_direct_connection(self):
        """Should use direct connection IP when no headers present."""
        mock_request = Mock()
        mock_request.headers.get.return_value = None
        mock_request.client.host = "198.51.100.5"

        result = get_client_ip(mock_request)

        assert result == "198.51.100.5"

    def test_get_client_ip_fallback_localhost(self):
        """Should fallback to localhost when no client info available."""
        mock_request = Mock()
        mock_request.headers.get.return_value = None
        mock_request.client = None

        result = get_client_ip(mock_request)

        assert result == "127.0.0.1"

    def test_get_client_ip_strips_whitespace(self):
        """Should strip whitespace from forwarded IP."""
        mock_request = Mock()
        mock_request.headers.get.return_value = "  192.168.1.100  , 10.0.0.1"
        mock_request.client = None

        result = get_client_ip(mock_request)

        assert result == "192.168.1.100"


@pytest.mark.unit
class TestUpdateLastSeen:
    """Test lastSeen update with throttling."""

    @pytest.mark.asyncio
    async def test_update_last_seen_first_time(self, fake_redis):
        """Should update lastSeen on first call."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            mock_response = Mock()
            mock_response.status_code = 200
            mock_client.patch.return_value = mock_response

            await update_last_seen("user123", "token123", fake_redis)

            # Should have called PocketBase PATCH
            mock_client.patch.assert_called_once()

            # Should have set throttle key
            assert fake_redis.get("lastseen:user123") is not None

    @pytest.mark.asyncio
    async def test_update_last_seen_throttled(self, fake_redis):
        """Should skip update when recently updated."""
        # Set throttle key
        fake_redis.setex("lastseen:user123", 3600, "1")

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            await update_last_seen("user123", "token123", fake_redis)

            # Should NOT have called PocketBase
            mock_client.patch.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_last_seen_sets_current_time(self, fake_redis):
        """Should set current timestamp in lastSeen."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            mock_response = Mock()
            mock_response.status_code = 200
            mock_client.patch.return_value = mock_response

            before_time = datetime.now(UTC)

            await update_last_seen("user123", "token123", fake_redis)

            # Check the lastSeen value sent to PocketBase
            patch_call = mock_client.patch.call_args
            json_data = patch_call.kwargs["json"]
            last_seen_str = json_data["lastSeen"]
            last_seen_time = datetime.fromisoformat(
                last_seen_str.replace("Z", "+00:00")
            )

            # Should be recent
            assert last_seen_time >= before_time

    @pytest.mark.asyncio
    async def test_update_last_seen_handles_patch_failure(self, fake_redis):
        """Should handle PocketBase update failure gracefully."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            mock_response = Mock()
            mock_response.status_code = 500
            mock_response.text = "Server error"
            mock_client.patch.return_value = mock_response

            # Should not raise exception
            await update_last_seen("user123", "token123", fake_redis)

    @pytest.mark.asyncio
    async def test_update_last_seen_handles_network_error(self, fake_redis):
        """Should handle network errors gracefully."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            import httpx

            mock_client.patch.side_effect = httpx.RequestError("Network error")

            # Should not raise exception
            await update_last_seen("user123", "token123", fake_redis)

    @pytest.mark.asyncio
    async def test_update_last_seen_handles_redis_error(self, fake_redis):
        """Should continue even if Redis throttle check fails."""
        # Make Redis raise error
        fake_redis.get = Mock(side_effect=Exception("Redis error"))

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            mock_response = Mock()
            mock_response.status_code = 200
            mock_client.patch.return_value = mock_response

            # Should still attempt update
            await update_last_seen("user123", "token123", fake_redis)

            mock_client.patch.assert_called_once()


@pytest.mark.unit
class TestVerifyToken:
    """Test token verification with caching."""

    @pytest.mark.asyncio
    async def test_verify_token_blacklisted(self, fake_redis):
        """Should reject blacklisted tokens."""
        mock_response = Response()
        fake_redis.set("blacklist:token123", "1")

        with pytest.raises(HTTPException) as exc_info:
            await verify_token(mock_response, "token123", fake_redis)

        assert exc_info.value.status_code == 401
        assert "Logout" in exc_info.value.detail or "ungültig" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_verify_token_cache_hit(self, fake_redis, sample_session_info):
        """Should return session from cache on cache hit."""
        mock_response = Response()

        # Set cache
        fake_redis.setex(
            "session:token123", 3600, sample_session_info.model_dump_json()
        )

        with patch("priotag.utils.update_last_seen") as mock_update:
            result = await verify_token(mock_response, "token123", fake_redis)

            assert result.id == sample_session_info.id
            assert result.username == sample_session_info.username

            # Should update lastSeen in background
            mock_update.assert_called_once()

    @pytest.mark.asyncio
    async def test_verify_token_cache_miss_success(self, fake_redis, sample_user_data):
        """Should fetch from PocketBase on cache miss."""
        mock_response = Response()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            mock_pb_response = Mock()
            mock_pb_response.status_code = 200
            mock_pb_response.json.return_value = {
                "token": "token123",
                "record": sample_user_data,
            }
            mock_client.post.return_value = mock_pb_response

            with patch("priotag.utils.update_last_seen"):
                result = await verify_token(mock_response, "token123", fake_redis)

                assert result.id == sample_user_data["id"]
                assert result.username == sample_user_data["username"]

                # Should cache the session
                cached = fake_redis.get("session:token123")
                assert cached is not None

    @pytest.mark.asyncio
    async def test_verify_token_refresh_updates_cookie(
        self, fake_redis, sample_user_data
    ):
        """Should update cookie when token is refreshed."""
        mock_response = Response()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            # Return different token (refreshed)
            mock_pb_response = Mock()
            mock_pb_response.status_code = 200
            mock_pb_response.json.return_value = {
                "token": "new_token123",  # Different token
                "record": sample_user_data,
            }
            mock_client.post.return_value = mock_pb_response

            with patch("priotag.utils.update_last_seen"):
                await verify_token(mock_response, "old_token", fake_redis)

                # Should have set new cookie (check in headers)
                # Response.set_cookie adds to headers, not cookies attribute
                assert "set-cookie" in mock_response.headers

    @pytest.mark.asyncio
    async def test_verify_token_admin_shorter_ttl(self, fake_redis, sample_admin_data):
        """Should use shorter TTL for admin sessions."""
        mock_response = Response()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            mock_pb_response = Mock()
            mock_pb_response.status_code = 200
            mock_pb_response.json.return_value = {
                "token": "token123",
                "record": sample_admin_data,
            }
            mock_client.post.return_value = mock_pb_response

            with patch("priotag.utils.update_last_seen"):
                await verify_token(mock_response, "token123", fake_redis)

                # Check TTL (admin should be 900 seconds)
                ttl = fake_redis.ttl("session:token123")
                assert ttl <= 900

    @pytest.mark.asyncio
    async def test_verify_token_pb_auth_failure(self, fake_redis):
        """Should raise 401 when PocketBase auth refresh fails."""
        mock_response = Response()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            mock_pb_response = Mock()
            mock_pb_response.status_code = 401
            mock_client.post.return_value = mock_pb_response

            with pytest.raises(HTTPException) as exc_info:
                await verify_token(mock_response, "invalid_token", fake_redis)

            assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_verify_token_pb_connection_error(self, fake_redis):
        """Should raise 503 on PocketBase connection error."""
        mock_response = Response()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            import httpx

            mock_client.post.side_effect = httpx.RequestError("Connection failed")

            with pytest.raises(HTTPException) as exc_info:
                await verify_token(mock_response, "token123", fake_redis)

            assert exc_info.value.status_code == 503

    @pytest.mark.asyncio
    async def test_verify_token_handles_invalid_cache_data(self, fake_redis):
        """Should fall back to PocketBase if cached data is invalid."""
        mock_response = Response()

        # Set invalid JSON in cache
        fake_redis.set("session:token123", "invalid json{{{")

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            mock_pb_response = Mock()
            mock_pb_response.status_code = 200
            mock_pb_response.json.return_value = {
                "token": "token123",
                "record": {
                    "id": "user123",
                    "username": "testuser",
                    "email": "test@example.com",
                    "emailVisibility": False,
                    "role": "user",
                    "salt": "dGVzdF9zYWx0",
                    "user_wrapped_dek": "d3JhcHBlZF9kZWs=",
                    "admin_wrapped_dek": "YWRtaW5fd3JhcHBlZA==",
                    "encrypted_fields": "ZW5jcnlwdGVk",
                    "lastSeen": "2024-01-01T00:00:00Z",
                    "verified": True,
                    "collectionId": "coll",
                    "collectionName": "users",
                    "created": "2024-01-01T00:00:00Z",
                    "updated": "2024-01-01T00:00:00Z",
                },
            }
            mock_client.post.return_value = mock_pb_response

            with patch("priotag.utils.update_last_seen"):
                # Should not raise, falls back to PocketBase
                result = await verify_token(mock_response, "token123", fake_redis)

                assert result.id == "user123"

    @pytest.mark.asyncio
    async def test_verify_token_handles_redis_error(self, fake_redis):
        """Should fall back to PocketBase on Redis error."""
        mock_response = Response()

        # Make Redis raise error
        fake_redis.get = Mock(side_effect=Exception("Redis down"))

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            mock_pb_response = Mock()
            mock_pb_response.status_code = 200
            mock_pb_response.json.return_value = {
                "token": "token123",
                "record": {
                    "id": "user123",
                    "username": "testuser",
                    "email": "test@example.com",
                    "emailVisibility": False,
                    "role": "user",
                    "salt": "dGVzdF9zYWx0",
                    "user_wrapped_dek": "d3JhcHBlZF9kZWs=",
                    "admin_wrapped_dek": "YWRtaW5fd3JhcHBlZA==",
                    "encrypted_fields": "ZW5jcnlwdGVk",
                    "lastSeen": "2024-01-01T00:00:00Z",
                    "verified": True,
                    "collectionId": "coll",
                    "collectionName": "users",
                    "created": "2024-01-01T00:00:00Z",
                    "updated": "2024-01-01T00:00:00Z",
                },
            }
            mock_client.post.return_value = mock_pb_response

            with patch("priotag.utils.update_last_seen"):
                # Should not raise, falls back to PocketBase
                result = await verify_token(mock_response, "token123", fake_redis)

                assert result.id == "user123"

    @pytest.mark.asyncio
    async def test_verify_token_blacklist_check_error(self, fake_redis):
        """Should continue if blacklist check fails (don't block valid users)."""
        mock_response = Response()

        # Make blacklist check raise error
        def blacklist_error(key):
            if key.startswith("blacklist:"):
                raise Exception("Redis error")
            return None

        fake_redis.get = Mock(side_effect=blacklist_error)

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            mock_pb_response = Mock()
            mock_pb_response.status_code = 200
            mock_pb_response.json.return_value = {
                "token": "token123",
                "record": {
                    "id": "user123",
                    "username": "testuser",
                    "email": "test@example.com",
                    "emailVisibility": False,
                    "role": "user",
                    "salt": "dGVzdF9zYWx0",
                    "user_wrapped_dek": "d3JhcHBlZF9kZWs=",
                    "admin_wrapped_dek": "YWRtaW5fd3JhcHBlZA==",
                    "encrypted_fields": "ZW5jcnlwdGVk",
                    "lastSeen": "2024-01-01T00:00:00Z",
                    "verified": True,
                    "collectionId": "coll",
                    "collectionName": "users",
                    "created": "2024-01-01T00:00:00Z",
                    "updated": "2024-01-01T00:00:00Z",
                },
            }
            mock_client.post.return_value = mock_pb_response

            with patch("priotag.utils.update_last_seen"):
                # Should not raise, continues even if blacklist check fails
                result = await verify_token(mock_response, "token123", fake_redis)
                assert result.id == "user123"

    @pytest.mark.asyncio
    async def test_verify_token_session_deletion_error(
        self, fake_redis, sample_user_data
    ):
        """Should handle error when deleting old session."""
        mock_response = Response()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            # Mock token refresh response
            mock_pb_response = Mock()
            mock_pb_response.status_code = 200
            mock_pb_response.json.return_value = {
                "token": "new_token",  # Different token triggers deletion
                "record": sample_user_data,
            }
            mock_client.post.return_value = mock_pb_response

            # Make delete raise error for old session
            original_delete = fake_redis.delete

            def delete_error(key):
                if "old_token" in str(key):
                    raise Exception("Redis delete failed")
                return original_delete(key)

            fake_redis.delete = Mock(side_effect=delete_error)

            with patch("priotag.utils.update_last_seen"):
                # Should not raise, logs warning and continues
                result = await verify_token(mock_response, "old_token", fake_redis)
                assert result.id == sample_user_data["id"]

    @pytest.mark.asyncio
    async def test_verify_token_setex_error(self, fake_redis, sample_user_data):
        """Should handle error when setting new session in Redis."""
        mock_response = Response()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            mock_pb_response = Mock()
            mock_pb_response.status_code = 200
            mock_pb_response.json.return_value = {
                "token": "new_token",
                "record": sample_user_data,
            }
            mock_client.post.return_value = mock_pb_response

            # Make setex raise error
            fake_redis.setex = Mock(side_effect=Exception("Redis setex failed"))

            with patch("priotag.utils.update_last_seen"):
                # Should not raise, logs warning and continues
                result = await verify_token(mock_response, "token123", fake_redis)
                assert result.id == sample_user_data["id"]

    @pytest.mark.asyncio
    async def test_update_last_seen_setex_throttle_error(self, fake_redis):
        """Should handle error when setting throttle key in Redis."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            mock_response = Mock()
            mock_response.status_code = 200
            mock_client.patch.return_value = mock_response

            # Make setex raise error for throttle key
            original_setex = fake_redis.setex

            def setex_error(key, ttl, value):
                if key.startswith("lastseen:"):
                    raise Exception("Redis setex failed")
                return original_setex(key, ttl, value)

            fake_redis.setex = Mock(side_effect=setex_error)

            # Should not raise, logs warning and continues
            await update_last_seen("user123", "token123", fake_redis)

            # Should have attempted the update
            mock_client.patch.assert_called_once()
