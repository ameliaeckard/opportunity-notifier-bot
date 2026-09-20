# Scout

Discord bot that lets users opt in to personalized internship and hackathon notifications with daily or weekly digests.

Users explicitly opt in, choose the opportunities they want to receive, and select either daily or weekly private Discord digests. Notifications are sent by DM and include quick access to preferences and unsubscribe controls.

### Add Scout to your server

Want Scout in your server? [Add Scout to your server](https://discord.com/oauth2/authorize?client_id=1551281451536752781)

## What it does

- `/opportunities` opens a private, ephemeral setup flow.
- Users choose whether to opt in.
- Users choose Internships, Hackathons, or Both.
- Users choose Daily or Weekly delivery.
- Weekly digests are sent on Sundays.
- Digests are sent only via Discord DM.
- Every notification includes Preferences and Unsubscribe buttons.
- `/unsubscribe` stops all notification DMs immediately.
- SQLite stores only the Discord user ID, notification preferences, timestamps, source state, and delivery history.
- New items are deduplicated before delivery.
- The first successful source sync becomes a baseline, so existing listings are not blasted to users as if they were new.

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

## Scheduling behavior

The source poller checks for additions throughout the day. The digest scheduler runs after `DIGEST_HOUR_LOCAL` in `BOT_TIMEZONE` and records each daily or weekly scheduler run in SQLite so a restart does not cause the same scheduled run to execute twice.

Daily subscribers are checked every day. Weekly subscribers are checked on Sundays. If a student has no new undelivered opportunities, the bot sends nothing.

Each digest currently includes up to 10 new internships and up to 10 new hackathons. Additional undelivered items remain queued for a later digest.

## Privacy notes

The bot does not store Discord usernames, email addresses, message content, or public student profiles. It stores Discord user IDs only because Discord needs the user ID to deliver the DM and associate preferences with the correct account.

Users must explicitly opt in. They can change preferences with `/opportunities`, use the Preferences button in a DM, use the Unsubscribe button in a DM, or run `/unsubscribe`.

## Tests

Run:

```bash
pytest
```

The included tests cover preference storage, delivery deduplication, first-sync baseline behavior, and source parsing.
