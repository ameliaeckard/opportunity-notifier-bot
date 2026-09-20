# Opportunity Notifier Bot

A privacy-conscious Discord bot that lets students explicitly opt in to private internship and hackathon notifications.

## What it does

- `/opportunities` opens a private, ephemeral setup flow.
- Students choose whether to opt in.
- Students choose Internships, Hackathons, or Both.
- Students choose Daily or Weekly delivery.
- Weekly digests are sent on Sundays.
- Digests are sent only by Discord DM.
- Every notification includes Preferences and Unsubscribe buttons.
- `/unsubscribe` stops all notification DMs immediately.
- SQLite stores only the Discord user ID, notification preferences, timestamps, source state, and delivery history.
- New items are deduplicated before delivery.
- The first successful source sync becomes a baseline, so existing listings are not blasted to students as if they were new.

## Data sources

### Internships

Internships are read from the public `dev` branch of [SimplifyJobs Summer 2027 Internships](https://github.com/SimplifyJobs/Summer2027-Internships), using its structured listings JSON.

### Hackathons

Hackathons are read from the public [Hackalendar API](https://hackalendar.com/api). It provides upcoming, human-verified events as structured data without an API key and links users back to organiser registration pages.

This project does not scrape Devpost.

## Project structure

```text
bot/
  cogs/
    opportunities.py
  sources/
    base.py
    internships.py
    hackathons.py
  views/
    preferences.py
  config.py
  database.py
  main.py
  models.py
  notifications.py
  scheduler.py
  source_service.py
tests/
  test_database.py
  test_sources.py
.env.example
railway.json
requirements.txt
```

## Local setup

1. Create a Discord application and bot in the Discord Developer Portal.
2. Add the bot to your class server with the `bot` and `applications.commands` scopes.
3. Copy `.env.example` to `.env`.
4. Put your bot token in `DISCORD_TOKEN`.
5. Optionally set `DISCORD_GUILD_ID` to your class server ID while testing. Guild-scoped commands appear quickly. Leave it blank for global command sync.
6. Install dependencies and start the bot.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m bot.main
```

On Windows PowerShell, activate the environment with:

```powershell
.venv\Scripts\Activate.ps1
```

## Environment variables

| Variable | Required | Default | Purpose |
| --- | --- | --- | --- |
| `DISCORD_TOKEN` | Yes | None | Discord bot token |
| `DISCORD_GUILD_ID` | No | None | Optional test guild for faster slash command sync |
| `DATABASE_PATH` | No | `./data/opportunity_notifier.db` | SQLite database path |
| `BOT_TIMEZONE` | No | `America/New_York` | Timezone used for digest scheduling |
| `DIGEST_HOUR_LOCAL` | No | `9` | Local hour when digests become eligible to run |
| `SOURCE_POLL_MINUTES` | No | `15` | How often the bot checks sources for additions |
| `LOG_LEVEL` | No | `INFO` | Python logging level |

## Railway deployment

This repository includes `railway.json`. Railway will use Railpack and start the service with:

```text
python -m bot.main
```

In Railway:

1. Create a new project from this GitHub repository.
2. Add `DISCORD_TOKEN` as a Railway variable.
3. Add the other variables from `.env.example` as needed.
4. Add a persistent Railway volume.
5. Mount the volume at `/data`.
6. Set `DATABASE_PATH=/data/opportunity_notifier.db`.
7. Deploy one replica of the bot service.

SQLite must live on a persistent volume in Railway. Without a volume, preferences and duplicate history can be lost when a deployment is replaced.

Keep this bot at one Railway replica while using SQLite. Multiple replicas would need a shared database such as Postgres plus scheduler coordination to avoid duplicate sends.

## Scheduling behavior

The source poller checks for additions throughout the day. The digest scheduler runs after `DIGEST_HOUR_LOCAL` in `BOT_TIMEZONE` and records each daily or weekly scheduler run in SQLite so a restart does not cause the same scheduled run to execute twice.

Daily subscribers are checked every day. Weekly subscribers are checked on Sundays. If a student has no new undelivered opportunities, the bot sends nothing.

Each digest currently includes up to 10 new internships and up to 10 new hackathons. Additional undelivered items remain queued for a later digest.

## Privacy notes

The bot does not store Discord usernames, email addresses, message content, or public student profiles. It stores Discord user IDs only because Discord needs the user ID to deliver the DM and associate preferences with the correct account.

Students must explicitly opt in. They can change preferences with `/opportunities`, use the Preferences button in a DM, use the Unsubscribe button in a DM, or run `/unsubscribe`.

## Tests

Run:

```bash
pytest
```

The included tests cover preference storage, delivery deduplication, first-sync baseline behavior, and source parsing.

## Notes

- No GitHub Actions are used.
- Logging goes to stdout so Railway can collect it.
- The bot does not require the privileged Message Content intent.
- Source failures are logged and do not automatically initialize a failed source baseline.
