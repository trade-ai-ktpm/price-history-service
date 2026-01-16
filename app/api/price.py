from fastapi import APIRouter, Query, HTTPException
from app.services.binance_client import BinanceClient
from app.repositories.price_cache import PriceCacheRepository
from app.models.candle import Candle, CandleResponse
from app.utils.time import is_supported_interval
from app.services.coingecko_service import CoinGeckoService
import httpx

router = APIRouter(prefix="/prices", tags=["Prices"])

binance = BinanceClient()
cache = PriceCacheRepository()
coingecko = CoinGeckoService()

@router.get("/history", response_model=CandleResponse)
async def get_price_history(
    symbol: str = Query(..., example="BTCUSDT"),
    interval: str = Query(..., example="1m"),
    limit: int = Query(500, le=1000)
):
    if not is_supported_interval(interval):
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported interval: {interval}"
        )

    cached = await cache.get(symbol, interval)
    if cached:
        return cached

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

    await cache.set(symbol, interval, response)

    return response

@router.get("/ticker/{symbol}")
async def get_ticker_24h(symbol: str):
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://api.binance.com/api/v3/ticker/24hr?symbol={symbol}"
            )
            if response.status_code != 200:
                raise HTTPException(status_code=500, detail="Failed to fetch ticker")
            return response.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/market-cap/{symbol}")
async def get_market_cap(symbol: str):
    try:
        data = await coingecko.get_market_cap(symbol)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/market-overview")
async def get_market_overview():
    try:
        symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "ADAUSDT"]
        results = []
        
        async with httpx.AsyncClient() as client:
            for symbol in symbols:
                response = await client.get(
                    f"https://api.binance.com/api/v3/ticker/24hr?symbol={symbol}"
                )
                if response.status_code == 200:
                    ticker = response.json()
                    results.append({
                        "symbol": ticker["symbol"],
                        "price": float(ticker["lastPrice"]),
                        "change": float(ticker["priceChangePercent"])
                    })
        
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
