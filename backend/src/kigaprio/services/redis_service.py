import os

import redis

# Redis connection pool
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379")
redis_pool = None


async def get_redis() -> redis.Redis:
    """Get Redis connection from pool"""
    global redis_pool
    if redis_pool is None:
        redis_pool = redis.ConnectionPool.from_url(
            REDIS_URL, decode_responses=True, max_connections=10
        )
    return redis.Redis(connection_pool=redis_pool)


def cache_admin_identity(identity: str, redis_client: redis.Redis):
    """Cache an identity as admin for faster future lookups"""
    admin_cache_key = f"known_admin:{identity}"
    # Cache for 30 days - adjust as needed
    redis_client.setex(admin_cache_key, 30 * 24 * 3600, "1")


def remove_admin_identity(identity: str, redis_client: redis.Redis):
    """Remove an identity from admin cache if it exists"""
    admin_cache_key = f"known_admin:{identity}"
    redis_client.delete(admin_cache_key)
