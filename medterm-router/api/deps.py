from fastapi import Request, Depends
import asyncpg
import redis.asyncio as aioredis
from app.services.cache_service import RedisCacheService

async def get_db_pool(request: Request) -> asyncpg.Pool:
    """從 app.state 獲取資料庫連線池"""
    return request.app.state.db_pool

async def get_redis_client(request: Request) -> aioredis.Redis:
    """從 app.state 獲取 Redis Client"""
    return request.app.state.redis

async def get_cache_service(
    redis: aioredis.Redis = Depends(get_redis_client)
) -> RedisCacheService:
    """注入快取與限流服務實例"""
    return RedisCacheService(redis)