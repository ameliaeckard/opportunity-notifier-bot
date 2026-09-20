from bot.models import Opportunity
from bot.notifications import PAGE_SIZE, digest_embed, page_count


def make_internship(index: int) -> Opportunity:
    return Opportunity(
        source="test",
        external_id=str(index),
        kind="internship",
        organization=f"Example Co {index}",
        title="Software Engineering Intern",
        location="Remote",
        url=f"https://example.com/job/{index}",
    )


def test_digest_page_contains_five_listings():
    items = [make_internship(index) for index in range(1, 8)]
    embed = digest_embed("internship", items, 0, "daily")
    assert PAGE_SIZE == 5
    assert page_count(len(items)) == 2
    assert embed.title == "Internships: 7 new"
    assert embed.footer.text == "Daily digest • Page 1 of 2 • Report a bug below"
    assert len(embed.fields) == 6
    assert embed.fields[0].name == "1. Example Co 1"
    assert embed.fields[4].name == "5. Example Co 5"


def test_second_page_contains_remaining_listings():
    items = [make_internship(index) for index in range(1, 8)]
    embed = digest_embed("internship", items, 1, "daily")
    assert embed.footer.text == "Daily digest • Page 2 of 2 • Report a bug below"
    assert len(embed.fields) == 3
    assert embed.fields[0].name == "6. Example Co 6"
    assert embed.fields[1].name == "7. Example Co 7"


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
    embed = digest_embed("hackathon", [item], 0, "test")
    assert embed.title == "Upcoming Hackathons: 1"
    assert embed.footer.text == "Admin test • Page 1 of 1 • Report a bug below"
