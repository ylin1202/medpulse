import json
import os
import redis

# Initialize dedicated Redis client for caching layer
redis_cache = redis.StrictRedis(
    host=os.getenv("REDIS_HOST", "localhost"),
    port=int(os.getenv("REDIS_PORT", 6379)),
    db=int(os.getenv("DB_REDIS", 0)),
    decode_responses=True
)


class CacheService:
    """Universal Redis query caching and distributed state management service."""

    @staticmethod
    def get_client() -> redis.StrictRedis:
        """Provide native Redis client instance for specialized operations (e.g., OTP codes, blocklists)."""
        return redis_cache

    @staticmethod
    def get(key):
        """
        Retrieve cached value and deserialize JSON payload into native Python dictionaries/lists.
        Fails silently to prevent caching outages from breaking primary database queries.
        """
        try:
            data = redis_cache.get(key)
            if data:
                return json.loads(data)
            return None
        except Exception:
            # Defensive fallback: cache failure should degrade gracefully without interrupting business logic
            return None

    @staticmethod
    def set(key, value, expire=600):
        """
        Serialize payload to JSON and write to Redis with a configurable TTL (default: 600s / 10 mins).
        """
        try:
            json_data = json.dumps(value)
            redis_cache.set(key, json_data, ex=expire)
        except Exception:
            pass

    @staticmethod
    def delete_pattern(pattern):
        """Batch invalidate cache entries matching the specified wildcard pattern."""
        try:
            keys = redis_cache.keys(pattern)
            if keys:
                redis_cache.delete(*keys)
        except Exception:
            pass