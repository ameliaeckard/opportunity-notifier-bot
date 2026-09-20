from __future__ import annotations

import logging

import discord
from discord.ext import commands

from bot.cogs.opportunities import OpportunitiesCog
from bot.config import Config
from bot.database import Database
from bot.scheduler import BackgroundScheduler
from bot.source_service import SourceService
from bot.sources import HackathonSource, InternshipSource
from bot.views.preferences import NotificationControlsView


class OpportunityBot(commands.Bot):
    def __init__(self, config: Config) -> None:
        intents = discord.Intents.none()
        super().__init__(command_prefix=commands.when_mentioned, intents=intents)
        self.config = config
        self.database = Database(config.database_path)
        self.source_service = SourceService(
            self.database,
            [InternshipSource(), HackathonSource()],
        )
        self.scheduler = BackgroundScheduler(
            self,
            config,
            self.database,
            self.source_service,
        )

    async def setup_hook(self) -> None:
        self.database.initialize()
        self.add_view(NotificationControlsView(self.database))
        await self.add_cog(OpportunitiesCog(self, self.database))
        await self.source_service.sync_all()

        if self.config.discord_guild_id:
            guild = discord.Object(id=self.config.discord_guild_id)
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
            logging.getLogger(__name__).info("Slash commands synced to guild %s.", self.config.discord_guild_id)
        else:
            await self.tree.sync()
            logging.getLogger(__name__).info("Global slash commands synced.")

        self.scheduler.start()

    async def close(self) -> None:
        self.scheduler.stop()
        await super().close()

    async def on_ready(self) -> None:
        logging.getLogger(__name__).info("Logged in as %s (%s).", self.user, self.user.id if self.user else "unknown")


def configure_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level, logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


def main() -> None:
    config = Config.from_env()
    configure_logging(config.log_level)
    bot = OpportunityBot(config)
    bot.run(config.discord_token, log_handler=None)


if __name__ == "__main__":
    main()
