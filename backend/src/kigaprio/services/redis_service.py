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
