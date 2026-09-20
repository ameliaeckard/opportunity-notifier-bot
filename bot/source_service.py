from __future__ import annotations

import logging

import aiohttp

from bot.database import Database
from bot.sources.base import OpportunitySource


logger = logging.getLogger(__name__)


class SourceService:
    def __init__(self, database: Database, sources: list[OpportunitySource]) -> None:
        self.database = database
        self.sources = sources

    async def sync_all(self) -> dict[str, int]:
        timeout = aiohttp.ClientTimeout(total=45)
        headers = {"User-Agent": "opportunity-notifier-bot/1.0"}
        results: dict[str, int] = {}
        async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
            for source in self.sources:
                try:
                    opportunities = await source.fetch(session)
                    initialized = self.database.source_initialized(source.name)
                    inserted = self.database.store_opportunities(
                        opportunities,
                        notify_eligible=initialized,
                    )
                    self.database.mark_source_checked(source.name, initialized=True)
                    results[source.name] = inserted
                    if initialized:
                        logger.info("Source %s synced. %s new opportunities found.", source.name, inserted)
                    else:
                        logger.info("Source %s baseline created with %s current opportunities.", source.name, inserted)
                except Exception:
                    logger.exception("Failed to sync source %s.", source.name)
        return results
