from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo


KST = ZoneInfo("Asia/Seoul")


def is_in_quiet_hours(quiet_start_hour: int, quiet_end_hour: int, now: datetime | None = None) -> bool:
    current = now.astimezone(KST) if now else datetime.now(KST)
    hour = current.hour
    if quiet_start_hour == quiet_end_hour:
        return False
    if quiet_start_hour < quiet_end_hour:
        return quiet_start_hour <= hour < quiet_end_hour
    return hour >= quiet_start_hour or hour < quiet_end_hour

