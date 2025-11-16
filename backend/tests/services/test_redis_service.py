"""
Tests for Redis service.

Tests cover:
- RedisService connection pool management
- URL building with password injection
- Health checks
- Pool statistics
- Redis INFO metrics
"""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from redis.exceptions import ConnectionError, TimeoutError

from priotag.services.redis_service import (
    RedisService,
    close_redis,
    get_redis,
    redis_health_check,
    update_redis_metrics,
)


@pytest.mark.unit
class TestRedisService:
    """Test RedisService class."""

    @patch("pathlib.Path.exists", return_value=True)
    @patch("pathlib.Path.read_text", return_value="test_password\n")
    def test_build_redis_url_with_password(self, mock_read, mock_exists):
        """Should build Redis URL with password from secret file."""
        service = RedisService()

        with patch.dict("os.environ", {"REDIS_URL": "redis://redis:6379"}):
            url = service._build_redis_url()

            assert "test_password" in url
            assert url.startswith("redis://:test_password@redis:6379")

    @patch("pathlib.Path.exists", return_value=False)
    def test_build_redis_url_missing_password_raises(self, mock_exists):
        """Should raise ValueError when password file is missing."""
        service = RedisService()

        with pytest.raises(ValueError) as exc_info:
            service._build_redis_url()

        assert "Missing redis password" in str(exc_info.value)

    @patch("pathlib.Path.exists", return_value=True)
    @patch("pathlib.Path.read_text", return_value="pwd123")
    def test_redis_url_property_lazy_builds(self, mock_read, mock_exists):
        """Should lazy-build Redis URL on first access."""
        service = RedisService()

        # URL should be None initially
        assert service._redis_url is None

        with patch.dict("os.environ", {"REDIS_URL": "redis://localhost:6379"}):
            url = service.redis_url

            # Should build and cache the URL
            assert service._redis_url is not None
            assert "pwd123" in url

    @patch("pathlib.Path.exists", return_value=True)
    @patch("pathlib.Path.read_text", return_value="pwd123")
    def test_redis_url_property_caches_result(self, mock_read, mock_exists):
        """Should cache Redis URL after first build."""
        service = RedisService()

        with patch.dict("os.environ", {"REDIS_URL": "redis://localhost:6379"}):
            url1 = service.redis_url
            url2 = service.redis_url

            assert url1 == url2
            # Should only read password once
            assert mock_read.call_count == 1

    @patch("pathlib.Path.exists", return_value=True)
    @patch("pathlib.Path.read_text", return_value="pwd")
    @patch("redis.BlockingConnectionPool")
    def test_pool_property_creates_connection_pool(
        self, mock_pool_class, mock_read, mock_exists
    ):
        """Should create BlockingConnectionPool with correct settings."""
        service = RedisService()

        with patch.dict("os.environ", {"REDIS_URL": "redis://redis:6379/0"}):
            _ = service.pool

            # Should have created pool
            mock_pool_class.assert_called_once()
            call_kwargs = mock_pool_class.call_args.kwargs

            assert call_kwargs["host"] == "redis"
            assert call_kwargs["port"] == 6379
            assert call_kwargs["password"] == "pwd"
            assert call_kwargs["db"] == 0
            assert call_kwargs["max_connections"] == 10

    @patch("pathlib.Path.exists", return_value=True)
    @patch("pathlib.Path.read_text", return_value="pwd")
    @patch("redis.BlockingConnectionPool")
    def test_pool_property_lazy_initializes(
        self, mock_pool_class, mock_read, mock_exists
    ):
        """Should lazy-initialize pool on first access."""
        service = RedisService()

        # Pool should be None initially
        assert service._pool is None

        with patch.dict("os.environ", {"REDIS_URL": "redis://redis:6379"}):
            pool = service.pool

            # Should create and cache pool
            assert service._pool is not None
            assert pool == service._pool

    @patch("pathlib.Path.exists", return_value=True)
    @patch("pathlib.Path.read_text", return_value="pwd")
    @patch("redis.BlockingConnectionPool")
    @patch("redis.Redis")
    def test_get_client_returns_redis_instance(
        self, mock_redis_class, mock_pool_class, mock_read, mock_exists
    ):
        """Should return Redis client from pool."""
        service = RedisService()

        with patch.dict("os.environ", {"REDIS_URL": "redis://redis:6379"}):
            client = service.get_client()

            # Should have created Redis client with pool
            mock_redis_class.assert_called_once()
            call_kwargs = mock_redis_class.call_args.kwargs
            assert "connection_pool" in call_kwargs

    @patch("pathlib.Path.exists", return_value=True)
    @patch("pathlib.Path.read_text", return_value="pwd")
    @patch("redis.BlockingConnectionPool")
    def test_health_check_success(self, mock_pool_class, mock_read, mock_exists):
        """Should return True when Redis responds to ping."""
        service = RedisService()

        with patch.dict("os.environ", {"REDIS_URL": "redis://redis:6379"}):
            with patch.object(service, "get_client") as mock_get_client:
                mock_client = Mock()
                mock_client.ping.return_value = True
                mock_get_client.return_value = mock_client

                result = service.health_check()

                assert result is True
                mock_client.ping.assert_called_once()

    @patch("pathlib.Path.exists", return_value=True)
    @patch("pathlib.Path.read_text", return_value="pwd")
    @patch("redis.BlockingConnectionPool")
    def test_health_check_connection_error(
        self, mock_pool_class, mock_read, mock_exists
    ):
        """Should return False on connection error."""
        service = RedisService()

        with patch.dict("os.environ", {"REDIS_URL": "redis://redis:6379"}):
            with patch.object(service, "get_client") as mock_get_client:
                mock_client = Mock()
                mock_client.ping.side_effect = ConnectionError("Connection failed")
                mock_get_client.return_value = mock_client

                result = service.health_check()

                assert result is False

    @patch("pathlib.Path.exists", return_value=True)
    @patch("pathlib.Path.read_text", return_value="pwd")
    @patch("redis.BlockingConnectionPool")
    def test_health_check_timeout_error(self, mock_pool_class, mock_read, mock_exists):
        """Should return False on timeout error."""
        service = RedisService()

        with patch.dict("os.environ", {"REDIS_URL": "redis://redis:6379"}):
            with patch.object(service, "get_client") as mock_get_client:
                mock_client = Mock()
                mock_client.ping.side_effect = TimeoutError("Timeout")
                mock_get_client.return_value = mock_client

                result = service.health_check()

                assert result is False

    def test_get_pool_stats_no_pool(self):
        """Should return zero stats when pool not initialized."""
        service = RedisService()

        stats = service.get_pool_stats()

        assert stats["active"] == 0
        assert stats["available"] == 0
        assert stats["max"] == 0

    @patch("pathlib.Path.exists", return_value=True)
    @patch("pathlib.Path.read_text", return_value="pwd")
    @patch("redis.BlockingConnectionPool")
    def test_get_pool_stats_with_pool(self, mock_pool_class, mock_read, mock_exists):
        """Should return pool statistics when pool exists."""
        service = RedisService()

        with patch.dict("os.environ", {"REDIS_URL": "redis://redis:6379"}):
            # Create mock pool
            mock_pool = Mock()
            mock_pool.max_connections = 10
            mock_pool._in_use_connections = {Mock(), Mock()}  # 2 active
            mock_pool.pool = Mock()
            mock_pool.pool.qsize.return_value = 5  # 5 available

            service._pool = mock_pool

            stats = service.get_pool_stats()

            assert stats["max"] == 10
            assert stats["active"] == 2
            assert stats["available"] == 5

    @patch("pathlib.Path.exists", return_value=True)
    @patch("pathlib.Path.read_text", return_value="pwd")
    @patch("redis.BlockingConnectionPool")
    def test_get_pool_stats_fallback_on_error(
        self, mock_pool_class, mock_read, mock_exists
    ):
        """Should use pessimistic fallback on error."""
        service = RedisService()

        with patch.dict("os.environ", {"REDIS_URL": "redis://redis:6379"}):
            # Create mock pool that raises error
            mock_pool = Mock()
            mock_pool.max_connections = 10
            mock_pool.pool.qsize.side_effect = Exception("Error")

            service._pool = mock_pool

            stats = service.get_pool_stats()

            # Should assume pool is exhausted
            assert stats["max"] == 10
            assert stats["active"] == 10
            assert stats["available"] == 0

    @patch("pathlib.Path.exists", return_value=True)
    @patch("pathlib.Path.read_text", return_value="pwd")
    @patch("redis.BlockingConnectionPool")
    def test_get_redis_info_success(self, mock_pool_class, mock_read, mock_exists):
        """Should return Redis INFO metrics."""
        service = RedisService()

        with patch.dict("os.environ", {"REDIS_URL": "redis://redis:6379"}):
            with patch.object(service, "get_client") as mock_get_client:
                mock_client = Mock()
                mock_client.info.side_effect = [
                    {"used_memory": 1024000, "maxmemory": 10240000},  # memory
                    {"connected_clients": 5},  # stats
                ]
                mock_get_client.return_value = mock_client

                info = service.get_redis_info()

                assert info["memory_used"] == 1024000
                assert info["memory_max"] == 10240000
                assert info["connected_clients"] == 5

    @patch("pathlib.Path.exists", return_value=True)
    @patch("pathlib.Path.read_text", return_value="pwd")
    @patch("redis.BlockingConnectionPool")
    def test_get_redis_info_failure(self, mock_pool_class, mock_read, mock_exists):
        """Should return zeros on failure."""
        service = RedisService()

        with patch.dict("os.environ", {"REDIS_URL": "redis://redis:6379"}):
            with patch.object(service, "get_client") as mock_get_client:
                mock_client = Mock()
                mock_client.info.side_effect = Exception("Connection failed")
                mock_get_client.return_value = mock_client

                info = service.get_redis_info()

                assert info["memory_used"] == 0
                assert info["memory_max"] == 0
                assert info["connected_clients"] == 0

    @patch("pathlib.Path.exists", return_value=True)
    @patch("pathlib.Path.read_text", return_value="pwd")
    @patch("redis.BlockingConnectionPool")
    def test_close_disconnects_pool(self, mock_pool_class, mock_read, mock_exists):
        """Should disconnect pool on close."""
        service = RedisService()

        with patch.dict("os.environ", {"REDIS_URL": "redis://redis:6379"}):
            # Initialize pool
            _ = service.pool
            mock_pool = service._pool

            # Close
            service.close()

            # Should disconnect and clear pool
            mock_pool.disconnect.assert_called_once()
            assert service._pool is None


