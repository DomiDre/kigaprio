import os
from pathlib import Path
from urllib.parse import urlparse, urlunparse

import redis
from redis.exceptions import ConnectionError, TimeoutError

from kigaprio.middleware.metrics import (
    update_redis_info_metrics,
    update_redis_pool_metrics,
)


class RedisService:
    """Redis connection service with automatic password injection"""

    def __init__(self):
        self._pool: redis.ConnectionPool | None = None
        self._redis_url: str | None = None

    def _build_redis_url(self) -> str:
        """Build Redis URL with password from secret file"""
        # Read password from secret
        redis_pass_path = Path("/run/secrets/redis_pass")
        if not redis_pass_path.exists():
            raise ValueError("Missing redis password! Please set as secret.")
        password = redis_pass_path.read_text().strip()

        # Get base URL from environment
        base_url = os.getenv("REDIS_URL", "redis://redis:6379")

        # Parse and inject password
        parsed = urlparse(base_url)

        # Build new netloc with password
        if password:
            netloc = f":{password}@{parsed.hostname}"
            if parsed.port:
                netloc += f":{parsed.port}"
        else:
            netloc = parsed.netloc

        # Reconstruct URL with password
        redis_url = urlunparse(
            (
                parsed.scheme,
                netloc,
                parsed.path,
                parsed.params,
                parsed.query,
                parsed.fragment,
            )
        )

        return redis_url

    @property
    def redis_url(self) -> str:
        """Lazy-build Redis URL on first access"""
        if self._redis_url is None:
            self._redis_url = self._build_redis_url()
        return self._redis_url

    @property
    def pool(self) -> redis.ConnectionPool:
        """Lazy-initialize connection pool"""
        if self._pool is None:
            self._pool = redis.ConnectionPool.from_url(
                self.redis_url,
                decode_responses=True,
                max_connections=10,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
                health_check_interval=30,
            )
        return self._pool

    def get_client(self) -> redis.Redis:
        """Get Redis client from pool"""
        return redis.Redis(connection_pool=self.pool)

    def health_check(self) -> bool:  # Remove async
        """Check Redis connection health"""
        try:
            client: redis.Redis = self.get_client()
            result = client.ping()
            return bool(result)
        except (ConnectionError, TimeoutError) as e:
            print(f"Redis health check failed: {e}")
            return False

    def get_pool_stats(self) -> dict[str, int]:
        """Get Redis connection pool statistics"""
        if not self._pool:
            return {
                "active": 0,
                "available": 0,
                "max": 0,
            }

        # Get pool statistics
        # Note: redis-py doesn't directly expose these, but we can infer
        max_connections = self._pool.max_connections

        # Active connections are those checked out from the pool
        # Available = max - active (approximation)
        # This is a best-effort metric since redis-py doesn't expose exact counts

        return {
            "active": 0,  # redis-py doesn't expose this directly
            "available": max_connections,  # Assume all available if we can't count
            "max": max_connections,
        }

    def get_redis_info(self) -> dict[str, int]:
        """Get Redis INFO metrics"""
        try:
            client: redis.Redis = self.get_client()
            # Type hint: info() returns Dict[str, Any]
            info: dict[str, int | str] = client.info("memory")  # type: ignore
            stats: dict[str, int | str] = client.info("stats")  # type: ignore

            # Parse memory info - cast to int
            memory_used = int(info.get("used_memory", 0))
            memory_max = int(info.get("maxmemory", 0))

            # Parse client info
            connected_clients = int(stats.get("connected_clients", 0))

            return {
                "memory_used": memory_used,
                "memory_max": memory_max,
                "connected_clients": connected_clients,
            }
        except Exception as e:
            print(f"Failed to get Redis INFO: {e}")
            return {
                "memory_used": 0,
                "memory_max": 0,
                "connected_clients": 0,
            }

    def close(self):
        """Close connection pool"""
        if self._pool:
            self._pool.disconnect()
            self._pool = None


# Global instance
_redis_service = RedisService()


def get_redis() -> redis.Redis:  # Remove async
    """Get Redis connection from pool"""
    return _redis_service.get_client()


def redis_health_check() -> bool:  # Remove async
    """Check if Redis is healthy"""
    return _redis_service.health_check()  # Remove await


def close_redis():
    """Close Redis connections (call on shutdown)"""
    _redis_service.close()


def update_redis_metrics():
    """Update Redis metrics (call periodically from background task)"""
    try:
        # Import here to avoid circular dependency

        # Get pool stats
        pool_stats = _redis_service.get_pool_stats()
        update_redis_pool_metrics(
            active=pool_stats["active"],
            available=pool_stats["available"],
            max_connections=pool_stats["max"],
        )

        # Get Redis INFO stats
        info_stats = _redis_service.get_redis_info()
        update_redis_info_metrics(
            memory_used=info_stats["memory_used"],
            memory_max=info_stats["memory_max"],
            connected_clients=info_stats["connected_clients"],
        )
    except Exception as e:
        print(f"Failed to update Redis metrics: {e}")
