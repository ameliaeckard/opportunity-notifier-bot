from datetime import datetime
from zoneinfo import ZoneInfo

from bot.schedule_logic import latest_daily_boundary, latest_weekly_boundary


ZONE = ZoneInfo("America/New_York")


def test_daily_boundary_after_noon_is_today():
    now = datetime(2026, 9, 27, 12, 5, tzinfo=ZONE)
    assert latest_daily_boundary(now, 12) == datetime(2026, 9, 27, 12, 0, tzinfo=ZONE)


def test_daily_boundary_before_noon_is_yesterday():
    now = datetime(2026, 9, 27, 9, 0, tzinfo=ZONE)
    assert latest_daily_boundary(now, 12) == datetime(2026, 9, 26, 12, 0, tzinfo=ZONE)


def test_weekly_boundary_is_monday_noon():
    now = datetime(2026, 9, 28, 12, 1, tzinfo=ZONE)
    assert latest_weekly_boundary(now, 12) == datetime(2026, 9, 28, 12, 0, tzinfo=ZONE)


def test_missed_monday_recovers_on_tuesday():
    now = datetime(2026, 9, 29, 15, 0, tzinfo=ZONE)
    assert latest_weekly_boundary(now, 12) == datetime(2026, 9, 28, 12, 0, tzinfo=ZONE)


def test_monday_before_noon_points_to_previous_monday():
    now = datetime(2026, 9, 28, 11, 59, tzinfo=ZONE)
    assert latest_weekly_boundary(now, 12) == datetime(2026, 9, 21, 12, 0, tzinfo=ZONE)
