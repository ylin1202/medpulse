from functools import wraps
import hashlib
import json
import logging
from typing import Any, Callable, Optional
import redis.asyncio as aioredis

logger = logging.getLogger(__name__)


def redis_safe_fallback(default_return: Any = None):
    """Decorator to catch Redis connection exceptions and gracefully degrade operations."""
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                logger.warning(f"[Redis Degradation] '{func.__name__}' failed: {e}. Bypassing protection safely.")
                return default_return
        return wrapper
    return decorator


class RedisCacheService:
    """Service handling distributed query caching, key hashing, and sliding-window rate limiting."""

    def __init__(self, redis_client: aioredis.Redis):
        self.redis = redis_client

    @staticmethod
    def generate_cache_key(prefix: str, content: str) -> str:
        """Generate a deterministic SHA-256 hashed cache key for arbitrary text payloads."""
        hashed = hashlib.sha256(content.strip().encode("utf-8")).hexdigest()
        return f"{prefix}:{hashed}"

    @redis_safe_fallback(default_return=None)
    async def get_json(self, key: str) -> Optional[dict]:
        """Retrieve and deserialize a JSON-encoded value from Redis."""
        cached_data = await self.redis.get(key)
        return json.loads(cached_data) if cached_data else None

    @redis_safe_fallback(default_return=False)
    async def set_json(self, key: str, value: Any, ttl: int = 3600) -> bool:
        """Serialize a Python dictionary/list to JSON and store it in Redis with an expiration TTL."""
        await self.redis.setex(key, ttl, json.dumps(value))
        return True

    @redis_safe_fallback(default_return=False)
    async def is_rate_limited(self, key: str, limit: int, window: int) -> bool:
        """
        Check if the incoming request exceeds the configured threshold using an atomic increment counter.
        Returns True if the rate limit is exceeded, False otherwise.
        """
        current = await self.redis.incr(key)
        if current == 1:
            await self.redis.expire(key, window)
        return current > limit