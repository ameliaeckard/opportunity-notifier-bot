from __future__ import annotations

import discord

from bot.constants import BUG_REPORT_URL
from bot.database import Database
from bot.notifications import digest_embed, page_count
from bot.views.preferences import InterestView


class DigestPagerView(discord.ui.View):
    def __init__(self, database: Database, *, current_page: int = 0, total_pages: int = 1) -> None:
        super().__init__(timeout=None)
        self.database = database
        self.previous.disabled = current_page <= 0
        self.next.disabled = current_page >= total_pages - 1
        self.add_item(discord.ui.Button(label="Report Bug", style=discord.ButtonStyle.link, url=BUG_REPORT_URL, row=1))

    async def _batch(self, interaction: discord.Interaction):
        if not interaction.message:
            await interaction.response.send_message("This digest could not be identified.", ephemeral=True)
            return None
        batch = self.database.get_digest_by_message(interaction.message.id)
        if not batch:
            await interaction.response.send_message("This digest is no longer available.", ephemeral=True)
            return None
        if interaction.user.id != batch["discord_user_id"]:
            await interaction.response.send_message("This digest belongs to another user.", ephemeral=True)
            return None
        return batch

    async def _move(self, interaction: discord.Interaction, offset: int) -> None:
        batch = await self._batch(interaction)
        if not batch:
            return
        items = batch["items"]
        if not items:
            await interaction.response.send_message("This digest has no opportunities.", ephemeral=True)
            return
        total_pages = page_count(len(items))
        page = max(0, min(batch["current_page"] + offset, total_pages - 1))
        self.database.set_digest_page(batch["digest_id"], page)
        await interaction.response.edit_message(
            embed=digest_embed(batch["kind"], items, page, batch["frequency"]),
            view=DigestPagerView(self.database, current_page=page, total_pages=total_pages),
        )

    @discord.ui.button(label="Previous", style=discord.ButtonStyle.secondary, custom_id="scout:digest:previous", row=0)
    async def previous(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await self._move(interaction, -1)

    @discord.ui.button(label="Next", style=discord.ButtonStyle.primary, custom_id="scout:digest:next", row=0)
    async def next(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await self._move(interaction, 1)

    @discord.ui.button(label="Preferences", style=discord.ButtonStyle.secondary, custom_id="scout:digest:preferences", row=1)
    async def preferences(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        subscriber = self.database.get_subscriber(interaction.user.id)
        if not subscriber or not subscriber.opted_in:
            await interaction.response.send_message("You are not currently subscribed. Run `/opportunities` in a server to opt in.", ephemeral=True)
            return
        await interaction.response.send_message("What would you like to receive?", view=InterestView(interaction.user.id, self.database), ephemeral=True)

    @discord.ui.button(label="Unsubscribe", style=discord.ButtonStyle.danger, custom_id="scout:digest:unsubscribe", row=1)
    async def unsubscribe(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        self.database.opt_out(interaction.user.id)
        await interaction.response.send_message("You are unsubscribed. No more opportunity DMs will be sent.", ephemeral=True)


class PreviewPagerView(discord.ui.View):
    def __init__(self, owner_id: int, kind: str, items: list, current_page: int = 0) -> None:
        super().__init__(timeout=900)
        self.owner_id = owner_id
        self.kind = kind
        self.items = items
        self.current_page = current_page
        total_pages = page_count(len(items))
        self.previous.disabled = current_page <= 0
        self.next.disabled = current_page >= total_pages - 1
        self.add_item(discord.ui.Button(label="Report Bug", style=discord.ButtonStyle.link, url=BUG_REPORT_URL, row=1))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id == self.owner_id:
            return True
        await interaction.response.send_message("This admin preview belongs to another user.", ephemeral=True)
        return False

    async def _move(self, interaction: discord.Interaction, offset: int) -> None:
        total_pages = page_count(len(self.items))
        page = max(0, min(self.current_page + offset, total_pages - 1))
        await interaction.response.edit_message(
            embed=digest_embed(self.kind, self.items, page, "test"),
            view=PreviewPagerView(self.owner_id, self.kind, self.items, page),
        )

    @discord.ui.button(label="Previous", style=discord.ButtonStyle.secondary, row=0)
    async def previous(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await self._move(interaction, -1)

    @discord.ui.button(label="Next", style=discord.ButtonStyle.primary, row=0)
    async def next(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await self._move(interaction, 1)
