from pathlib import Path

import redis

# Redis connection pool
redis_pass_path = Path("/run/secrets/redis_pass")
if not redis_pass_path.exists():
    raise ValueError("Missing redis password!!! Please set as secret.")
REDIS_PASS = redis_pass_path.read_text().strip()
REDIS_URL = f"redis://:{REDIS_PASS}@redis:6379"
redis_pool = None


async def get_redis() -> redis.Redis:
    """Get Redis connection from pool"""
    global redis_pool
    if redis_pool is None:
        redis_pool = redis.ConnectionPool.from_url(
            REDIS_URL, decode_responses=True, max_connections=10
        )
    return redis.Redis(connection_pool=redis_pool)
