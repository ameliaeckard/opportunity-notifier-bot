from __future__ import annotations

import logging

import aiohttp
import discord


logger = logging.getLogger(__name__)


async def send_student_added_webhook(
    webhook_url: str | None,
    user: discord.User | discord.Member,
    guild: discord.Guild | None,
    categories: list[str],
    frequency: str,
) -> None:
    if not webhook_url:
        return

    embed = discord.Embed(
        title="Student Added!",
        description="A student opted in to Scout opportunity notifications.",
    )
    embed.add_field(name="Student", value=f"{user} (`{user.id}`)", inline=False)
    if guild is not None:
        embed.add_field(name="Server", value=f"{guild.name} (`{guild.id}`)", inline=False)
    else:
        embed.add_field(name="Server", value="Unknown / DM context", inline=False)
    embed.add_field(name="Receiving", value=" and ".join(categories), inline=True)
    embed.add_field(name="Frequency", value=frequency, inline=True)

    try:
        async with aiohttp.ClientSession() as session:
            webhook = discord.Webhook.from_url(webhook_url, session=session)
            await webhook.send(embed=embed, username="Scout", allowed_mentions=discord.AllowedMentions.none())
    except (discord.HTTPException, ValueError, aiohttp.ClientError):
        logger.exception("Could not send the Student Added webhook notification.")
