from __future__ import annotations

import discord

from bot.constants import BUG_REPORT_URL
from bot.database import Database


def opportunity_prompt_embed() -> discord.Embed:
    embed = discord.Embed(
        title="Opportunity Notifications",
        description="Would you like private DMs when new internships or hackathons are found?",
    )
    embed.set_footer(text="You must explicitly opt in before any notification is sent.")
    return embed


def preferences_summary_embed(subscriber) -> discord.Embed:
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
    return embed


async def send_opportunity_setup(interaction: discord.Interaction, database: Database) -> None:
    subscriber = database.get_subscriber(interaction.user.id)
    if subscriber and subscriber.opted_in:
        await interaction.response.send_message(
            embed=preferences_summary_embed(subscriber),
            view=PreferencesHomeView(interaction.user.id, database),
            ephemeral=True,
        )
        return

    await interaction.response.send_message(
        embed=opportunity_prompt_embed(),
        view=OptInView(interaction.user.id, database),
        ephemeral=True,
    )


class OwnedView(discord.ui.View):
    def __init__(self, owner_id: int, *, timeout: float = 180) -> None:
        super().__init__(timeout=timeout)
        self.owner_id = owner_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id == self.owner_id:
            return True
        await interaction.response.send_message("This preference menu belongs to another user.", ephemeral=True)
        return False


class OptInView(OwnedView):
    def __init__(self, owner_id: int, database: Database) -> None:
        super().__init__(owner_id)
        self.database = database

    @discord.ui.button(label="Yes, send me notifications", style=discord.ButtonStyle.primary)
    async def yes(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await interaction.response.edit_message(
            content="What would you like to receive?",
            embed=None,
            view=InterestView(self.owner_id, self.database),
        )

    @discord.ui.button(label="No thanks", style=discord.ButtonStyle.secondary)
    async def no(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        self.database.opt_out(self.owner_id)
        await interaction.response.edit_message(
            content="No notifications will be sent. You can run `/opportunities` whenever you want to opt in.",
            embed=None,
            view=None,
        )


class InterestView(OwnedView):
    def __init__(self, owner_id: int, database: Database) -> None:
        super().__init__(owner_id)
        self.database = database

    async def _choose(self, interaction: discord.Interaction, internships: bool, hackathons: bool) -> None:
        await interaction.response.edit_message(
            content="How often would you like your private digest?",
            embed=None,
            view=FrequencyView(self.owner_id, self.database, internships, hackathons),
        )

    @discord.ui.button(label="Internships", style=discord.ButtonStyle.secondary)
    async def internships(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await self._choose(interaction, True, False)

    @discord.ui.button(label="Hackathons", style=discord.ButtonStyle.secondary)
    async def hackathons(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await self._choose(interaction, False, True)

    @discord.ui.button(label="Both", style=discord.ButtonStyle.primary)
    async def both(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await self._choose(interaction, True, True)


class FrequencyView(OwnedView):
    def __init__(self, owner_id: int, database: Database, internships: bool, hackathons: bool) -> None:
        super().__init__(owner_id)
        self.database = database
        self.internships = internships
        self.hackathons = hackathons

    async def _save(self, interaction: discord.Interaction, frequency: str) -> None:
        self.database.save_preferences(
            self.owner_id,
            internships=self.internships,
            hackathons=self.hackathons,
            frequency=frequency,
        )
        label = "Daily" if frequency == "daily" else "Weekly on Sundays"
        categories = []
        if self.internships:
            categories.append("internships")
        if self.hackathons:
            categories.append("hackathons")
        await interaction.response.edit_message(
            content=f"Preferences saved. You will receive {label.lower()} private DMs for {' and '.join(categories)} when new opportunities are available.",
            embed=None,
            view=None,
        )

    @discord.ui.button(label="Daily", style=discord.ButtonStyle.primary)
    async def daily(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await self._save(interaction, "daily")

    @discord.ui.button(label="Weekly", style=discord.ButtonStyle.secondary)
    async def weekly(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await self._save(interaction, "weekly")


class PreferencesHomeView(OwnedView):
    def __init__(self, owner_id: int, database: Database) -> None:
        super().__init__(owner_id)
        self.database = database

    @discord.ui.button(label="Change preferences", style=discord.ButtonStyle.primary)
    async def change(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await interaction.response.edit_message(
            content="What would you like to receive?",
            embed=None,
            view=InterestView(self.owner_id, self.database),
        )

    @discord.ui.button(label="Unsubscribe", style=discord.ButtonStyle.danger)
    async def unsubscribe(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        self.database.opt_out(self.owner_id)
        await interaction.response.edit_message(
            content="You are unsubscribed. No more opportunity DMs will be sent.",
            embed=None,
            view=None,
        )


class PublicOpportunitySignupView(discord.ui.View):
    def __init__(self, database: Database) -> None:
        super().__init__(timeout=None)
        self.database = database

    @discord.ui.button(
        label="Set up notifications",
        style=discord.ButtonStyle.primary,
        custom_id="scout:public:opportunity_setup",
    )
    async def setup(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await send_opportunity_setup(interaction, self.database)


class NotificationControlsView(discord.ui.View):
    def __init__(self, database: Database) -> None:
        super().__init__(timeout=None)
        self.database = database
        self.add_item(discord.ui.Button(label="Report Bug", style=discord.ButtonStyle.link, url=BUG_REPORT_URL, row=1))

    @discord.ui.button(
        label="Preferences",
        style=discord.ButtonStyle.secondary,
        custom_id="opportunity_notifier:preferences",
    )
    async def preferences(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        subscriber = self.database.get_subscriber(interaction.user.id)
        if not subscriber or not subscriber.opted_in:
            await interaction.response.send_message(
                "You are not currently subscribed. Run `/opportunities` in the server to opt in.",
                ephemeral=True,
            )
            return
        await interaction.response.send_message(
            "What would you like to receive?",
            view=InterestView(interaction.user.id, self.database),
            ephemeral=True,
        )

    @discord.ui.button(
        label="Unsubscribe",
        style=discord.ButtonStyle.danger,
        custom_id="opportunity_notifier:unsubscribe",
    )
    async def unsubscribe(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        self.database.opt_out(interaction.user.id)
        await interaction.response.send_message(
            "You are unsubscribed. No more opportunity DMs will be sent.",
            ephemeral=True,
        )
