from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

import discord
from discord.ext import tasks

from bot.config import Config
from bot.database import Database
from bot.models import Opportunity
from bot.notifications import digest_embed, page_count
from bot.source_service import SourceService
from bot.views.digests import DigestPagerView


logger = logging.getLogger(__name__)


class BackgroundScheduler:
    def __init__(self, bot: discord.Client, config: Config, database: Database, source_service: SourceService) -> None:
        self.bot = bot
        self.config = config
        self.database = database
        self.source_service = source_service
        self.zone = ZoneInfo(config.timezone)
        self.source_poll.change_interval(minutes=config.source_poll_minutes)

    def start(self) -> None:
        self.source_poll.start()
        self.digest_check.start()

    def stop(self) -> None:
        self.source_poll.cancel()
        self.digest_check.cancel()

    @tasks.loop(minutes=60)
    async def source_poll(self) -> None:
        await self.source_service.sync_all()

    @source_poll.before_loop
    async def before_source_poll(self) -> None:
        await self.bot.wait_until_ready()
        await asyncio.sleep(self.config.source_poll_minutes * 60)

    @tasks.loop(minutes=5)
    async def digest_check(self) -> None:
        now = datetime.now(self.zone)
        if now.hour < self.config.digest_hour_local:
            return

        daily_key = f"daily:{now.date().isoformat()}"
        weekly_key = f"weekly:{now.date().isoformat()}"
        run_daily = not self.database.scheduler_run_exists(daily_key)
        run_weekly = now.weekday() == 6 and not self.database.scheduler_run_exists(weekly_key)
        if not run_daily and not run_weekly:
            return

        await self.source_service.sync_all()

        if run_daily:
            await self._send_frequency("daily")
            self.database.mark_scheduler_run(daily_key)

        if run_weekly:
            await self._send_frequency("weekly")
            self.database.mark_scheduler_run(weekly_key)

    @digest_check.before_loop
    async def before_digest_check(self) -> None:
        await self.bot.wait_until_ready()

    async def _send_frequency(self, frequency: str) -> None:
        subscribers = self.database.subscribers_for_frequency(frequency)
        logger.info("Running %s digest for %s subscribers.", frequency, len(subscribers))
        for subscriber in subscribers:
            internships = self.database.pending_opportunities(subscriber, "internship", limit=25) if subscriber.internships_enabled else []
            hackathons = self.database.pending_opportunities(subscriber, "hackathon", limit=25) if subscriber.hackathons_enabled else []
            if not internships and not hackathons:
                continue

            try:
                user = self.bot.get_user(subscriber.discord_user_id) or await self.bot.fetch_user(subscriber.discord_user_id)
            except discord.HTTPException:
                logger.exception("Could not fetch Discord user %s.", subscriber.discord_user_id)
                continue

            if internships:
                await self._send_category(user, subscriber.discord_user_id, "internship", internships, frequency)
            if hackathons:
                await self._send_category(user, subscriber.discord_user_id, "hackathon", hackathons, frequency)

    async def _send_category(self, user: discord.User, user_id: int, kind: str, items: list[Opportunity], frequency: str) -> None:
        try:
            digest_id = self.database.create_digest_batch(user_id, kind, frequency, items)
            message = await user.send(
                embed=digest_embed(kind, items, 0, frequency),
                view=DigestPagerView(self.database, current_page=0, total_pages=page_count(len(items))),
            )
            self.database.attach_digest_message(digest_id, message.id)
            self.database.mark_delivered(user_id, items)
        except discord.Forbidden:
            logger.warning("Could not DM user %s. DMs may be disabled.", user_id)
        except discord.HTTPException:
            logger.exception("Discord API error while messaging user %s.", user_id)
        except Exception:
            logger.exception("Unexpected error while messaging user %s.", user_id)
