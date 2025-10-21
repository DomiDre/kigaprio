import os
from pathlib import Path
from urllib.parse import urlparse, urlunparse

import redis
from redis.exceptions import ConnectionError, TimeoutError

from kigaprio.middleware.metrics import track_redis_error


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

    def close(self):
        """Close connection pool"""
        if self._pool:
            self._pool.disconnect()
            self._pool = None


# Global instance
_redis_service = RedisService()


def get_redis() -> redis.Redis:  # Remove async
    """Get Redis connection from pool"""
    try:
        return _redis_service.get_client()
    except Exception:
        track_redis_error()
        raise


def redis_health_check() -> bool:  # Remove async
    """Check if Redis is healthy"""
    return _redis_service.health_check()  # Remove await


def close_redis():
    """Close Redis connections (call on shutdown)"""
    _redis_service.close()
