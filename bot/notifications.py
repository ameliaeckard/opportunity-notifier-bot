from __future__ import annotations

import math
from datetime import datetime

import discord

from bot.constants import HACKALENDAR_URL, SIMPLIFY_REPO_URL
from bot.models import Opportunity


PAGE_SIZE = 5


def _format_date(value: str | None) -> str | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.strftime("%B %d, %Y").replace(" 0", " ")
    except ValueError:
        return value


def page_count(total_items: int) -> int:
    return max(1, math.ceil(total_items / PAGE_SIZE))


def digest_embed(kind: str, items: list[Opportunity], page: int, frequency: str) -> discord.Embed:
    total = len(items)
    total_pages = page_count(total)
    safe_page = max(0, min(page, total_pages - 1))
    start_index = safe_page * PAGE_SIZE
    page_items = items[start_index:start_index + PAGE_SIZE]

    if kind == "internship":
        embed = discord.Embed(title=f"Internships: {total} new" if frequency != "test" else f"Recent Internships: {total}")
        for offset, item in enumerate(page_items, start=start_index + 1):
            embed.add_field(
                name=f"{offset}. {item.organization}",
                value=f"**{item.title}**\n{item.location}\n[View Posting]({item.url})",
                inline=False,
            )
        embed.add_field(name="Source", value=f"[SimplifyJobs Summer 2027 Internships]({SIMPLIFY_REPO_URL})", inline=False)
    elif kind == "hackathon":
        embed = discord.Embed(title=f"Hackathons: {total} new" if frequency != "test" else f"Upcoming Hackathons: {total}")
        for offset, item in enumerate(page_items, start=start_index + 1):
            start = _format_date(item.start_date)
            end = _format_date(item.end_date)
            date_line = f"{start} to {end}" if start and end else start or end or "Date not listed"
            organizer = f"**{item.title}**\n" if item.title and item.title != "Hackathon" else ""
            embed.add_field(
                name=f"{offset}. {item.organization}",
                value=f"{organizer}{date_line}\n{item.location}\n[View Event]({item.url})",
                inline=False,
            )
        embed.add_field(name="Source", value=f"[Hackalendar]({HACKALENDAR_URL})", inline=False)
    else:
        raise ValueError("kind must be internship or hackathon")

    if frequency == "daily":
        label = "Daily digest"
    elif frequency == "weekly":
        label = "Weekly digest"
    else:
        label = "Admin test"
    embed.set_footer(text=f"{label} • Page {safe_page + 1} of {total_pages} • Report a bug below")
    return embed
