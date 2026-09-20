from __future__ import annotations

import discord

from bot.database import Database


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


class NotificationControlsView(discord.ui.View):
    def __init__(self, database: Database) -> None:
        super().__init__(timeout=None)
        self.database = database

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
