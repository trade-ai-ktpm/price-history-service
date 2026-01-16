import os

# Redis - Parse from REDIS_URL
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
if REDIS_URL.startswith("redis://"):
    redis_host_port = REDIS_URL.replace("redis://", "").split("/")[0]
    if ":" in redis_host_port:
        REDIS_HOST, port_str = redis_host_port.split(":")
        REDIS_PORT = int(port_str)
    else:
        REDIS_HOST = redis_host_port
        REDIS_PORT = 6379
else:
    REDIS_HOST = "localhost"
    REDIS_PORT = 6379

REDIS_DB = 0
BINANCE_BASE_URL = "https://api.binance.com/api/v3"
CACHE_TTL_SECONDS = 60

# Binance API
BINANCE_API_URL = os.getenv("BINANCE_BASE_URL", "https://api.binance.com")