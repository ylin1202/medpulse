import os
from flask import jsonify
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# 初始化 Limiter，並設定以「使用者 IP」作為辨識基準 (get_remote_address)
limiter = Limiter(
    key_func=get_remote_address,
    # 預設儲存後端直接對接我們原本的 Redis 伺服器
    storage_uri=f"redis://{os.getenv('REDIS_HOST', 'localhost')}:{os.getenv('REDIS_PORT', 6379)}/{os.getenv('DB_REDIS', 0)}",
    
    # 全域的預設流量限制（如果個別路由沒設定，就套用這個）
    # 例如：每分鐘最多 100 次請求，每小時最多 2000 次
    default_limits=["100 per minute", "2000 per hour"]
)
