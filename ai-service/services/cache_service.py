import hashlib
import json
import logging
from typing import Any, Optional, Callable
from functools import wraps
import redis.asyncio as aioredis

logger = logging.getLogger(__name__)

def redis_safe_fallback(default_return: Any = None):
    """Redis 異常時捕獲並優雅降級的裝飾器"""
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
    def __init__(self, redis_client: aioredis.Redis):
        self.redis = redis_client

    @staticmethod
    def generate_cache_key(prefix: str, content: str) -> str:
        hashed = hashlib.sha256(content.strip().encode("utf-8")).hexdigest()
        return f"{prefix}:{hashed}"

    @redis_safe_fallback(default_return=None)
    async def get_json(self, key: str) -> Optional[dict]:
        cached_data = await self.redis.get(key)
        return json.loads(cached_data) if cached_data else None

    @redis_safe_fallback(default_return=False)
    async def set_json(self, key: str, value: Any, ttl: int = 3600) -> bool:
        await self.redis.setex(key, ttl, json.dumps(value))
        return True

    @redis_safe_fallback(default_return=False)
    async def is_rate_limited(self, key: str, limit: int, window: int) -> bool:
        current = await self.redis.incr(key)
        if current == 1:
            await self.redis.expire(key, window)
        return current > limit