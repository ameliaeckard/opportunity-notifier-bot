from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


load_dotenv()


@dataclass(frozen=True, slots=True)
class Config:
    discord_token: str
    discord_guild_id: int | None
    database_path: str
    timezone: str
    digest_hour_local: int
    source_poll_minutes: int
    log_level: str

    @classmethod
    def from_env(cls) -> "Config":
        token = os.getenv("DISCORD_TOKEN", "").strip()
        if not token:
            raise RuntimeError("DISCORD_TOKEN is required.")

        guild_id_raw = os.getenv("DISCORD_GUILD_ID", "").strip()
        guild_id = int(guild_id_raw) if guild_id_raw else None

        digest_hour = int(os.getenv("DIGEST_HOUR_LOCAL", "9"))
        if not 0 <= digest_hour <= 23:
            raise ValueError("DIGEST_HOUR_LOCAL must be between 0 and 23.")

        poll_minutes = int(os.getenv("SOURCE_POLL_MINUTES", "15"))
        if poll_minutes < 5:
            raise ValueError("SOURCE_POLL_MINUTES must be at least 5.")

        return cls(
            discord_token=token,
            discord_guild_id=guild_id,
            database_path=os.getenv("DATABASE_PATH", "./data/opportunity_notifier.db"),
            timezone=os.getenv("BOT_TIMEZONE", "America/New_York"),
            digest_hour_local=digest_hour,
            source_poll_minutes=poll_minutes,
            log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
        )
