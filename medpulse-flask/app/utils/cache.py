import json
import os
import redis

# ⚡ 初始化快取專用的 Redis Client
redis_cache = redis.StrictRedis(
    host=os.getenv("REDIS_HOST", "localhost"),
    port=int(os.getenv("REDIS_PORT", 6379)),
    db=int(os.getenv("DB_REDIS", 0)),
    decode_responses=True
)

class CacheService:
    """通用 Redis 查詢快取服務"""

    @staticmethod
    def get(key):
        """讀取快取，自動將 JSON 字串轉回 Python 字典/列表"""
        try:
            data = redis_cache.get(key)
            if data:
                return json.loads(data)
            return None
        except Exception:
            # 防禦性設計：即使 Redis 掛了，也不要影響主業務查詢
            return None

    @staticmethod
    def set(key, value, expire=600):
        """寫入快取，將資料序列化為 JSON，預設存活 10 分鐘 (600秒)"""
        try:
            json_data = json.dumps(value)
            redis_cache.set(key, json_data, ex=expire)
        except Exception:
            pass

    @staticmethod
    def delete_pattern(pattern):
        """根據 Pattern 批量刪除快取 (未來後台如果有更新藥品資料時可以用)"""
        try:
            keys = redis_cache.keys(pattern)
            if keys:
                redis_cache.delete(*keys)
        except Exception:
            pass