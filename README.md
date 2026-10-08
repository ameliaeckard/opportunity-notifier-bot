# Scout _(opportunity-notifier-bot)_

Lab report: [Scout Opportunity Notifier](https://lab.ameliaeckard.com/notes/2026-10-08-scout)

An opt-in opportunity delivery service for personalized internship and hackathon discovery through Discord.

## Background

Scout separates source ingestion from delivery so opportunities can be normalized, deduplicated, stored, and sent on different schedules without repeatedly notifying the same person.

## Install

```bash
git clone https://github.com/ameliaeckard/opportunity-notifier-bot.git
cd opportunity-notifier-bot
python -m venv .venv
pip install -r requirements.txt
```

Copy `.env.example` and configure the Discord token, database path, timezone, and optional webhook settings.

## Usage

```bash
python -m bot.main
```

Run tests with:

```bash
python -m pytest
```

Users can opt into internships, hackathons, or both and choose daily or weekly private digests. SQLite stores preferences, source state, and delivery history so retries do not duplicate messages.

## Maintainer

[Amelia Eckard](https://github.com/ameliaeckard)

## Contributing

Issues are welcome for bugs or documentation problems. Please open an issue before a substantial pull request.
