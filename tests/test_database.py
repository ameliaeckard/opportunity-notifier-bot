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
