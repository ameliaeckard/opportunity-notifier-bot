from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from bot.database import Database
from bot.notifications import digest_embed
from bot.source_service import SourceService
from bot.views.digests import PreviewPagerView
from bot.views.preferences import PublicOpportunitySignupView, opportunity_prompt_embed, send_opportunity_setup


class OpportunitiesCog(commands.Cog):
    def __init__(self, bot: commands.Bot, database: Database, source_service: SourceService) -> None:
        self.bot = bot
        self.database = database
        self.source_service = source_service

    @app_commands.command(name="opportunities", description="Set or review your private opportunity notification preferences.")
    async def opportunities(self, interaction: discord.Interaction) -> None:
        await send_opportunity_setup(interaction, self.database)

    @app_commands.command(name="postopportunities", description="Post Scout's reusable opportunity opt-in panel in this channel.")
    @app_commands.guild_only()
    @app_commands.default_permissions(manage_guild=True)
    async def postopportunities(self, interaction: discord.Interaction) -> None:
        if not interaction.permissions.manage_guild:
            await interaction.response.send_message("This command requires Manage Server permission.", ephemeral=True)
            return
        await interaction.response.send_message(
            embed=opportunity_prompt_embed(),
            view=PublicOpportunitySignupView(self.database),
        )

    @app_commands.command(name="unsubscribe", description="Stop all opportunity notification DMs.")
    async def unsubscribe(self, interaction: discord.Interaction) -> None:
        self.database.opt_out(interaction.user.id)
        await interaction.response.send_message("You are unsubscribed. No more opportunity DMs will be sent.", ephemeral=True)

    @app_commands.command(name="testrecent", description="Admin test of Scout's live internship and hackathon sources.")
    @app_commands.describe(count="How many recent listings per category to preview, from 5 to 25.")
    @app_commands.guild_only()
    @app_commands.default_permissions(administrator=True)
    async def testrecent(self, interaction: discord.Interaction, count: app_commands.Range[int, 5, 25] = 10) -> None:
        if not interaction.permissions.administrator:
            await interaction.response.send_message("This command is only available to server administrators.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True, thinking=True)
        preview = await self.source_service.preview_recent(limit=count)
        sent = []
        missing = []
        try:
            internships = preview.get("internship", [])
            if internships:
                await interaction.user.send(
                    embed=digest_embed("internship", internships, 0, "test"),
                    view=PreviewPagerView(interaction.user.id, "internship", internships),
                )
                sent.append(f"{len(internships)} recent internships")
            else:
                missing.append("internships")

            hackathons = preview.get("hackathon", [])
            if hackathons:
                await interaction.user.send(
                    embed=digest_embed("hackathon", hackathons, 0, "test"),
                    view=PreviewPagerView(interaction.user.id, "hackathon", hackathons),
                )
                sent.append(f"{len(hackathons)} upcoming hackathons")
            else:
                missing.append("hackathons")
        except discord.Forbidden:
            await interaction.followup.send("Scout found current opportunities, but Discord blocked the test DM. Make sure you can receive DMs from this server.", ephemeral=True)
            return
        except discord.HTTPException:
            await interaction.followup.send("Scout reached Discord but could not send the test DM. Check the Railway logs for the Discord API error.", ephemeral=True)
            return

        if sent:
            note = f"Live source check complete. I sent you separate test DMs for {' and '.join(sent)}. Each page shows up to 5 listings. This test does not mark anything as delivered."
            if missing:
                note += f" No usable {' or '.join(missing)} were returned, so check the Railway source logs."
            await interaction.followup.send(note, ephemeral=True)
        else:
            await interaction.followup.send("The live source check completed, but neither source returned usable current opportunities. Check the Railway source logs.", ephemeral=True)
