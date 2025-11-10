import os
from pathlib import Path
from urllib.parse import urlparse, urlunparse

import redis
from redis.exceptions import ConnectionError, TimeoutError

from priotag.middleware.metrics import (
    update_redis_info_metrics,
    update_redis_pool_metrics,
)


class RedisService:
    """Redis connection service with automatic password injection and accurate pool tracking"""

    def __init__(self):
        self._pool: redis.BlockingConnectionPool | None = None
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
    def pool(self) -> redis.BlockingConnectionPool:
        """Lazy-initialize blocking connection pool with accurate tracking"""
        if self._pool is None:
            parsed = urlparse(self.redis_url)

            # Use BlockingConnectionPool for better tracking and automatic blocking
            # when pool is exhausted (prevents silent failures)
            self._pool = redis.BlockingConnectionPool(
                host=parsed.hostname,
                port=parsed.port or 6379,
                password=parsed.password,
                db=int(parsed.path.lstrip("/")) if parsed.path else 0,
                decode_responses=True,
                max_connections=10,
                timeout=20,  # Timeout for waiting for a connection from pool
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
                health_check_interval=30,
            )
        return self._pool

    def get_client(self) -> redis.Redis:
        """Get Redis client from pool"""
        return redis.Redis(connection_pool=self.pool)

    def health_check(self) -> bool:
        """Check Redis connection health"""
        try:
            client: redis.Redis = self.get_client()
            result = client.ping()
            return bool(result)
        except (ConnectionError, TimeoutError) as e:
            print(f"Redis health check failed: {e}")
            return False

    def get_pool_stats(self) -> dict[str, int]:
        """Get Redis connection pool statistics

        BlockingConnectionPool provides accurate tracking through:
        - _available_connections: Queue of available connections
        - _in_use_connections: Set of connections currently in use
        """
        if not self._pool:
            return {
                "active": 0,
                "available": 0,
                "max": 0,
            }

        max_connections = self._pool.max_connections

        try:
            # BlockingConnectionPool has better internal tracking
            # _available_connections is a queue of connections ready to use
            pool_obj = self._pool.pool if hasattr(self._pool, "pool") else None

            if pool_obj is not None:
                # Get number of available connections in the pool
                available_count = pool_obj.qsize()
            else:
                # Fallback: try to access _available_connections directly
                available_count = len(getattr(self._pool, "_available_connections", []))

            # _in_use_connections tracks borrowed connections
            in_use: set = getattr(self._pool, "_in_use_connections", set())
            active_count = len(in_use)

            # Sanity check: active + available should not exceed max
            # (though it can be less if not all connections have been created yet)
            if active_count + available_count > max_connections:
                # Use created connections as source of truth
                created = getattr(self._pool, "_created_connections", 0)
                active_count = max(0, created - available_count)

        except Exception as e:
            # Fallback if internal API changes
            print(f"Warning: Could not get exact pool stats: {e}")
            # Make a pessimistic assumption - show pool as exhausted to be safe
            available_count = 0
            active_count = max_connections

        return {
            "active": active_count,
            "available": available_count,
            "max": max_connections,
        }

    def get_redis_info(self) -> dict[str, int]:
        """Get Redis INFO metrics"""
        try:
            client: redis.Redis = self.get_client()
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


def get_redis() -> redis.Redis:
    """Get Redis connection from pool"""
    return _redis_service.get_client()


def redis_health_check() -> bool:
    """Check if Redis is healthy"""
    return _redis_service.health_check()


def close_redis():
    """Close Redis connections (call on shutdown)"""
    _redis_service.close()


def update_redis_metrics():
    """Update Redis metrics (call periodically from background task)"""
    try:
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
