from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from bot.database import Database
from bot.views.preferences import OptInView, PreferencesHomeView


class OpportunitiesCog(commands.Cog):
    def __init__(self, bot: commands.Bot, database: Database) -> None:
        self.bot = bot
        self.database = database

    @app_commands.command(name="opportunities", description="Set or review your private opportunity notification preferences.")
    async def opportunities(self, interaction: discord.Interaction) -> None:
        subscriber = self.database.get_subscriber(interaction.user.id)
        if subscriber and subscriber.opted_in:
            categories = []
            if subscriber.internships_enabled:
                categories.append("Internships")
            if subscriber.hackathons_enabled:
                categories.append("Hackathons")
            frequency = "Daily" if subscriber.frequency == "daily" else "Weekly on Sundays"
            embed = discord.Embed(title="Opportunity Notifications")
            embed.add_field(name="Receiving", value=" and ".join(categories) or "Nothing", inline=False)
            embed.add_field(name="Frequency", value=frequency, inline=False)
            embed.set_footer(text="Only your Discord user ID and notification preferences are stored.")
            await interaction.response.send_message(
                embed=embed,
                view=PreferencesHomeView(interaction.user.id, self.database),
                ephemeral=True,
            )
            return

        embed = discord.Embed(
            title="Opportunity Notifications",
            description="Would you like private DMs when new internships or hackathons are found?",
        )
        embed.set_footer(text="You must explicitly opt in before any notification is sent.")
        await interaction.response.send_message(
            embed=embed,
            view=OptInView(interaction.user.id, self.database),
            ephemeral=True,
        )

    @app_commands.command(name="unsubscribe", description="Stop all opportunity notification DMs.")
    async def unsubscribe(self, interaction: discord.Interaction) -> None:
        self.database.opt_out(interaction.user.id)
        await interaction.response.send_message(
            "You are unsubscribed. No more opportunity DMs will be sent.",
            ephemeral=True,
        )
