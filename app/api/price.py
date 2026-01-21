from fastapi import APIRouter, Query, HTTPException
from app.services.binance_client import BinanceClient
from app.repositories.price_cache import PriceCacheRepository
from app.repositories.candle_repository import CandleRepository
from app.models.candle import Candle, CandleResponse
from app.utils.time import is_supported_interval
from app.services.coingecko_service import CoinGeckoService
import httpx

router = APIRouter(prefix="/prices", tags=["Prices"])

binance = BinanceClient()
cache = PriceCacheRepository()
candle_repo = CandleRepository()
coingecko = CoinGeckoService()

@router.get("/history", response_model=CandleResponse)
async def get_price_history(
    symbol: str = Query(..., example="BTCUSDT"),
    interval: str = Query(..., example="1m"),
    limit: int = Query(None, le=2000)
):
    """
    Get historical price candles from TimescaleDB.
    Falls back to Binance API if symbol not found in DB.
    """
    if not is_supported_interval(interval):
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported interval: {interval}"
        )

    # Auto-calculate optimal limit based on interval if not provided
    if limit is None:
        limit_map = {
            "1m": 1000,  # ~16.7 hours
            "5m": 864,   # 3 days
            "15m": 672,  # 1 week
            "1h": 720,   # 30 days
            "4h": 540,   # 90 days
            "1d": 365,   # 1 year
            "1w": 156,   # 3 years
        }
        limit = limit_map.get(interval, 500)

    # Check cache first
    cached = await cache.get(symbol, interval)
    if cached:
        return cached

    try:
        # Try to get from TimescaleDB first
        candles_data = await candle_repo.get_candles(symbol, interval, limit)
        
        if candles_data:
            # Convert to Candle models
            candles = [
                Candle(
                    open_time=c["open_time"],
                    open=c["open"],
                    high=c["high"],
                    low=c["low"],
                    close=c["close"],
                    volume=c["volume"],
                    close_time=c["close_time"]
                )
                for c in candles_data
            ]
            
            response = CandleResponse(
                symbol=symbol.upper(),
                interval=interval,
                candles=candles
            ).dict()
            
            # Dynamic TTL based on interval (shorter intervals = shorter cache)
            ttl_map = {
                "1m": 5,    # 5 seconds - very fresh data
                "5m": 10,   # 10 seconds
                "15m": 30,  # 30 seconds
                "1h": 60,   # 1 minute
                "4h": 300,  # 5 minutes
                "1d": 600,  # 10 minutes
                "1w": 1800, # 30 minutes
            }
            ttl = ttl_map.get(interval, 60)
            
            # Cache the result with dynamic TTL
            await cache.set(symbol, interval, response, ttl)
            
            return response
            
    except Exception as e:
        print(f"Error fetching from DB: {e}", flush=True)
        # Fall through to Binance API fallback
    
    # Fallback to Binance API if not in DB or error
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

    # Dynamic TTL based on interval
    ttl_map = {
        "1m": 5, "5m": 10, "15m": 30, "1h": 60,
        "4h": 300, "1d": 600, "1w": 1800,
    }
    ttl = ttl_map.get(interval, 60)
    
    await cache.set(symbol, interval, response, ttl)

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

@router.get("/current-candle")
async def get_current_candle(
    symbol: str = Query(..., example="BTCUSDT"),
    interval: str = Query(..., example="5m")
):
    """
    Get current open candle OHLC from Redis cache.
    This provides the accumulated state of the current incomplete candle.
    """
    try:
        # Try to get from Redis first
        redis_key = f"current_candle:{symbol}:{interval}"
        current_candle = await cache.redis.get(redis_key)
        
        if current_candle:
            import json
            return json.loads(current_candle)
        
        # If not in Redis, return None (frontend will handle)
        return None
        
    except Exception as e:
        print(f"Error fetching current candle: {e}", flush=True)
        return None


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
