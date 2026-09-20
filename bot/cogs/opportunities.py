from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from bot.database import Database
from bot.notifications import digest_embed
from bot.source_service import SourceService
from bot.views.digests import PreviewPagerView
from bot.views.preferences import OptInView, PreferencesHomeView


class OpportunitiesCog(commands.Cog):
    def __init__(self, bot: commands.Bot, database: Database, source_service: SourceService) -> None:
        self.bot = bot
        self.database = database
        self.source_service = source_service

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
        await interaction.response.send_message("You are unsubscribed. No more opportunity DMs will be sent.", ephemeral=True)

    @app_commands.command(name="testrecent", description="Admin test of Scout's current internship and hackathon sources.")
    @app_commands.guild_only()
    @app_commands.default_permissions(administrator=True)
    async def testrecent(self, interaction: discord.Interaction) -> None:
        if not interaction.permissions.administrator:
            await interaction.response.send_message("This command is only available to server administrators.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True, thinking=True)
        preview = await self.source_service.preview_recent(limit=5)
        sent = []
        try:
            internships = preview.get("internship", [])
            if internships:
                await interaction.user.send(
                    embed=digest_embed("internship", internships[0], 0, len(internships), "test"),
                    view=PreviewPagerView(interaction.user.id, "internship", internships),
                )
                sent.append(f"{len(internships)} recent internships")

            hackathons = preview.get("hackathon", [])
            if hackathons:
                await interaction.user.send(
                    embed=digest_embed("hackathon", hackathons[0], 0, len(hackathons), "test"),
                    view=PreviewPagerView(interaction.user.id, "hackathon", hackathons),
                )
                sent.append(f"{len(hackathons)} upcoming hackathons")
        except discord.Forbidden:
            await interaction.followup.send("Scout found current opportunities, but Discord blocked the test DM. Make sure you can receive DMs from this server.", ephemeral=True)
            return
        except discord.HTTPException:
            await interaction.followup.send("Scout reached Discord but could not send the test DM. Check the Railway logs for the Discord API error.", ephemeral=True)
            return

        if sent:
            await interaction.followup.send(f"Live source check complete. I sent you separate test DMs for {' and '.join(sent)}. This test does not mark anything as delivered.", ephemeral=True)
        else:
            await interaction.followup.send("The live source check completed, but neither source returned usable current opportunities.", ephemeral=True)
