import json
import redis.asyncio as redis
from app.config import REDIS_HOST, REDIS_PORT, REDIS_DB, REDIS_PASSWORD

class PriceCacheRepository:

    def __init__(self):
        self.redis = redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            db=REDIS_DB,
            password=REDIS_PASSWORD,
            decode_responses=True
        )

    def _key(self, symbol: str, interval: str):
        return f"history:{symbol}:{interval}"

    async def get(self, symbol: str, interval: str):
        key = self._key(symbol, interval)
        data = await self.redis.get(key)
        if data:
            return json.loads(data)
        return None

    async def set(self, symbol: str, interval: str, value, ttl: int = None):
        key = self._key(symbol, interval)
        # Use provided ttl or default from config
        if ttl is None:
            from app.config import CACHE_TTL_SECONDS
            ttl = CACHE_TTL_SECONDS
        await self.redis.setex(
            key,
            ttl,
            json.dumps(value)
        )
