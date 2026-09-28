from __future__ import annotations

from datetime import datetime, timedelta


WEEKLY_WEEKDAY = 0  # Monday


def latest_daily_boundary(now: datetime, digest_hour_local: int) -> datetime:
    boundary = now.replace(hour=digest_hour_local, minute=0, second=0, microsecond=0)
    if now < boundary:
        boundary -= timedelta(days=1)
    return boundary


def latest_weekly_boundary(now: datetime, digest_hour_local: int, weekday: int = WEEKLY_WEEKDAY) -> datetime:
    today_boundary = now.replace(hour=digest_hour_local, minute=0, second=0, microsecond=0)
    days_since_target = (now.weekday() - weekday) % 7
    boundary = today_boundary - timedelta(days=days_since_target)
    if days_since_target == 0 and now < today_boundary:
        boundary -= timedelta(days=7)
    return boundary


def fallback_window_start(boundary: datetime, frequency: str) -> datetime:
    if frequency == "daily":
        return boundary - timedelta(days=1)
    if frequency == "weekly":
        return boundary - timedelta(days=7)
    raise ValueError("frequency must be daily or weekly")
