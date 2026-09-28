from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class Opportunity:
    source: str
    external_id: str
    kind: str
    organization: str
    title: str
    location: str
    url: str
    start_date: str | None = None
    end_date: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class Subscriber:
    discord_user_id: int
    opted_in: bool
    internships_enabled: bool
    hackathons_enabled: bool
    frequency: str | None
    last_notification: str | None
    opted_in_at: str | None
