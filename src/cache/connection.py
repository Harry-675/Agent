"""Redis cache connection management."""

import json
from typing import Any, Optional

import redis.asyncio as redis

from src.config import get_settings

settings = get_settings()


class RedisConnection:
    """Redis connection manager."""
    
    def __init__(self):
        self.redis_url = settings.redis_url
        self.default_ttl = settings.cache_ttl_seconds
        self._client: Optional[redis.Redis] = None
    
    async def connect(self):
        """Connect to Redis."""
        if self._client is None:
            self._client = await redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
    
    async def disconnect(self):
        """Disconnect from Redis."""
        if self._client:
            await self._client.close()
            self._client = None
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        if not self._client:
            await self.connect()
        
        value = await self._client.get(key)
        if value:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
        return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache with optional TTL."""
        if not self._client:
            await self.connect()
        
        ttl = ttl or self.default_ttl
        
        if isinstance(value, (dict, list)):
            value = json.dumps(value)
        
        return await self._client.setex(key, ttl, value)
    
    async def delete(self, key: str) -> bool:
        """Delete key from cache."""
        if not self._client:
            await self.connect()
        
        return await self._client.delete(key) > 0
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        if not self._client:
            await self.connect()
        
        return await self._client.exists(key) > 0
    
    async def invalidate_pattern(self, pattern: str) -> int:
        """Invalidate all keys matching pattern."""
        if not self._client:
            await self.connect()
        
        keys = []
        async for key in self._client.scan_iter(match=pattern):
            keys.append(key)
        
        if keys:
            return await self._client.delete(*keys)
        return 0


# Global Redis connection instance
_redis_connection: Optional[RedisConnection] = None


def get_redis() -> RedisConnection:
    """Get the global Redis connection instance."""
    global _redis_connection
    if _redis_connection is None:
        _redis_connection = RedisConnection()
    return _redis_connection
