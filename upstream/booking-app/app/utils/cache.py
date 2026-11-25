from typing import Any, Optional, List
import json
import os
import logging
from redis import Redis, RedisError

from app.metrics import CACHE_HITS, CACHE_MISSES

logger = logging.getLogger("booking-api")

# Initialize Redis client (Internal Docker host: 'redis', Port: 6379)
redis_client = Redis(
    host=os.getenv("REDIS_HOST", "redis"),
    port=int(os.getenv("REDIS_PORT", "6379")),
    db=0,
    decode_responses=True,
    socket_timeout=1.5,           # Prevent blocking if Redis is slow
    socket_connect_timeout=1.5
)

# ----------------- Cache-Aside Helper Functions -----------------

def get_cached_units(skip: int, limit: int) -> Optional[List[dict]]:
    """Fetch cached units list from Redis. Returns None on cache miss or Redis failure (Fail-Open)."""
    key = f"units:all:{skip}:{limit}"
    try:
        data = redis_client.get(key)
        if data:
            CACHE_HITS.labels(cache_type="units").inc()
            logger.info(f"[CACHE HIT] Loaded units from Redis ({key})")
            return json.loads(data)
        
        CACHE_MISSES.labels(cache_type="units").inc()
        logger.info(f"[CACHE MISS] Key not found in Redis ({key})")
        return None
    except RedisError as e:
        logger.warning(f"[CACHE ERROR] Redis get failed (failing open to Postgres): {e}")
        return None


def set_cached_units(skip: int, limit: int, units_data: List[dict], ttl: int = 60) -> None:
    """Store serialized units in Redis with an expiration TTL (default: 60s)."""
    key = f"units:all:{skip}:{limit}"
    try:
        redis_client.setex(key, ttl, json.dumps(units_data))
        logger.info(f"[CACHE SET] Stored units in Redis with TTL={ttl}s ({key})")
    except RedisError as e:
        logger.warning(f"[CACHE ERROR] Redis set failed: {e}")


def invalidate_units_cache() -> None:
    """Delete all cached unit listings when a unit is created or modified."""
    try:
        keys = redis_client.keys("units:all:*")
        if keys:
            redis_client.delete(*keys)
            logger.info(f"[CACHE INVALIDATE] Cleared {len(keys)} unit cache keys")
    except RedisError as e:
        logger.warning(f"[CACHE ERROR] Redis cache invalidation failed: {e}")
