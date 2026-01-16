import httpx
from app.config import BINANCE_BASE_URL

class BinanceClient:

    async def get_klines(
        self,
        symbol: str,
        interval: str,
        limit: int = 500
    ):
        async with httpx.AsyncClient() as client:
            # BINANCE_BASE_URL already includes /api/v3
            url = f"{BINANCE_BASE_URL}/klines"
            params = {
                "symbol": symbol,
                "interval": interval,
                "limit": limit
            }
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            return resp.json()
