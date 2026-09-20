from __future__ import annotations

import asyncio
import logging
import time
from typing import Iterable

import aiohttp

from bot.database import Database
from bot.models import Opportunity
from bot.sources.base import OpportunitySource


logger = logging.getLogger(__name__)


class SourceService:
    def __init__(self, database: Database, sources: list[OpportunitySource]) -> None:
        self.database = database
        self.sources = sources
        self._sync_lock = asyncio.Lock()
        self._last_sync_monotonic: float | None = None

    async def fetch_current(self) -> dict[str, list[Opportunity]]:
        timeout = aiohttp.ClientTimeout(total=45)
        headers = {"User-Agent": "scout-opportunity-bot/1.0"}
        results: dict[str, list[Opportunity]] = {}
        async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
            for source in self.sources:
                try:
                    results[source.name] = await source.fetch(session)
                except Exception:
                    logger.exception("Failed to fetch source %s.", source.name)
        return results

    async def sync_all(self, minimum_gap_seconds: int = 300) -> dict[str, int]:
        async with self._sync_lock:
            now = time.monotonic()
            if self._last_sync_monotonic is not None and now - self._last_sync_monotonic < minimum_gap_seconds:
                logger.info("Skipping source refresh because Scout checked less than %s seconds ago.", minimum_gap_seconds)
                return {}

            fetched = await self.fetch_current()
            results: dict[str, int] = {}
            for source in self.sources:
                if source.name not in fetched:
                    continue
                opportunities = fetched[source.name]
                initialized = self.database.source_initialized(source.name)
                inserted = self.database.store_opportunities(opportunities, notify_eligible=initialized)
                self.database.mark_source_checked(source.name, initialized=True)
                results[source.name] = inserted
                if initialized:
                    logger.info("Source %s checked. %s unseen opportunities were added.", source.name, inserted)
                else:
                    logger.info("Source %s baseline created with %s current opportunities.", source.name, inserted)
            self._last_sync_monotonic = time.monotonic()
            return results

    async def preview_recent(self, limit: int = 5) -> dict[str, list[Opportunity]]:
        fetched = await self.fetch_current()
        items = list(self._flatten(fetched.values()))
        internships = [item for item in items if item.kind == "internship"]
        hackathons = [item for item in items if item.kind == "hackathon"]
        internships.sort(key=self._internship_recency, reverse=True)
        hackathons.sort(key=lambda item: item.start_date or "9999-12-31T23:59:59Z")
        return {
            "internship": internships[:limit],
            "hackathon": hackathons[:limit],
        }

    @staticmethod
    def _flatten(groups: Iterable[list[Opportunity]]) -> Iterable[Opportunity]:
        for group in groups:
            yield from group

    @staticmethod
    def _internship_recency(item: Opportunity) -> float:
        for key in ("date_updated", "date_posted"):
            value = item.metadata.get(key)
            try:
                return float(value)
            except (TypeError, ValueError):
                continue
        return 0.0
