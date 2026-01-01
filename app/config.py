import os

BINANCE_BASE_URL = "https://api.binance.com"

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_DB = 0

CACHE_TTL_SECONDS = 60