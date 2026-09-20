<img width="2172" height="724" alt="scoutbanner" src="https://github.com/user-attachments/assets/e5960c47-2fc9-4d52-982a-a1053c801990" />

# Scout

Discord bot that lets users opt in to personalized internship and hackathon notifications with daily or weekly digests.

Users explicitly opt in, choose the opportunities they want to receive, and select either daily or weekly private Discord digests. Notifications are sent by DM and include quick access to preferences, unsubscribe controls, and bug reporting.

### Add Scout to your server

Want Scout in your server? [Add Scout to your server](https://discord.com/oauth2/authorize?client_id=1551281451536752781&permissions=19456&integration_type=0&scope=bot+applications.commands)

Found a problem? [Report a bug](https://ameliaeckard.com/bug/)

## What it does

- `/opportunities` opens a private, ephemeral setup flow.
- `/postopportunities` lets a server manager post a persistent public opt-in panel. Users click the button and complete the same setup privately.
- Users choose Internships, Hackathons, or Both.
- Users choose Daily or Weekly delivery.
- Weekly digests are sent on Sundays.
- Digests are sent only via Discord DM.
- Internship and hackathon digests are sent as separate messages.
- Each digest works like a small book with Previous and Next controls, one opportunity per page, and a direct View Posting or View Event button.
- Digest controls include Preferences, Unsubscribe, and Report Bug.
- `/unsubscribe` stops all notification DMs immediately.
- `/testrecent` lets a server administrator run a live source test and receive separate private preview DMs without marking anything as delivered.
- SQLite stores Discord user IDs, preferences, source state, delivery history, and digest navigation state.
- New items are deduplicated before delivery.
- The first successful source sync becomes a baseline, so existing listings are not sent as if they were new.

## How source checking works

Scout does not continuously search the web. It checks its structured sources periodically, with a default interval of 60 minutes, and compares stable source IDs against the records already stored in SQLite. Only unseen opportunities are added as new.

Scout also performs one source refresh immediately before a scheduled digest so the daily or Sunday message uses the latest available source data. The first scheduled background poll is delayed after startup so the initial baseline sync is not immediately repeated.

For admin testing, `/testrecent` performs a live read without changing delivery history. It previews the most recently updated internship listings and the next upcoming hackathons.

## Data sources

### Internships

Internships are read from the public `dev` branch of [SimplifyJobs Summer 2027 Internships](https://github.com/SimplifyJobs/Summer2027-Internships), using its structured listings JSON.

### Hackathons

Hackathons are read from the public [Hackalendar API](https://hackalendar.com/api). It provides upcoming, human-verified events as structured data without an API key and links users back to organizer registration pages.

Scout does not scrape Devpost.

## Discord commands

- `/opportunities`: Opt in, review preferences, or change notification settings.
- `/unsubscribe`: Stop all Scout notification DMs.
- `/testrecent`: Administrator-only live test of both opportunity sources. The results are sent privately to the administrator and do not affect subscriber delivery state.

## Local setup

1. Create a Discord application and bot in the Discord Developer Portal.
2. Add the bot to your server with the `bot` and `applications.commands` scopes.
3. Copy `.env.example` to `.env`.
4. Put your bot token in `DISCORD_TOKEN`.
5. Optionally set `DISCORD_GUILD_ID` to your server ID while testing. Guild-scoped commands appear quickly. Leave it blank for global command sync.
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

```text
DISCORD_TOKEN=
DISCORD_GUILD_ID=
DATABASE_PATH=./data/opportunity_notifier.db
BOT_TIMEZONE=America/New_York
DIGEST_HOUR_LOCAL=9
SOURCE_POLL_MINUTES=60
LOG_LEVEL=INFO
```

`SOURCE_POLL_MINUTES` must be at least 15 minutes. The default is 60 minutes.

## Railway

Scout is configured for Railway through `railway.json` and starts with:

```text
python -m bot.main
```

For SQLite persistence, add a Railway volume mounted at `/data` and set:

```text
DATABASE_PATH=/data/opportunity_notifier.db
```

Keep the service at one replica while using SQLite.

Scout also handles temporary Discord startup failures with exponential backoff. Instead of immediately crashing and causing a rapid Railway restart loop, it waits 60 seconds and increases the delay up to 15 minutes between retry attempts. Invalid bot tokens still fail immediately so configuration errors are visible.

## Scheduling behavior

Scout checks its structured sources on a configurable interval, which defaults to once per hour. It does not continuously scrape websites. SimplifyJobs is fetched as one structured listings file and deduplicated by listing ID. Hackalendar is fetched from its structured API, with its documented read-only MCP search used as a fallback if the JSON response cannot be parsed.

Daily subscribers are checked once per day after `DIGEST_HOUR_LOCAL`. Weekly subscribers are checked on Sundays. If a user has no new undelivered opportunities, Scout sends nothing.

Each category can include up to 25 new opportunities per digest. Scout shows up to 5 listings on each page, and Previous and Next move through the digest five listings at a time. If a user subscribes to both categories, Scout sends one Internship DM and one Hackathon DM.


### Admin source test

Server administrators can run `/testrecent` to perform a live source check without notifying subscribers or marking listings as delivered. The command accepts a count from 5 to 25 per category and sends separate Internship and Hackathon preview DMs using the same five-listings-per-page layout as real digests.

## Privacy

Scout does not store Discord usernames, email addresses, message content, or public user profiles. It stores Discord user IDs because Discord requires them to associate preferences and deliver private notifications.

Users must explicitly opt in and can unsubscribe at any time.

## Tests

Run:

```bash
python -m pytest
```

Tests cover preference storage, delivery deduplication, first-sync baseline behavior, digest navigation persistence, source parsing, and digest formatting.

## Notes

- No GitHub Actions are used.
- Logging goes to stdout for Railway.
- Scout does not require the privileged Message Content intent.
