from __future__ import annotations

import logging
from datetime import datetime
from zoneinfo import ZoneInfo

import discord
from discord.ext import tasks

from bot.config import Config
from bot.database import Database
from bot.notifications import hackathon_embed, internship_embed
from bot.source_service import SourceService
from bot.views.preferences import NotificationControlsView


logger = logging.getLogger(__name__)


class BackgroundScheduler:
    def __init__(
        self,
        bot: discord.Client,
        config: Config,
        database: Database,
        source_service: SourceService,
    ) -> None:
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

    @tasks.loop(minutes=15)
    async def source_poll(self) -> None:
        await self.source_service.sync_all()

    @source_poll.before_loop
    async def before_source_poll(self) -> None:
        await self.bot.wait_until_ready()

    @tasks.loop(minutes=5)
    async def digest_check(self) -> None:
        now = datetime.now(self.zone)
        if now.hour < self.config.digest_hour_local:
            return

        daily_key = f"daily:{now.date().isoformat()}"
        if not self.database.scheduler_run_exists(daily_key):
            await self._send_frequency("daily")
            self.database.mark_scheduler_run(daily_key)

        if now.weekday() == 6:
            weekly_key = f"weekly:{now.date().isoformat()}"
            if not self.database.scheduler_run_exists(weekly_key):
                await self._send_frequency("weekly")
                self.database.mark_scheduler_run(weekly_key)

    @digest_check.before_loop
    async def before_digest_check(self) -> None:
        await self.bot.wait_until_ready()

    async def _send_frequency(self, frequency: str) -> None:
        subscribers = self.database.subscribers_for_frequency(frequency)
        logger.info("Running %s digest for %s subscribers.", frequency, len(subscribers))
        for subscriber in subscribers:
            internships = (
                self.database.pending_opportunities(subscriber, "internship", limit=10)
                if subscriber.internships_enabled
                else []
            )
            hackathons = (
                self.database.pending_opportunities(subscriber, "hackathon", limit=10)
                if subscriber.hackathons_enabled
                else []
            )
            if not internships and not hackathons:
                continue

            embeds: list[discord.Embed] = []
            if internships:
                embeds.append(internship_embed(internships))
            if hackathons:
                embeds.append(hackathon_embed(hackathons))
            for embed in embeds:
                label = "Daily" if frequency == "daily" else "Weekly"
                embed.set_footer(text=f"You're receiving the {label} digest.")

            try:
                user = self.bot.get_user(subscriber.discord_user_id) or await self.bot.fetch_user(subscriber.discord_user_id)
                await user.send(
                    embeds=embeds,
                    view=NotificationControlsView(self.database),
                )
                self.database.mark_delivered(
                    subscriber.discord_user_id,
                    [*internships, *hackathons],
                )
            except discord.Forbidden:
                logger.warning("Could not DM user %s. DMs may be disabled.", subscriber.discord_user_id)
            except discord.HTTPException:
                logger.exception("Discord API error while messaging user %s.", subscriber.discord_user_id)
            except Exception:
                logger.exception("Unexpected error while messaging user %s.", subscriber.discord_user_id)
