from fastapi import APIRouter, Query, HTTPException
from app.services.binance_client import BinanceClient
from app.repositories.price_cache import PriceCacheRepository
from app.models.candle import Candle, CandleResponse
from app.utils.time import is_supported_interval

router = APIRouter(prefix="/prices", tags=["Prices"])

binance = BinanceClient()
cache = PriceCacheRepository()

@router.get("/history", response_model=CandleResponse)
async def get_price_history(
    symbol: str = Query(..., example="BTCUSDT"),
    interval: str = Query(..., example="1m"),
    limit: int = Query(500, le=1000)
):
    # 1. Validate input sớm nhất
    if not is_supported_interval(interval):
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported interval: {interval}"
        )

    # 2. Check cache
    cached = await cache.get(symbol, interval)
    if cached:
        return cached

    # 3. Fetch from Binance
    raw_klines = await binance.get_klines(symbol, interval, limit)

    candles = [
        Candle(
            open_time=k[0],
            open=float(k[1]),
            high=float(k[2]),
            low=float(k[3]),
            close=float(k[4]),
            volume=float(k[5]),
            close_time=k[6]
        )
        for k in raw_klines
    ]

    response = CandleResponse(
        symbol=symbol.upper(),
        interval=interval,
        candles=candles
    ).dict()

    # 3. Cache result
    await cache.set(symbol, interval, response)

    return response
