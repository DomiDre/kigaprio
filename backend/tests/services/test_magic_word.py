"""
Tests for magic word service.

Tests cover:
- get_magic_word_from_cache_or_db (Redis caching logic)
- create_or_update_magic_word (database operations)
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from priotag.services.magic_word import (
    create_or_update_magic_word,
    get_magic_word_from_cache_or_db,
)


@pytest.mark.unit
class TestGetMagicWordFromCacheOrDB:
    """Test getting magic word with cache fallback."""

    @pytest.mark.asyncio
    async def test_get_from_cache_when_present(self, fake_redis):
        """Should return cached magic word when present."""
        fake_redis.set("magic_word:current", "cached_magic_word")

        result = await get_magic_word_from_cache_or_db(fake_redis)

        assert result == "cached_magic_word"

    @pytest.mark.asyncio
    async def test_get_from_cache_bytes(self, fake_redis):
        """Should decode bytes from cache."""
        fake_redis.set("magic_word:current", b"cached_word")

        result = await get_magic_word_from_cache_or_db(fake_redis)

        assert result == "cached_word"

    @pytest.mark.asyncio
    async def test_get_from_db_when_cache_miss(self, fake_redis):
        """Should fetch from database when cache misses."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            # Mock service account authentication
            with patch(
                "priotag.services.magic_word.authenticate_service_account",
                return_value="service_token",
            ):
                # Mock database response
                mock_response = Mock()
                mock_response.status_code = 200
                mock_response.json.return_value = {
                    "items": [{"value": "database_magic_word"}]
                }
                mock_client.get.return_value = mock_response

                result = await get_magic_word_from_cache_or_db(fake_redis)

                assert result == "database_magic_word"
                # Should cache the result
                assert fake_redis.get("magic_word:current") == "database_magic_word"

    @pytest.mark.asyncio
    async def test_get_from_db_caches_with_ttl(self, fake_redis):
        """Should cache result with 5 minute TTL."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            with patch(
                "priotag.services.magic_word.authenticate_service_account",
                return_value="service_token",
            ):
                mock_response = Mock()
                mock_response.status_code = 200
                mock_response.json.return_value = {"items": [{"value": "test_word"}]}
                mock_client.get.return_value = mock_response

                await get_magic_word_from_cache_or_db(fake_redis)

                # Check TTL (should be around 300 seconds)
                ttl = fake_redis.ttl("magic_word:current")
                assert 290 <= ttl <= 300

    @pytest.mark.asyncio
    async def test_get_returns_none_when_db_empty(self, fake_redis):
        """Should return None when database has no magic word."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            with patch(
                "priotag.services.magic_word.authenticate_service_account",
                return_value="service_token",
            ):
                mock_response = Mock()
                mock_response.status_code = 200
                mock_response.json.return_value = {"items": []}
                mock_client.get.return_value = mock_response

                result = await get_magic_word_from_cache_or_db(fake_redis)

                assert result is None

    @pytest.mark.asyncio
    async def test_get_returns_none_on_auth_failure(self, fake_redis):
        """Should return None when service authentication fails."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            with patch(
                "priotag.services.magic_word.authenticate_service_account",
                return_value=None,
            ):
                result = await get_magic_word_from_cache_or_db(fake_redis)

                assert result is None

    @pytest.mark.asyncio
    async def test_get_returns_none_on_exception(self, fake_redis):
        """Should return None and log error on exception."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client_class.side_effect = Exception("Connection failed")

            result = await get_magic_word_from_cache_or_db(fake_redis)

            assert result is None

    @pytest.mark.asyncio
    async def test_get_returns_none_on_http_error(self, fake_redis):
        """Should return None when HTTP request fails."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            with patch(
                "priotag.services.magic_word.authenticate_service_account",
                return_value="service_token",
            ):
                mock_response = Mock()
                mock_response.status_code = 500
                mock_client.get.return_value = mock_response

                result = await get_magic_word_from_cache_or_db(fake_redis)

                assert result is None


@pytest.mark.unit
class TestCreateOrUpdateMagicWord:
    """Test creating or updating magic word."""

    @pytest.mark.asyncio
    async def test_update_existing_magic_word(self, fake_redis):
        """Should update existing magic word record."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            # Mock GET response (record exists)
            mock_get_response = Mock()
            mock_get_response.status_code = 200
            mock_get_response.json.return_value = {"items": [{"id": "record_123"}]}

            # Mock PATCH response (update successful)
            mock_patch_response = Mock()
            mock_patch_response.status_code = 200

            mock_client.get.return_value = mock_get_response
            mock_client.patch.return_value = mock_patch_response

            result = await create_or_update_magic_word(
                "new_magic_word", "admin_token", fake_redis, "admin@example.com"
            )

            assert result is True
            # Should have called PATCH
            mock_client.patch.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_clears_cache(self, fake_redis):
        """Should clear and update cache on successful update."""
        # Set initial cache
        fake_redis.set("magic_word:current", "old_word")

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            mock_get_response = Mock()
            mock_get_response.status_code = 200
            mock_get_response.json.return_value = {"items": [{"id": "record_123"}]}

            mock_patch_response = Mock()
            mock_patch_response.status_code = 200

            mock_client.get.return_value = mock_get_response
            mock_client.patch.return_value = mock_patch_response

            await create_or_update_magic_word(
                "new_magic_word", "admin_token", fake_redis
            )

            # Cache should be updated
            assert fake_redis.get("magic_word:current") == "new_magic_word"

    @pytest.mark.asyncio
    async def test_create_new_magic_word(self, fake_redis):
        """Should create new magic word record when none exists."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            # Mock GET response (no existing record)
            mock_get_response = Mock()
            mock_get_response.status_code = 200
            mock_get_response.json.return_value = {"items": []}

            # Mock POST response (create successful)
            mock_post_response = Mock()
            mock_post_response.status_code = 200

            mock_client.get.return_value = mock_get_response
            mock_client.post.return_value = mock_post_response

            result = await create_or_update_magic_word(
                "new_magic_word", "admin_token", fake_redis
            )

            assert result is True
            # Should have called POST
            mock_client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_sets_admin_email(self, fake_redis):
        """Should set last_updated_by field."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            mock_get_response = Mock()
            mock_get_response.status_code = 200
            mock_get_response.json.return_value = {"items": [{"id": "record_123"}]}

            mock_patch_response = Mock()
            mock_patch_response.status_code = 200

            mock_client.get.return_value = mock_get_response
            mock_client.patch.return_value = mock_patch_response

            await create_or_update_magic_word(
                "new_word", "admin_token", fake_redis, "admin@test.com"
            )

            # Check PATCH was called with correct data
            patch_call = mock_client.patch.call_args
            json_data = patch_call.kwargs["json"]
            assert json_data["last_updated_by"] == "admin@test.com"

    @pytest.mark.asyncio
    async def test_update_returns_false_on_patch_failure(self, fake_redis):
        """Should return False when update fails."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            mock_get_response = Mock()
            mock_get_response.status_code = 200
            mock_get_response.json.return_value = {"items": [{"id": "record_123"}]}

            # Mock PATCH failure
            mock_patch_response = Mock()
            mock_patch_response.status_code = 500

            mock_client.get.return_value = mock_get_response
            mock_client.patch.return_value = mock_patch_response

            result = await create_or_update_magic_word(
                "new_word", "admin_token", fake_redis
            )

            assert result is False
            # Cache should not be updated on failure
            assert fake_redis.get("magic_word:current") is None

    @pytest.mark.asyncio
    async def test_create_returns_false_on_post_failure(self, fake_redis):
        """Should return False when create fails."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            mock_get_response = Mock()
            mock_get_response.status_code = 200
            mock_get_response.json.return_value = {"items": []}

            # Mock POST failure
            mock_post_response = Mock()
            mock_post_response.status_code = 500

            mock_client.get.return_value = mock_get_response
            mock_client.post.return_value = mock_post_response

            result = await create_or_update_magic_word(
                "new_word", "admin_token", fake_redis
            )

            assert result is False

    @pytest.mark.asyncio
    async def test_returns_false_on_exception(self, fake_redis):
        """Should return False and log error on exception."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client_class.side_effect = Exception("Connection failed")

            result = await create_or_update_magic_word(
                "new_word", "admin_token", fake_redis
            )

            assert result is False

    @pytest.mark.asyncio
    async def test_returns_false_on_get_failure(self, fake_redis):
        """Should return False when initial GET fails."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            mock_get_response = Mock()
            mock_get_response.status_code = 500

            mock_client.get.return_value = mock_get_response

            result = await create_or_update_magic_word(
                "new_word", "admin_token", fake_redis
            )

            assert result is False
