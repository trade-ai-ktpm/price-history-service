import httpx
from typing import Dict, Any
import asyncio
import logging
import redis.asyncio as redis
import json
from app.config import REDIS_HOST, REDIS_PORT, REDIS_DB

logger = logging.getLogger(__name__)

class CoinGeckoService:
    def __init__(self):
        self.base_url = "https://api.coingecko.com/api/v3"
        self.symbol_map = {
            "BTCUSDT": "bitcoin",
            "ETHUSDT": "ethereum",
            "BNBUSDT": "binancecoin",
            "SOLUSDT": "solana",
            "ADAUSDT": "cardano",
        }
        self.redis_client = None
        self.cache_ttl = 3600  # 1 hour cache

    async def _get_redis(self):
        if self.redis_client is None:
            self.redis_client = await redis.Redis(
                host=REDIS_HOST,
                port=REDIS_PORT,
                db=REDIS_DB,
                decode_responses=True
            )
        return self.redis_client

    async def get_market_cap(self, symbol: str) -> Dict[str, Any]:
        coin_id = self.symbol_map.get(symbol)
        if not coin_id:
            logger.warning(f"Unknown symbol: {symbol}")
            return {"symbol": symbol, "marketCap": None}

        # Check Redis cache first
        cache_key = f"market_cap:{symbol}"
        try:
            redis_client = await self._get_redis()
            cached = await redis_client.get(cache_key)
            if cached:
                logger.info(f"Market cap cache HIT for {symbol}")
                data = json.loads(cached)
                return {"symbol": symbol, "marketCap": data.get("marketCap")}
        except Exception as e:
            logger.error(f"Redis error: {e}")

        # Retry logic for rate limits
        max_retries = 3
        for attempt in range(max_retries):
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.get(
                        f"{self.base_url}/simple/price",
                        params={
                            "ids": coin_id,
                            "vs_currencies": "usd",
                            "include_market_cap": "true"
                        }
                    )
                    
                    if response.status_code == 429:  # Rate limit
                        if attempt < max_retries - 1:
                            wait_time = (attempt + 1) * 2
                            logger.warning(f"Rate limited, retrying in {wait_time}s...")
                            await asyncio.sleep(wait_time)
                            continue
                        logger.error(f"Rate limit exceeded for {symbol}")
                        return {"symbol": symbol, "marketCap": None}
                    
                    if response.status_code != 200:
                        logger.error(f"CoinGecko error {response.status_code} for {symbol}")
                        return {"symbol": symbol, "marketCap": None}
                    
                    data = response.json()
                    market_cap = data.get(coin_id, {}).get("usd_market_cap")
                    
                    if market_cap is None:
                        logger.warning(f"No market cap data for {symbol}")
                    else:
                        # Cache in Redis for 1 hour
                        try:
                            redis_client = await self._get_redis()
                            await redis_client.setex(
                                cache_key,
                                self.cache_ttl,
                                json.dumps({"marketCap": market_cap})
                            )
                            logger.info(f"Cached market cap for {symbol}")
                        except Exception as e:
                            logger.error(f"Failed to cache: {e}")
                    
                    return {
                        "symbol": symbol,
                        "marketCap": market_cap
                    }
                    
            except Exception as e:
                logger.error(f"Error fetching market cap for {symbol}: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(1)
                    continue
                return {"symbol": symbol, "marketCap": None}
        
        return {"symbol": symbol, "marketCap": None}
