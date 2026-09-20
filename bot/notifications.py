from __future__ import annotations

from datetime import datetime

import discord

from bot.models import Opportunity


HACKATHON_SOURCE = "https://hackalendar.com"
SIMPLIFY_REPO = "https://github.com/SimplifyJobs/Summer2027-Internships"


def _format_date(value: str | None) -> str | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.strftime("%B %d, %Y").replace(" 0", " ")
    except ValueError:
        return value


def internship_embed(items: list[Opportunity]) -> discord.Embed:
    embed = discord.Embed(title="New Opportunities", description=f"**Internships: {len(items)} new**")
    for item in items:
        embed.add_field(
            name=item.organization,
            value=f"{item.title}\n{item.location}\n[View Posting]({item.url})",
            inline=False,
        )
    embed.add_field(name="Source", value=f"[SimplifyJobs Summer 2027 Internships]({SIMPLIFY_REPO})", inline=False)
    return embed


def hackathon_embed(items: list[Opportunity]) -> discord.Embed:
    embed = discord.Embed(title="New Opportunities", description=f"**Hackathons: {len(items)} new**")
    for item in items:
        start = _format_date(item.start_date)
        end = _format_date(item.end_date)
        date_line = f"{start} to {end}" if start and end else start or end or "Date not listed"
        embed.add_field(
            name=item.organization,
            value=f"{date_line}\n{item.location}\n[View Event]({item.url})",
            inline=False,
        )
    embed.add_field(name="Source", value=f"[Hackalendar]({HACKATHON_SOURCE})", inline=False)
    return embed
