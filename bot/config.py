from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


load_dotenv()


@dataclass(frozen=True, slots=True)
class Config:
    discord_token: str
    legacy_discord_guild_id: int | None
    database_path: str
    timezone: str
    digest_hour_local: int
    student_added_webhook_url: str | None
    log_level: str

    @classmethod
    def from_env(cls) -> "Config":
        token = os.getenv("DISCORD_TOKEN", "").strip()
        if not token:
            raise RuntimeError("DISCORD_TOKEN is required.")

        # Kept only so an older guild-scoped command deployment can be cleared.
        # Scout always registers its active commands globally.
        legacy_guild_id_raw = os.getenv("DISCORD_GUILD_ID", "").strip()
        legacy_guild_id = int(legacy_guild_id_raw) if legacy_guild_id_raw else None

        digest_hour = int(os.getenv("DAILY_DIGEST_HOUR_LOCAL", "12"))
        if not 0 <= digest_hour <= 23:
            raise ValueError("DAILY_DIGEST_HOUR_LOCAL must be between 0 and 23.")

        return cls(
            discord_token=token,
            legacy_discord_guild_id=legacy_guild_id,
            database_path=os.getenv("DATABASE_PATH", "./data/opportunity_notifier.db"),
            timezone=os.getenv("BOT_TIMEZONE", "America/New_York"),
            digest_hour_local=digest_hour,
            student_added_webhook_url=os.getenv("STUDENT_ADDED_WEBHOOK_URL", "").strip() or None,
            log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
        )
