import httpx
from app.config import BINANCE_BASE_URL

class BinanceClient:

    async def get_klines(
        self,
        symbol: str,
        interval: str,
        limit: int = 500
    ):
        url = f"{BINANCE_BASE_URL}/api/v3/klines"
        params = {
            "symbol": symbol.upper(),
            "interval": interval,
            "limit": limit
        }

        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            return resp.json()
