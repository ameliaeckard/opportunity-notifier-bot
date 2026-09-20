from bot.models import Opportunity
from bot.notifications import digest_embed


def test_internship_digest_is_single_page_and_has_bug_footer():
    item = Opportunity(
        source="test",
        external_id="1",
        kind="internship",
        organization="Example Co",
        title="Software Engineering Intern",
        location="Remote",
        url="https://example.com/job",
    )
    embed = digest_embed("internship", item, 1, 4, "daily")
    assert embed.title == "Internships: 4 new"
    assert embed.footer.text == "Daily digest • Page 2 of 4 • Report a bug below"
    assert len(embed.fields) == 3


def test_hackathon_digest_uses_test_footer():
    item = Opportunity(
        source="test",
        external_id="2",
        kind="hackathon",
        organization="Hack Example",
        title="Example University",
        location="Charlotte, NC",
        url="https://example.com/event",
        start_date="2026-10-10T12:00:00Z",
        end_date="2026-10-12T12:00:00Z",
    )
    embed = digest_embed("hackathon", item, 0, 2, "test")
    assert embed.title == "Hackathons: 2 new"
    assert embed.footer.text == "Admin test • Page 1 of 2 • Report a bug below"
