"""
Redis connection and caching utilities
"""
import redis.asyncio as redis
from typing import Optional, Any
import json
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)

# Global Redis connection
redis_client: Optional[redis.Redis] = None


async def init_redis() -> None:
    """Initialize Redis connection"""
    global redis_client
    try:
        redis_client = redis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True
        )
        # Test connection
        await redis_client.ping()
        logger.info("Redis connection established successfully")
    except Exception as e:
        logger.error(f"Failed to connect to Redis: {e}")
        raise


async def get_redis() -> redis.Redis:
    """Get Redis client instance"""
    if redis_client is None:
        raise RuntimeError("Redis not initialized")
    return redis_client


async def close_redis() -> None:
    """Close Redis connection"""
    if redis_client:
        await redis_client.close()
        logger.info("Redis connection closed")


class CacheService:
    """Redis caching service"""
    
    def __init__(self):
        self.default_ttl = settings.REDIS_CACHE_TTL
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        try:
            client = await get_redis()
            value = await client.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.error(f"Cache get error for key {key}: {e}")
            return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache"""
        try:
            client = await get_redis()
            ttl = ttl or self.default_ttl
            serialized_value = json.dumps(value, default=str)
            await client.setex(key, ttl, serialized_value)
            return True
        except Exception as e:
            logger.error(f"Cache set error for key {key}: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete key from cache"""
        try:
            client = await get_redis()
            await client.delete(key)
            return True
        except Exception as e:
            logger.error(f"Cache delete error for key {key}: {e}")
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache"""
        try:
            client = await get_redis()
            return await client.exists(key) > 0
        except Exception as e:
            logger.error(f"Cache exists error for key {key}: {e}")
            return False


# Global cache service instance
cache = CacheService()