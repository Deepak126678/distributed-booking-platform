from typing import Optional, Tuple, Dict, Any
import json
import logging
from redis import RedisError
from app.utils.cache import redis_client

logger = logging.getLogger("booking-api")


def check_idempotency(key: str) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """
    Check if an Idempotency-Key has already been processed or is currently in progress.
    Returns:
        (is_in_progress, cached_response)
    """
    redis_key = f"idemp:{key}"
    try:
        val = redis_client.get(redis_key)
        if val is None:
            # Key not found; claim it with "IN_PROGRESS" state and a 2-minute lock timeout
            acquired = redis_client.set(redis_key, "IN_PROGRESS", nx=True, ex=120)
            if not acquired:
                # A concurrent thread claimed this key in the exact same millisecond
                return True, None
            return False, None
        
        if val == "IN_PROGRESS":
            return True, None
        
        # Already completed; return cached response
        return False, json.loads(val)
    except RedisError as e:
        logger.warning(f"[IDEMPOTENCY] Redis error (failing open): {e}")
        return False, None


def save_idempotent_response(key: str, response_data: Dict[str, Any], ttl: int = 86400) -> None:
    """Store the completed booking response under the Idempotency-Key with a 24-hour TTL."""
    redis_key = f"idemp:{key}"
    try:
        redis_client.setex(redis_key, ttl, json.dumps(response_data))
        logger.info(f"[IDEMPOTENCY] Saved response for key {key} (TTL={ttl}s)")
    except RedisError as e:
        logger.warning(f"[IDEMPOTENCY] Redis save error: {e}")


def clear_idempotency_key(key: str) -> None:
    """Clear idempotency key on failure so the client can safely retry."""
    redis_key = f"idemp:{key}"
    try:
        redis_client.delete(redis_key)
    except RedisError as e:
        logger.warning(f"[IDEMPOTENCY] Redis clear error: {e}")
