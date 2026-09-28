from __future__ import annotations

from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo


WEEKLY_WEEKDAY = 0  # Monday


def latest_due_boundary(now: datetime, frequency: str, digest_hour_local: int, zone: ZoneInfo) -> datetime:
    local_now = now.astimezone(zone)
    today_boundary = local_now.replace(hour=digest_hour_local, minute=0, second=0, microsecond=0)
    if frequency == "daily":
        return today_boundary if local_now >= today_boundary else today_boundary - timedelta(days=1)
    if frequency != "weekly":
        raise ValueError("frequency must be daily or weekly")

    days_since_monday = (today_boundary.weekday() - WEEKLY_WEEKDAY) % 7
    boundary = today_boundary - timedelta(days=days_since_monday)
    if boundary > local_now:
        boundary -= timedelta(days=7)
    return boundary


def previous_period_start(boundary: datetime, frequency: str) -> datetime:
    if frequency == "daily":
        return boundary - timedelta(days=1)
    if frequency == "weekly":
        return boundary - timedelta(days=7)
    raise ValueError("frequency must be daily or weekly")


def boundary_from_run_date(run_date_iso: str, digest_hour_local: int, zone: ZoneInfo) -> datetime:
    d = datetime.fromisoformat(run_date_iso).date()
    return datetime.combine(d, time(hour=digest_hour_local), tzinfo=zone)
