from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

import aiohttp

from bot.models import Opportunity
from bot.sources.base import OpportunitySource


logger = logging.getLogger(__name__)


class HackathonSource(OpportunitySource):
    name = "hackalendar"
    api_url = "https://hackalendar.com/api/events?limit=200"
    mcp_url = "https://hackalendar.com/api/mcp"

    async def fetch(self, session: aiohttp.ClientSession) -> list[Opportunity]:
        async with session.get(self.api_url) as response:
            response.raise_for_status()
            payload = await response.json(content_type=None)
        data = payload.get("data", []) if isinstance(payload, dict) else payload
        parsed = self.parse(data)
        if parsed:
            return parsed

        logger.warning("Hackalendar JSON API returned no usable events. Trying the documented MCP search fallback.")
        mcp_payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": "search_hackathons", "arguments": {"limit": 50}},
        }
        async with session.post(self.mcp_url, json=mcp_payload) as response:
            response.raise_for_status()
            fallback_payload = await response.json(content_type=None)
        return self.parse(self._extract_mcp_events(fallback_payload))

    @classmethod
    def _extract_mcp_events(cls, payload: Any) -> list[dict[str, Any]]:
        if not isinstance(payload, dict):
            return []
        result = payload.get("result")
        if not isinstance(result, dict):
            return []
        structured = result.get("structuredContent") or result.get("structured_content")
        if isinstance(structured, dict) and isinstance(structured.get("events"), list):
            return structured["events"]
        if isinstance(result.get("events"), list):
            return result["events"]
        content = result.get("content")
        if isinstance(content, list):
            for block in content:
                if not isinstance(block, dict):
                    continue
                text = block.get("text")
                if not isinstance(text, str):
                    continue
                try:
                    decoded = json.loads(text)
                except json.JSONDecodeError:
                    continue
                if isinstance(decoded, dict) and isinstance(decoded.get("events"), list):
                    return decoded["events"]
        return []

    @classmethod
    def parse(cls, payload: Any) -> list[Opportunity]:
        if not isinstance(payload, list):
            raise ValueError("Hackalendar payload must be a list.")

        now = datetime.now(timezone.utc)
        opportunities: list[Opportunity] = []
        for item in payload:
            if not isinstance(item, dict) or item.get("cancelled") is True:
                continue
            slug = str(item.get("slug") or item.get("id") or "").strip()
            name = str(item.get("name") or item.get("title") or "").strip()
            starts_at = str(item.get("startsAt") or item.get("starts_at") or item.get("start") or "").strip()
            ends_at = str(item.get("endsAt") or item.get("ends_at") or item.get("end") or "").strip()
            registration_url = str(item.get("registrationUrl") or item.get("registration_url") or item.get("url") or "").strip()
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
                    str(raw_location.get("city") or raw_location.get("name") or "").strip(),
                    str(raw_location.get("region") or raw_location.get("state") or raw_location.get("province") or "").strip(),
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
            organizer_name = str(organizer.get("name") or "").strip() if isinstance(organizer, dict) else str(organizer or "").strip()
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
                        "registration_deadline": item.get("registrationDeadline") or item.get("registration_deadline"),
                        "happening_now": item.get("happeningNow") or item.get("happening_now") or False,
                        "pick_note": item.get("pickNote") or item.get("pick_note"),
                    },
                )
            )
        return opportunities
