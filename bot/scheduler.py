from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
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

    def start(self) -> None:
        self.digest_check.start()

    def stop(self) -> None:
        self.digest_check.cancel()

    @tasks.loop(minutes=1)
    async def digest_check(self) -> None:
        now = datetime.now(self.zone)
        scheduled_today = now.replace(hour=self.config.digest_hour_local, minute=0, second=0, microsecond=0)
        if now < scheduled_today:
            return

        schedule_tag = f"{self.config.digest_hour_local:02d}00"
        daily_key = f"daily:{schedule_tag}:{now.date().isoformat()}"
        weekly_key = f"weekly:{schedule_tag}:{now.date().isoformat()}"
        run_daily = not self.database.scheduler_run_exists(daily_key)
        run_weekly = now.weekday() == 6 and not self.database.scheduler_run_exists(weekly_key)
        if not run_daily and not run_weekly:
            return

        logger.info("Running Scout's scheduled noon source refresh before digest delivery.")
        sync_results = await self.source_service.sync_all(minimum_gap_seconds=0)
        expected_sources = {source.name for source in self.source_service.sources}
        checked_sources = set(sync_results)
        all_sources_checked = expected_sources.issubset(checked_sources)
        if not all_sources_checked:
            logger.warning("Not every source completed the scheduled refresh. Missing: %s", sorted(expected_sources - checked_sources))

        if run_daily:
            window_start = scheduled_today - timedelta(days=1)
            delivered = await self._send_frequency("daily", window_start, scheduled_today)
            if delivered and all_sources_checked:
                self.database.mark_scheduler_run(daily_key)
            else:
                logger.warning("Daily noon digest remains pending and will retry on the next scheduler check.")

        if run_weekly:
            window_start = scheduled_today - timedelta(days=7)
            delivered = await self._send_frequency("weekly", window_start, scheduled_today)
            if delivered and all_sources_checked:
                self.database.mark_scheduler_run(weekly_key)
            else:
                logger.warning("Weekly Sunday digest remains pending and will retry on the next scheduler check.")

    @digest_check.before_loop
    async def before_digest_check(self) -> None:
        await self.bot.wait_until_ready()

    async def _send_frequency(self, frequency: str, window_start: datetime, window_end: datetime) -> bool:
        subscribers = self.database.subscribers_for_frequency(frequency)
        logger.info(
            "Running %s digest for %s subscribers. Window: %s to %s.",
            frequency,
            len(subscribers),
            window_start.isoformat(),
            window_end.isoformat(),
        )
        all_transient_sends_succeeded = True
        for subscriber in subscribers:
            window_start_iso = window_start.astimezone(timezone.utc).isoformat()
            window_end_iso = window_end.astimezone(timezone.utc).isoformat()
            internships = (
                self.database.pending_opportunities_for_window(subscriber, "internship", window_start_iso, window_end_iso)
                if subscriber.internships_enabled else []
            )
            hackathons = (
                self.database.pending_opportunities_for_window(subscriber, "hackathon", window_start_iso, window_end_iso)
                if subscriber.hackathons_enabled else []
            )
            if not internships and not hackathons:
                continue

            try:
                user = self.bot.get_user(subscriber.discord_user_id) or await self.bot.fetch_user(subscriber.discord_user_id)
            except discord.HTTPException:
                logger.exception("Could not fetch Discord user %s.", subscriber.discord_user_id)
                all_transient_sends_succeeded = False
                continue

            if internships:
                result = await self._send_category(user, subscriber.discord_user_id, "internship", internships, frequency)
                if result == "retry":
                    all_transient_sends_succeeded = False
            if hackathons:
                result = await self._send_category(user, subscriber.discord_user_id, "hackathon", hackathons, frequency)
                if result == "retry":
                    all_transient_sends_succeeded = False
        return all_transient_sends_succeeded

    async def _send_category(self, user: discord.User, user_id: int, kind: str, items: list[Opportunity], frequency: str) -> str:
        try:
            digest_id = self.database.create_digest_batch(user_id, kind, frequency, items)
            message = await user.send(
                embed=digest_embed(kind, items, 0, frequency),
                view=DigestPagerView(self.database, current_page=0, total_pages=page_count(len(items))),
            )
            self.database.attach_digest_message(digest_id, message.id)
            self.database.mark_delivered(user_id, items)
            logger.info("Delivered %s %s opportunities to user %s.", len(items), kind, user_id)
            return "sent"
        except discord.Forbidden:
            logger.warning("Could not DM user %s because Discord blocked the DM. Not retrying this minute.", user_id)
            return "blocked"
        except discord.HTTPException:
            logger.exception("Discord API error while messaging user %s.", user_id)
            return "retry"
        except Exception:
            logger.exception("Unexpected error while messaging user %s.", user_id)
            return "retry"
