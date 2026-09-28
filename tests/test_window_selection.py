from datetime import datetime, timedelta, timezone

from bot.database import Database
from bot.models import Opportunity


def _set_discovered(database: Database, external_id: str, discovered_at: datetime) -> None:
    with database._connect() as conn:
        conn.execute(
            "UPDATE opportunities SET discovered_at = ? WHERE external_id = ?",
            (discovered_at.isoformat(), external_id),
        )


def test_daily_internship_uses_scout_discovery_window(tmp_path):
    db = Database(str(tmp_path / "test.db"))
    db.initialize()
    db.save_preferences(1, internships=True, hackathons=False, frequency="daily")
    subscriber = db.get_subscriber(1)
    assert subscriber is not None

    end = datetime(2026, 9, 27, 16, 0, tzinfo=timezone.utc)
    start = end - timedelta(days=1)
    item = Opportunity(
        source="simplifyjobs",
        external_id="daily-inside",
        kind="internship",
        organization="Example",
        title="Intern",
        location="Remote",
        url="https://example.com",
        metadata={"date_posted": (start - timedelta(days=30)).timestamp()},
    )
    db.store_opportunities([item], notify_eligible=True)
    _set_discovered(db, "daily-inside", start + timedelta(hours=2))

    selected = db.pending_opportunities_for_window(
        subscriber,
        "internship",
        start.isoformat(),
        end.isoformat(),
    )
    assert [x.external_id for x in selected] == ["daily-inside"]


def test_window_is_start_exclusive_end_inclusive_and_deduplicated(tmp_path):
    db = Database(str(tmp_path / "test.db"))
    db.initialize()
    db.save_preferences(2, internships=True, hackathons=False, frequency="daily")
    subscriber = db.get_subscriber(2)
    assert subscriber is not None

    end = datetime(2026, 9, 27, 16, 0, tzinfo=timezone.utc)
    start = end - timedelta(days=1)
    items = [
        Opportunity("simplifyjobs", "at-start", "internship", "A", "Intern", "Remote", "https://a"),
        Opportunity("simplifyjobs", "inside", "internship", "B", "Intern", "Remote", "https://b"),
        Opportunity("simplifyjobs", "at-end", "internship", "C", "Intern", "Remote", "https://c"),
    ]
    db.store_opportunities(items, notify_eligible=True)
    _set_discovered(db, "at-start", start)
    _set_discovered(db, "inside", start + timedelta(hours=1))
    _set_discovered(db, "at-end", end)

    selected = db.pending_opportunities_for_window(
        subscriber,
        "internship",
        start.isoformat(),
        end.isoformat(),
    )
    assert [x.external_id for x in selected] == ["inside", "at-end"]
    db.mark_delivered(2, selected)
    assert db.pending_opportunities_for_window(
        subscriber,
        "internship",
        start.isoformat(),
        end.isoformat(),
    ) == []


def test_hackathon_window_uses_same_discovery_boundaries(tmp_path):
    db = Database(str(tmp_path / "test.db"))
    db.initialize()
    db.save_preferences(3, internships=False, hackathons=True, frequency="daily")
    subscriber = db.get_subscriber(3)
    assert subscriber is not None

    end = datetime(2026, 9, 27, 16, 0, tzinfo=timezone.utc)
    start = end - timedelta(days=1)
    items = [
        Opportunity("hackalendar", "at-end", "hackathon", "Hack A", "Org", "Online", "https://a"),
        Opportunity("hackalendar", "after", "hackathon", "Hack B", "Org", "Online", "https://b"),
    ]
    db.store_opportunities(items, notify_eligible=True)
    _set_discovered(db, "at-end", end)
    _set_discovered(db, "after", end + timedelta(minutes=1))

    selected = db.pending_opportunities_for_window(
        subscriber,
        "hackathon",
        start.isoformat(),
        end.isoformat(),
    )
    assert [x.external_id for x in selected] == ["at-end"]


def test_weekly_category_preferences_are_preserved(tmp_path):
    db = Database(str(tmp_path / "test.db"))
    db.initialize()
    db.save_preferences(4, internships=True, hackathons=False, frequency="weekly")
    subscriber = db.get_subscriber(4)
    assert subscriber is not None
    assert subscriber.frequency == "weekly"
    assert subscriber.internships_enabled is True
    assert subscriber.hackathons_enabled is False


def test_last_notification_only_changes_when_explicitly_marked(tmp_path):
    db = Database(str(tmp_path / "test.db"))
    db.initialize()
    db.save_preferences(5, internships=True, hackathons=True, frequency="daily")
    item = Opportunity("simplifyjobs", "one", "internship", "A", "Intern", "Remote", "https://a", metadata={"date_posted": 1})
    db.store_opportunities([item], notify_eligible=True)
    before = db.get_subscriber(5)
    assert before is not None and before.last_notification is None
    db.mark_delivered(5, [item])
    middle = db.get_subscriber(5)
    assert middle is not None and middle.last_notification is None
    db.mark_notification_sent(5)
    after = db.get_subscriber(5)
    assert after is not None and after.last_notification is not None


def test_legacy_few_seconds_after_noon_can_be_repaired(tmp_path):
    db = Database(str(tmp_path / "test.db"))
    db.initialize()
    end = datetime(2026, 9, 28, 16, 0, tzinfo=timezone.utc)
    item = Opportunity("simplifyjobs", "late-noon", "internship", "A", "Intern", "Remote", "https://a")
    db.store_opportunities([item], notify_eligible=True, discovered_at=(end + timedelta(seconds=5)).isoformat())
    db.align_recent_discoveries_to_boundary(end.isoformat())
    with db._connect() as conn:
        row = conn.execute("SELECT discovered_at FROM opportunities WHERE external_id = ?", ("late-noon",)).fetchone()
    assert row["discovered_at"] == end.isoformat()
