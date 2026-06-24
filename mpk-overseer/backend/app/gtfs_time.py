from __future__ import annotations

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

WARSAW = ZoneInfo("Europe/Warsaw")

GTFS_WEEKDAY_FIELDS = (
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
)


def parse_gtfs_time(time_str: str) -> int:
    hours, minutes, seconds = (int(part) for part in time_str.split(":"))
    return hours * 3600 + minutes * 60 + seconds


def to_epoch_utc(service_date: date, seconds_from_midnight: int) -> int:
    midnight = datetime(
        service_date.year,
        service_date.month,
        service_date.day,
        tzinfo=WARSAW,
    )
    return int(midnight.timestamp()) + seconds_from_midnight


def dates_in_window(start_ts: int, end_ts: int) -> list[date]:
    start_date = datetime.fromtimestamp(start_ts, WARSAW).date()
    end_date = datetime.fromtimestamp(end_ts, WARSAW).date()
    dates: list[date] = []
    current = start_date
    while current <= end_date:
        dates.append(current)
        current += timedelta(days=1)
    return dates


def pick_time(time_value: str | None, fallback: str | None) -> str | None:
    if time_value:
        return time_value
    return fallback
