from __future__ import annotations

from typing import Any

import aiohttp

from bot.models import Opportunity
from bot.sources.base import OpportunitySource


class InternshipSource(OpportunitySource):
    name = "simplifyjobs"
    listings_url = "https://raw.githubusercontent.com/SimplifyJobs/Summer2027-Internships/dev/.github/scripts/listings.json"

    async def fetch(self, session: aiohttp.ClientSession) -> list[Opportunity]:
        async with session.get(self.listings_url) as response:
            response.raise_for_status()
            payload = await response.json(content_type=None)
        return self.parse(payload)

    @classmethod
    def parse(cls, payload: Any) -> list[Opportunity]:
        if not isinstance(payload, list):
            raise ValueError("SimplifyJobs listings payload must be a list.")

        opportunities: list[Opportunity] = []
        for item in payload:
            if not isinstance(item, dict):
                continue
            if not item.get("active") or not item.get("is_visible", True):
                continue
            terms = item.get("terms") or []
            if terms and not any("Summer 2027" in str(term) for term in terms):
                continue

            external_id = str(item.get("id") or "").strip()
            title = str(item.get("title") or "").strip()
            company = str(item.get("company_name") or "").strip()
            url = str(item.get("url") or "").strip()
            if not all((external_id, title, company, url)):
                continue

            locations = item.get("locations") or []
            if isinstance(locations, list):
                location = " / ".join(str(value).strip() for value in locations if str(value).strip())
            else:
                location = str(locations).strip()
            if not location:
                location = "Location not listed"

            opportunities.append(
                Opportunity(
                    source=cls.name,
                    external_id=external_id,
                    kind="internship",
                    organization=company,
                    title=title,
                    location=location,
                    url=url,
                    metadata={"source": item.get("source"), "terms": terms},
                )
            )
        return opportunities
