"""
Repository for querying candle data from TimescaleDB
"""
from typing import List, Optional
from datetime import datetime
import time
from sqlalchemy import text
from app.database import async_session
from app.repositories.price_cache import PriceCacheRepository

# Global cache instance
cache = PriceCacheRepository()


class CandleRepository:
    """Repository for candle data operations"""
    
    # Map interval to table/view name
    TABLE_MAP = {
        "1m": "candle_data_1m",
        "5m": "candle_data_5m",
        "15m": "candle_data_15m",
        "1h": "candle_data_1h",
        "4h": "candle_data_4h",
        "1d": "candle_data_1d",
        "1w": "candle_data_1w",
    }
    
    async def get_coin_id(self, symbol: str) -> Optional[int]:
        """Get coin ID by symbol"""
        async with async_session() as session:
            result = await session.execute(
                text("SELECT id FROM coins WHERE symbol = :symbol"),
                {"symbol": symbol}
            )
            row = result.fetchone()
            return row.id if row else None
    
    def _aggregate_1m_candles(self, candles_1m: List[dict], interval: str, limit: int) -> List[dict]:
        """
        Aggregate 1m candles into higher timeframes in-memory
        Same logic as aggregator.py for consistency
        
        Args:
            candles_1m: List of 1m candles sorted by timestamp ASC
            interval: Target timeframe (5m, 15m, 1h, 4h, 1d, 1w)
            limit: Number of aggregated candles to return
            
        Returns:
            List of aggregated candles
        """
        from datetime import datetime, timezone
        
        TIMEFRAME_MINUTES = {
            "5m": 5, "15m": 15, "1h": 60, "4h": 240, "1d": 1440, "1w": 10080
        }
        
        interval_minutes = TIMEFRAME_MINUTES.get(interval)
        if not interval_minutes:
            return []
        
        # Group 1m candles by target timeframe bucket
        aggregated = {}
        
        for candle in candles_1m:
            # Get bucket start time for this interval
            timestamp_ms = int(candle['time']) * 1000
            bucket_start_ms = (timestamp_ms // (interval_minutes * 60 * 1000)) * (interval_minutes * 60 * 1000)
            bucket_start = bucket_start_ms // 1000  # Back to seconds
            
            if bucket_start not in aggregated:
                aggregated[bucket_start] = {
                    'time': bucket_start,
                    'open': candle['open'],
                    'high': candle['high'],
                    'low': candle['low'],
                    'close': candle['close'],
                    'volume': candle['volume']
                }
            else:
                agg = aggregated[bucket_start]
                agg['high'] = max(agg['high'], candle['high'])
                agg['low'] = min(agg['low'], candle['low'])
                agg['close'] = candle['close']  # Last close
                agg['volume'] += candle['volume']
        
        # Sort by time and return last N candles
        result = sorted(aggregated.values(), key=lambda x: x['time'])
        return result[-limit:] if len(result) > limit else result
    
    async def get_candles(
        self, 
        symbol: str, 
        interval: str, 
        limit: int = 500
    ) -> List[dict]:
        """
        Get historical candles from TimescaleDB
        
        Strategy:
        - For 1m: Query directly from candle_data_1m
        - For other timeframes: Query 1m candles and aggregate in-memory
          (Same logic as realtime aggregator for consistency)
        
        Args:
            symbol: Trading pair (e.g., BTCUSDT)
            interval: Candle interval (1m, 5m, 15m, 1h, 4h, 1d, 1w)
            limit: Number of candles to return
            
        Returns:
            List of candle dictionaries
        """
        # Get coin ID
        coin_id = await self.get_coin_id(symbol)
        if coin_id is None:
            return []
        
        # For non-1m intervals, query 1m candles and aggregate in-memory
        if interval != "1m":
            TIMEFRAME_MINUTES = {
                "5m": 5, "15m": 15, "1h": 60, "4h": 240, "1d": 1440, "1w": 10080
            }
            interval_minutes = TIMEFRAME_MINUTES.get(interval, 5)
            
            # Calculate how many 1m candles we need
            # Need: limit * interval_minutes (e.g., 500 5m candles = 2500 1m candles)
            required_1m_candles = limit * interval_minutes
            
            # Query 1m candles (closed candles only)
            async with async_session() as session:
                query = text("""
                    SELECT 
                        EXTRACT(EPOCH FROM timestamp)::bigint as time,
                        open, high, low, close, volume
                    FROM candle_data_1m
                    WHERE coin_id = :coin_id
                    ORDER BY timestamp DESC
                    LIMIT :limit
                """)
                
                result = await session.execute(query, {
                    "coin_id": coin_id,
                    "limit": required_1m_candles
                })
                
                rows = result.fetchall()
                
                candles_1m = []
                if rows:
                    # Convert to list of dicts and reverse (oldest first for aggregation)
                    candles_1m = [
                        {
                            'time': row.time,
                            'open': float(row.open),
                            'high': float(row.high),
                            'low': float(row.low),
                            'close': float(row.close),
                            'volume': float(row.volume)
                        }
                        for row in reversed(rows)
                    ]
                
                # MERGE current 1m candle from Redis
                # This provides complete data: historical (DB) + current (Redis)
                import json
                current_1m_key = f"current_candle:{symbol}:1m"
                current_1m_data = await cache.redis.get(current_1m_key)
                
                if current_1m_data:
                    try:
                        current_1m = json.loads(current_1m_data)
                        # Only append if not already in historical data (avoid duplicates)
                        current_time = current_1m['time']
                        if not any(c['time'] == current_time for c in candles_1m):
                            candles_1m.append({
                                'time': current_time,
                                'open': float(current_1m['open']),
                                'high': float(current_1m['high']),
                                'low': float(current_1m['low']),
                                'close': float(current_1m['close']),
                                'volume': float(current_1m['volume'])
                            })
                    except Exception as e:
                        print(f"Warning: Could not parse current 1m candle: {e}")
                
                if not candles_1m:
                    return []
                
                # Aggregate in-memory (historical candles only, no current)
                return self._aggregate_1m_candles(candles_1m, interval, limit)
        
        # For 1m interval, query directly
        async with async_session() as session:
            query = text("""
                SELECT 
                    EXTRACT(EPOCH FROM timestamp)::bigint as time,
                    open, high, low, close, volume
                FROM candle_data_1m
                WHERE coin_id = :coin_id
                ORDER BY timestamp DESC
                LIMIT :limit
            """)
            
            result = await session.execute(query, {
                "coin_id": coin_id,
                "limit": limit
            })
            
            rows = result.fetchall()
            
            # Convert to list of dicts and reverse (oldest first)
            candles = [
                {
                    'time': row.time,
                    'open': float(row.open),
                    'high': float(row.high),
                    'low': float(row.low),
                    'close': float(row.close),
                    'volume': float(row.volume)
                }
                for row in reversed(rows)
            ]
            
            # MERGE current 1m candle from Redis (same as higher timeframes above)
            import json
            current_1m_key = f"current_candle:{symbol}:1m"
            current_1m_data = await cache.redis.get(current_1m_key)
            
            if current_1m_data:
                try:
                    current_1m = json.loads(current_1m_data)
                    current_time = current_1m['time']
                    if not any(c['time'] == current_time for c in candles):
                        candles.append({
                            'time': current_time,
                            'open': float(current_1m['open']),
                            'high': float(current_1m['high']),
                            'low': float(current_1m['low']),
                            'close': float(current_1m['close']),
                            'volume': float(current_1m['volume'])
                        })
                except Exception as e:
                    print(f"Warning: Could not parse current 1m candle: {e}")
            
            return candles
