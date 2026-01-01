from datetime import datetime, timedelta
from typing import Tuple

SUPPORTED_INTERVALS = {
    "1m": timedelta(minutes=1),
    "3m": timedelta(minutes=3),
    "5m": timedelta(minutes=5),
    "15m": timedelta(minutes=15),
    "30m": timedelta(minutes=30),
    "1h": timedelta(hours=1),
    "2h": timedelta(hours=2),
    "4h": timedelta(hours=4),
    "6h": timedelta(hours=6),
    "8h": timedelta(hours=8),
    "12h": timedelta(hours=12),
    "1d": timedelta(days=1),
    "3d": timedelta(days=3),
    "1w": timedelta(weeks=1),
    "1M": timedelta(days=30),
}


def is_supported_interval(interval: str) -> bool:
    """
    Kiểm tra interval có được Binance hỗ trợ không
    """
    return interval in SUPPORTED_INTERVALS


def ms_to_datetime(ms: int) -> datetime:
    """
    Convert timestamp milliseconds → datetime
    """
    return datetime.utcfromtimestamp(ms / 1000)


def datetime_to_ms(dt: datetime) -> int:
    """
    Convert datetime → milliseconds
    """
    return int(dt.timestamp() * 1000)


def get_time_range(
    interval: str,
    limit: int
) -> Tuple[int, int]:
    """
    Tính startTime và endTime (ms) dựa vào interval & limit

    Dùng khi:
    - Lấy dữ liệu theo khoảng thời gian
    - Phân trang lịch sử giá

    Ví dụ:
    interval = 1m, limit = 60
    → 60 phút gần nhất
    """
    if interval not in SUPPORTED_INTERVALS:
        raise ValueError(f"Unsupported interval: {interval}")

    now = datetime.utcnow()
    delta = SUPPORTED_INTERVALS[interval] * limit

    start_time = now - delta
    end_time = now

    return datetime_to_ms(start_time), datetime_to_ms(end_time)
