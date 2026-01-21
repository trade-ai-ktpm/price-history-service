import os
from urllib.parse import urlparse

# Redis - Parse from REDIS_URL
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
parsed = urlparse(REDIS_URL)
REDIS_HOST = parsed.hostname or "localhost"
REDIS_PORT = parsed.port or 6379
REDIS_PASSWORD = parsed.password
REDIS_DB = 0
BINANCE_BASE_URL = "https://api.binance.com/api/v3"
CACHE_TTL_SECONDS = 60

# Database
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://aiuser:ngocphat@timescaledb-ai:5432/aidb")

# Binance API
BINANCE_API_URL = os.getenv("BINANCE_BASE_URL", "https://api.binance.com")