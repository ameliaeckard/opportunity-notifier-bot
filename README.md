# Scout

Scout is a Discord bot for opt-in internship and hackathon notifications.

## Current behavior

- `/opportunities` opens the private notification setup flow.
- `/postopportunities` lets a server manager post Scout's reusable signup panel.
- `/unsubscribe` immediately stops notification DMs.
- `/testrecent` lets a server administrator do an on-demand live source preview without affecting delivery history.
- `/send` lets a server administrator manually send the current digest to all opted-in subscribers.
- Scout's slash commands are registered globally, so it works in every server where the bot is installed.
- Users choose Internships, Hackathons, or Both, and Daily or Weekly delivery.
- Digests are sent privately by DM and show 5 listings per page with Previous/Next controls.
- There is no 25-listing cap on scheduled digests.

## Noon schedule

Scout refreshes its sources once per day at **12:00 PM** in `BOT_TIMEZONE` (default `America/New_York`).

A "new opportunity" means an opportunity Scout first discovers from its sources.

Daily subscribers receive opportunities Scout first saw during:

```text
previous day at 12:00 PM < discovered_at <= current day at 12:00 PM
```

Weekly subscribers receive opportunities Scout first saw during:

```text
previous Monday at 12:00 PM < discovered_at <= current Monday at 12:00 PM
```

The scheduled noon refresh stamps newly discovered records at the noon boundary before digest selection. This means an item fetched a few seconds after the scheduler wakes up still belongs to the digest being sent at that noon boundary.

Listings already delivered to a user are protected by the delivery table and are not duplicated on retry or manual `/send`.

## Student Added webhook

Set `STUDENT_ADDED_WEBHOOK_URL` to a Discord webhook URL. When a student goes from unsubscribed/not subscribed to subscribed, Scout sends a `Student Added!` webhook containing the student's Discord identity, the server where they completed signup, selected categories, and frequency. Editing existing preferences does not trigger the webhook.

## Multi-server commands

Scout always performs a global application-command sync. `DISCORD_GUILD_ID` is retained only as a one-deployment compatibility setting: if an old single-server command deployment exists and this value is still present in Railway, Scout clears that legacy guild command copy and then syncs the global commands.

## Sources

- Internships: SimplifyJobs Summer 2027 Internships `dev` listings JSON.
- Hackathons: Hackalendar JSON API, with its documented MCP search fallback.
- Scout does not scrape Devpost.

## Railway / environment

```text
DISCORD_TOKEN=
DISCORD_GUILD_ID=
DATABASE_PATH=/data/opportunity_notifier.db
BOT_TIMEZONE=America/New_York
DAILY_DIGEST_HOUR_LOCAL=12
STUDENT_ADDED_WEBHOOK_URL=
LOG_LEVEL=INFO
```

For persistent subscribers and delivery history, keep the Railway volume mounted at `/data` and keep:

```text
DATABASE_PATH=/data/opportunity_notifier.db
```

Keep the service at one replica while using SQLite.

## Local setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m bot.main
```

Windows PowerShell activation:

```powershell
.venv\Scripts\Activate.ps1
```

Run tests with:

```bash
python -m pytest
```
