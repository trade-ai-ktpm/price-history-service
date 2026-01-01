from pydantic import BaseModel
from typing import List

class Candle(BaseModel):
    open_time: int
    open: float
    high: float
    low: float
    close: float
    volume: float
    close_time: int

class CandleResponse(BaseModel):
    symbol: str
    interval: str
    candles: List[Candle]
