from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import aiohttp

from bot.models import Opportunity
from bot.sources.base import OpportunitySource


class HackathonSource(OpportunitySource):
    name = "hackalendar"
    api_url = "https://hackalendar.com/api/events?limit=200"

    async def fetch(self, session: aiohttp.ClientSession) -> list[Opportunity]:
        async with session.get(self.api_url) as response:
            response.raise_for_status()
            payload = await response.json(content_type=None)
        data = payload.get("data", []) if isinstance(payload, dict) else []
        return self.parse(data)

    @classmethod
    def parse(cls, payload: Any) -> list[Opportunity]:
        if not isinstance(payload, list):
            raise ValueError("Hackalendar payload must be a list.")

        now = datetime.now(timezone.utc)
        opportunities: list[Opportunity] = []
        for item in payload:
            if not isinstance(item, dict):
                continue
            if item.get("cancelled") is True:
                continue

            slug = str(item.get("slug") or item.get("id") or "").strip()
            name = str(item.get("name") or item.get("title") or "").strip()
            starts_at = str(item.get("startsAt") or item.get("starts_at") or item.get("start") or "").strip()
            ends_at = str(item.get("endsAt") or item.get("ends_at") or item.get("end") or "").strip()
            registration_url = str(
                item.get("registrationUrl")
                or item.get("registration_url")
                or item.get("url")
                or ""
            ).strip()
            if not all((slug, name, starts_at, ends_at, registration_url)):
                continue

            try:
                end_dt = datetime.fromisoformat(ends_at.replace("Z", "+00:00"))
                if end_dt.tzinfo is None:
                    end_dt = end_dt.replace(tzinfo=timezone.utc)
                if end_dt < now:
                    continue
            except ValueError:
                continue

            raw_location = item.get("location")
            if isinstance(raw_location, dict):
                location_bits = [
                    str(raw_location.get("city") or "").strip(),
                    str(raw_location.get("region") or raw_location.get("state") or "").strip(),
                    str(raw_location.get("country") or "").strip(),
                ]
                location = ", ".join(bit for bit in location_bits if bit)
            else:
                location = str(raw_location or item.get("city") or "").strip()

            mode = str(item.get("mode") or item.get("modality") or "").lower()
            if mode in {"online", "virtual"}:
                location = "Online"
            elif mode == "hybrid":
                location = f"{location or 'Location not listed'} / Hybrid"
            elif not location:
                location = "Location not listed"

            organizer = item.get("organizer")
            if isinstance(organizer, dict):
                organizer_name = str(organizer.get("name") or "").strip()
            else:
                organizer_name = str(organizer or "").strip()

            opportunities.append(
                Opportunity(
                    source=cls.name,
                    external_id=slug,
                    kind="hackathon",
                    organization=name,
                    title=organizer_name or "Hackathon",
                    location=location,
                    url=registration_url,
                    start_date=starts_at,
                    end_date=ends_at,
                    metadata={
                        "mode": mode,
                        "themes": item.get("themes") or [],
                        "organizer": organizer_name,
                    },
                )
            )
        return opportunities
