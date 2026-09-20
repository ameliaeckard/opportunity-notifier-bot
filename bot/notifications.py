from __future__ import annotations

from datetime import datetime

import discord

from bot.constants import HACKALENDAR_URL, SIMPLIFY_REPO_URL
from bot.models import Opportunity


def _format_date(value: str | None) -> str | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.strftime("%B %d, %Y").replace(" 0", " ")
    except ValueError:
        return value


def digest_embed(kind: str, item: Opportunity, page: int, total: int, frequency: str) -> discord.Embed:
    if kind == "internship":
        embed = discord.Embed(title=f"Internships: {total} new")
        embed.add_field(name=item.organization, value=item.title, inline=False)
        embed.add_field(name="Location", value=item.location, inline=False)
        embed.add_field(name="Source", value=f"[SimplifyJobs Summer 2027 Internships]({SIMPLIFY_REPO_URL})", inline=False)
    elif kind == "hackathon":
        embed = discord.Embed(title=f"Hackathons: {total} new")
        start = _format_date(item.start_date)
        end = _format_date(item.end_date)
        date_line = f"{start} to {end}" if start and end else start or end or "Date not listed"
        embed.add_field(name=item.organization, value=item.title, inline=False)
        embed.add_field(name="Dates", value=date_line, inline=False)
        embed.add_field(name="Location", value=item.location, inline=False)
        embed.add_field(name="Source", value=f"[Hackalendar]({HACKALENDAR_URL})", inline=False)
    else:
        raise ValueError("kind must be internship or hackathon")

    if frequency == "daily":
        label = "Daily digest"
    elif frequency == "weekly":
        label = "Weekly digest"
    else:
        label = "Admin test"
    embed.set_footer(text=f"{label} • Page {page + 1} of {total} • Report a bug below")
    return embed