@pytest.mark.unit
class TestModuleFunctions:
    """Test module-level functions."""

    @patch("priotag.services.redis_service._redis_service")
    def test_get_redis(self, mock_service):
        """Should call get_client on global service."""
        mock_client = Mock()
        mock_service.get_client.return_value = mock_client

        result = get_redis()

        assert result == mock_client
        mock_service.get_client.assert_called_once()

    @patch("priotag.services.redis_service._redis_service")
    def test_redis_health_check(self, mock_service):
        """Should call health_check on global service."""
        mock_service.health_check.return_value = True

        result = redis_health_check()

        assert result is True
        mock_service.health_check.assert_called_once()

    @patch("priotag.services.redis_service._redis_service")
    def test_close_redis(self, mock_service):
        """Should call close on global service."""
        close_redis()

        mock_service.close.assert_called_once()

    @patch("priotag.services.redis_service._redis_service")
    @patch("priotag.services.redis_service.update_redis_pool_metrics")
    @patch("priotag.services.redis_service.update_redis_info_metrics")
    def test_update_redis_metrics(
        self, mock_info_metrics, mock_pool_metrics, mock_service
    ):
        """Should update both pool and info metrics."""
        mock_service.get_pool_stats.return_value = {
            "active": 3,
            "available": 7,
            "max": 10,
        }
        mock_service.get_redis_info.return_value = {
            "memory_used": 1024,
            "memory_max": 10240,
            "connected_clients": 5,
        }

        update_redis_metrics()

        # Should update pool metrics
        mock_pool_metrics.assert_called_once_with(
            active=3, available=7, max_connections=10
        )

        # Should update info metrics
        mock_info_metrics.assert_called_once_with(
            memory_used=1024, memory_max=10240, connected_clients=5
        )

    @patch("priotag.services.redis_service._redis_service")
    @patch("priotag.services.redis_service.update_redis_pool_metrics")
    def test_update_redis_metrics_handles_exception(
        self, mock_pool_metrics, mock_service
    ):
        """Should handle exceptions gracefully."""
        mock_service.get_pool_stats.side_effect = Exception("Error")

        # Should not raise
        update_redis_metrics()
