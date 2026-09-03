import json
import redis.asyncio as redis
from loguru import logger
from typing import Optional, Any
from ..core.config import settings

class CacheService:
    def __init__(self):
        self.redis_client = None

    async def connect(self):
        try:
            self.redis_client = await redis.from_url(
                settings.redis_url,
                decode_responses=True,
                encoding="utf-8"
            )

            await self.redis_client.ping()
            logger.info("Redis connected")
            return self.redis_client
        except Exception as e:
            logger.error(f"Redis connection error: {e}")
            self.redis_client = None
            return None


    async def get(self, key: str) ->Optional[str]:
        if not self.redis_client:
            return None
        try:
            value = await self.redis_client.get(key)
            return value
        except Exception as e:
            logger.warning(f"Redis get error: {e}")

    async def set(self, key: str, value: Any, ttl: int = None) -> bool:
        if not self.redis_client:
            return False
        try:
            ttl = ttl or settings.cache_ttl
            if isinstance(value,(dict, list)):
                value = json.dumps(value, default=str)
            await self.redis_client.setex(key, ttl, value)
            return True
        except Exception as e:
            logger.warning(f"Redis set error: {e}")
            return False

    async def delete(self, key:str) -> bool:
        if not self.redis_client:
            return False
        try:
            await self.redis_client.delete(key)
            return True
        except Exception as e:
            logger.warning(f"Redis delete error: {e}")
            return False

    async def close(self):
        if self.redis_client:
            await self.redis_client.close()

cache_service = CacheService()