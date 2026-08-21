import asyncpg
from fastapi import Depends, Request
import redis.asyncio as aioredis

from app.services.cache_service import RedisCacheService


async def get_db_pool(request: Request) -> asyncpg.Pool:
    """Retrieve the PostgreSQL connection pool from application state."""
    return request.app.state.db_pool


async def get_redis_client(request: Request) -> aioredis.Redis:
    """Retrieve the asynchronous Redis client instance from application state."""
    return request.app.state.redis


async def get_cache_service(
    redis: aioredis.Redis = Depends(get_redis_client)
) -> RedisCacheService:
    """Instantiate and inject the Redis caching and distributed rate-limiting service."""
    return RedisCacheService(redis)