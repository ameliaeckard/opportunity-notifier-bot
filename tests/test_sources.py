from datetime import datetime, timedelta, timezone

from bot.sources.hackathons import HackathonSource
from bot.sources.internships import InternshipSource


def test_internship_parser_filters_inactive_and_wrong_term():
    payload = [
        {"id": "1", "active": True, "is_visible": True, "terms": ["Summer 2027"], "company_name": "NVIDIA", "title": "Software Engineering Intern", "url": "https://example.com/1", "locations": ["Charlotte, NC", "Remote"], "source": "Simplify"},
        {"id": "2", "active": False, "is_visible": True, "terms": ["Summer 2027"], "company_name": "Old Co", "title": "Intern", "url": "https://example.com/2", "locations": ["Remote"]},
        {"id": "3", "active": True, "is_visible": True, "terms": ["Fall 2027"], "company_name": "Other Co", "title": "Intern", "url": "https://example.com/3", "locations": ["Remote"]},
    ]
    parsed = InternshipSource.parse(payload)
    assert len(parsed) == 1
    assert parsed[0].organization == "NVIDIA"
    assert parsed[0].location == "Charlotte, NC / Remote"


def test_hackathon_parser_keeps_upcoming_event():
    now = datetime.now(timezone.utc)
    payload = [{"slug": "hack-example-2026", "name": "Hack Example", "registrationUrl": "https://example.com/register", "startsAt": (now + timedelta(days=10)).isoformat(), "endsAt": (now + timedelta(days=12)).isoformat(), "mode": "hybrid", "location": "Chapel Hill, NC", "organizer": "Example University", "themes": ["student"], "cancelled": False}]
    parsed = HackathonSource.parse(payload)
    assert len(parsed) == 1
    assert parsed[0].organization == "Hack Example"
    assert parsed[0].title == "Example University"
    assert parsed[0].location == "Chapel Hill, NC / Hybrid"
    assert parsed[0].url == "https://example.com/register"


def test_hackathon_mcp_event_extraction_from_text_block():
    payload = {"result": {"content": [{"type": "text", "text": '{"count":1,"events":[{"slug":"test"}]}'}]}}
    events = HackathonSource._extract_mcp_events(payload)
    assert events == [{"slug": "test"}]
