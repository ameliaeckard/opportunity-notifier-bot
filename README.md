# Scout

Scout is a Discord bot for opt-in internship and hackathon notifications.

## Current behavior

- `/opportunities` opens the private notification setup flow.
- `/postopportunities` lets a server manager post Scout's reusable signup panel.
- `/unsubscribe` immediately stops notification DMs.
- `/testrecent` lets a server administrator do an on-demand live source preview without affecting delivery history.
- Scout's slash commands are registered **globally**, so it works in every server where the bot is installed.
- Users choose Internships, Hackathons, or Both, and Daily or Weekly delivery.
- Digests are sent privately by DM and show **5 listings per page** with Previous/Next controls.
- There is no 25-listing cap on scheduled digests; every matching undelivered item in the digest window is retained in the paginated digest.

## Noon schedule

Scout no longer polls its sources every 15 or 60 minutes.

The automatic source refresh happens once per day at **12:00 PM** in `BOT_TIMEZONE` (default `America/New_York`). Daily internship digests use the source listing's own SimplifyJobs `date_posted` Unix timestamp and include postings in the window:

```text
previous day at 12:00 PM <= date_posted < current day at 12:00 PM
```

Weekly subscribers receive the equivalent seven-day Sunday-noon window. Hackalendar does not provide a reliable posting-created timestamp, so hackathons use Scout's first-discovered timestamp for their daily/weekly window.

If Scout restarts after noon before that day's digest completed, the scheduler catches up. The scheduler key includes the noon schedule, so an older 9 AM run marker cannot block the new noon run.

Temporary Discord/API send failures leave the scheduled run pending so Scout can retry. Listings already delivered are protected by the delivery table and are not duplicated on retry.

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

The old `DIGEST_HOUR_LOCAL` and `SOURCE_POLL_MINUTES` values are no longer used by this build. You can remove them from Railway after replacing the code.

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
