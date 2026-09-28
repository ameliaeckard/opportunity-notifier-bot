from datetime import datetime, timedelta, timezone

from bot.database import Database
from bot.models import Opportunity


def _set_discovered(database: Database, external_id: str, discovered_at: datetime) -> None:
    with database._connect() as conn:
        conn.execute(
            "UPDATE opportunities SET discovered_at = ? WHERE external_id = ?",
            (discovered_at.isoformat(), external_id),
        )


def test_daily_internship_uses_posted_window_not_opt_in_discovery_time(tmp_path):
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
        metadata={"date_posted": (start + timedelta(hours=2)).timestamp()},
    )
    db.store_opportunities([item], notify_eligible=True)
    # Simulate Scout having discovered the posting before this user's opt-in.
    _set_discovered(db, "daily-inside", start - timedelta(days=2))

    selected = db.pending_opportunities_for_window(subscriber, "internship", start.isoformat(), end.isoformat())
    assert [x.external_id for x in selected] == ["daily-inside"]


def test_internship_window_is_half_open_and_deduplicated(tmp_path):
    db = Database(str(tmp_path / "test.db"))
    db.initialize()
    db.save_preferences(2, internships=True, hackathons=False, frequency="daily")
    subscriber = db.get_subscriber(2)
    assert subscriber is not None

    end = datetime(2026, 9, 27, 16, 0, tzinfo=timezone.utc)
    start = end - timedelta(days=1)
    items = [
        Opportunity("simplifyjobs", "at-start", "internship", "A", "Intern", "Remote", "https://a", metadata={"date_posted": start.timestamp()}),
        Opportunity("simplifyjobs", "inside", "internship", "B", "Intern", "Remote", "https://b", metadata={"date_posted": (start + timedelta(hours=1)).timestamp()}),
        Opportunity("simplifyjobs", "at-end", "internship", "C", "Intern", "Remote", "https://c", metadata={"date_posted": end.timestamp()}),
    ]
    db.store_opportunities(items, notify_eligible=True)
    selected = db.pending_opportunities_for_window(subscriber, "internship", start.isoformat(), end.isoformat())
    assert [x.external_id for x in selected] == ["at-start", "inside"]
    db.mark_delivered(2, selected)
    assert db.pending_opportunities_for_window(subscriber, "internship", start.isoformat(), end.isoformat()) == []


def test_hackathon_window_has_upper_boundary(tmp_path):
    db = Database(str(tmp_path / "test.db"))
    db.initialize()
    db.save_preferences(3, internships=False, hackathons=True, frequency="daily")
    subscriber = db.get_subscriber(3)
    assert subscriber is not None

    end = datetime(2026, 9, 27, 16, 0, tzinfo=timezone.utc)
    start = end - timedelta(days=1)
    items = [
        Opportunity("hackalendar", "inside", "hackathon", "Hack A", "Org", "Online", "https://a"),
        Opportunity("hackalendar", "after", "hackathon", "Hack B", "Org", "Online", "https://b"),
    ]
    db.store_opportunities(items, notify_eligible=True)
    _set_discovered(db, "inside", start + timedelta(hours=2))
    _set_discovered(db, "after", end + timedelta(minutes=1))

    selected = db.pending_opportunities_for_window(subscriber, "hackathon", start.isoformat(), end.isoformat())
    assert [x.external_id for x in selected] == ["inside"]


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
