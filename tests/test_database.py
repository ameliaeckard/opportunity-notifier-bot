from bot.database import Database
from bot.models import Opportunity


def test_preferences_and_delivery_flow(tmp_path):
    database = Database(str(tmp_path / "test.db"))
    database.initialize()
    database.save_preferences(123, internships=True, hackathons=False, frequency="daily")

    subscriber = database.get_subscriber(123)
    assert subscriber is not None
    assert subscriber.opted_in is True
    assert subscriber.internships_enabled is True
    assert subscriber.hackathons_enabled is False
    assert subscriber.frequency == "daily"

    opportunity = Opportunity(
        source="test",
        external_id="abc",
        kind="internship",
        organization="Example Co",
        title="Software Engineering Intern",
        location="Charlotte, NC",
        url="https://example.com/job",
    )
    database.store_opportunities([opportunity], notify_eligible=True)
    pending = database.pending_opportunities(subscriber, "internship")
    assert [item.external_id for item in pending] == ["abc"]

    database.mark_delivered(123, pending)
    assert database.pending_opportunities(subscriber, "internship") == []


def test_initial_source_baseline_is_not_notified(tmp_path):
    database = Database(str(tmp_path / "test.db"))
    database.initialize()
    database.save_preferences(456, internships=True, hackathons=False, frequency="daily")

    opportunity = Opportunity(
        source="test",
        external_id="baseline",
        kind="internship",
        organization="Example Co",
        title="Intern",
        location="Remote",
        url="https://example.com/baseline",
    )
    database.store_opportunities([opportunity], notify_eligible=False)
    subscriber = database.get_subscriber(456)
    assert subscriber is not None
    assert database.pending_opportunities(subscriber, "internship") == []


def test_digest_batch_tracks_pages_by_message(tmp_path):
    database = Database(str(tmp_path / "test.db"))
    database.initialize()
    items = [
        Opportunity(
            source="test",
            external_id="one",
            kind="internship",
            organization="One Co",
            title="Intern One",
            location="Remote",
            url="https://example.com/one",
        ),
        Opportunity(
            source="test",
            external_id="two",
            kind="internship",
            organization="Two Co",
            title="Intern Two",
            location="Charlotte, NC",
            url="https://example.com/two",
        ),
    ]
    database.store_opportunities(items, notify_eligible=True)
    digest_id = database.create_digest_batch(999, "internship", "daily", items)
    database.attach_digest_message(digest_id, 123456)

    batch = database.get_digest_by_message(123456)
    assert batch is not None
    assert batch["current_page"] == 0
    assert [item.external_id for item in batch["items"]] == ["one", "two"]

    database.set_digest_page(digest_id, 1)
    batch = database.get_digest_by_message(123456)
    assert batch is not None
    assert batch["current_page"] == 1
