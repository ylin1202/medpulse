import os
from flask import jsonify
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Initialize Limiter using client IP as the rate-limiting key identifier
limiter = Limiter(
    key_func=get_remote_address,
    # Configure Redis instance as the distributed rate-limit storage backend
    storage_uri=f"redis://{os.getenv('REDIS_HOST', 'localhost')}:{os.getenv('REDIS_PORT', 6379)}/{os.getenv('DB_REDIS', 0)}",
    # Global default rate limits applied to endpoints without explicit overrides
    default_limits=["100 per minute", "2000 per hour"]
)