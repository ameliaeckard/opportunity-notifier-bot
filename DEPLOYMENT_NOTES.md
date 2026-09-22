# Scout replacement deployment notes

1. Replace the old project files with this ZIP's contents.
2. Keep the existing Railway volume mounted at `/data` so the current SQLite subscriber/delivery history survives the deployment.
3. Keep `DATABASE_PATH=/data/opportunity_notifier.db`.
4. Add `DAILY_DIGEST_HOUR_LOCAL=12`.
5. Add `STUDENT_ADDED_WEBHOOK_URL=<your Discord webhook URL>`.
6. Keep `BOT_TIMEZONE=America/New_York`.
7. The old `DIGEST_HOUR_LOCAL` and `SOURCE_POLL_MINUTES` variables are ignored and can be deleted.
8. If `DISCORD_GUILD_ID` is still set from the old single-server deployment, leave it for the first deploy so Scout can clear the old guild-scoped commands. After a successful deploy, it can be removed because commands are global.

Scheduled automatic source collection now happens once at noon. `/testrecent` still performs an on-demand live read when an administrator explicitly runs it.
