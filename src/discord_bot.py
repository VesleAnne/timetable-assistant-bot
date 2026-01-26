from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

import discord
from discord import app_commands

from .engine import Engine, DiscordMessageContext
from .models import Platform
from .storage import SQLiteStorage

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DiscordBotSettings:
    token: str
    sqlite_path: str



class MonitorAddView(discord.ui.View):
    def __init__(self, storage: SQLiteStorage, guild_id: str) -> None:
        super().__init__(timeout=60)
        self.storage = storage
        self.guild_id = guild_id

    @discord.ui.select(
        cls=discord.ui.ChannelSelect,
        channel_types=[discord.ChannelType.text],
        placeholder="Select channels to monitor...",
        min_values=1,
        max_values=10,
    )
    async def channel_select(self, interaction: discord.Interaction, select: discord.ui.ChannelSelect):
        if not interaction.guild:
            await interaction.response.send_message("This command must be used in a server.", ephemeral=True)
            return

        channels = select.values
        for ch in channels:
            self.storage.discord_add_monitored_channel(str(interaction.guild.id), str(ch.id))

        channel_mentions = ", ".join(ch.mention for ch in channels)
        await interaction.response.send_message(
            f"✅ Monitoring enabled for: {channel_mentions}",
            ephemeral=True,
        )
        self.stop()

class MonitorRemoveView(discord.ui.View):
    def __init__(self, storage: SQLiteStorage, guild_id: str) -> None:
        super().__init__(timeout=60)
        self.storage = storage
        self.guild_id = guild_id

        monitored = storage.discord_list_monitored_channels(guild_id)
        options: list[discord.SelectOption] = []

        for cid in monitored[:25]:  # Discord select option limit
            options.append(discord.SelectOption(label=f"#{cid}", value=cid))

        if options:
            self.add_item(
                discord.ui.Select(
                    placeholder="Select monitored channels to remove...",
                    min_values=1,
                    max_values=min(10, len(options)),
                    options=options,
                )
            )

    @discord.ui.select()  # type: ignore
    async def select_callback(self, interaction: discord.Interaction, select: discord.ui.Select):
        if not interaction.guild:
            await interaction.response.send_message("This command must be used in a server.", ephemeral=True)
            return

        removed = []
        for cid in select.values:
            self.storage.discord_remove_monitored_channel(str(interaction.guild.id), str(cid))
            removed.append(f"<#{cid}>")

        await interaction.response.send_message(
            f"🛑 Monitoring disabled for: {', '.join(removed)}",
            ephemeral=True,
        )
        self.stop()


class ConvertForMeView(discord.ui.View):
    """
    The public view with a single button.
    The bot message is sent as a reply to the original user message.
    When clicked, we fetch the referenced original message and convert for the clicker.
    """

    def __init__(self, engine: Engine) -> None:
        super().__init__(timeout=None)
        self.engine = engine

    @discord.ui.button(label="Convert for me", style=discord.ButtonStyle.primary, custom_id="convert_for_me")
    async def convert_for_me(self, interaction: discord.Interaction, button: discord.ui.Button):
        # The bot message should be a reply to the original time message
        if not interaction.message or not interaction.channel:
            await interaction.response.send_message("Cannot find original message context.", ephemeral=True)
            return

        if not interaction.message.reference or not interaction.message.reference.message_id:
            await interaction.response.send_message("Cannot find the message to convert.", ephemeral=True)
            return

        try:
            original_msg = await interaction.channel.fetch_message(interaction.message.reference.message_id)
        except Exception:
            await interaction.response.send_message("Could not fetch the original message.", ephemeral=True)
            return

        clicker_id = str(interaction.user.id)
        original_sender_id = str(original_msg.author.id)
        original_text = original_msg.content or ""

        result = self.engine.discord_build_ephemeral_conversion_for_clicker(
            original_message_text=original_text,
            original_sender_id=original_sender_id,
            clicking_user_id=clicker_id,
        )

        if result is None:
            await interaction.response.send_message("No time mentions found.", ephemeral=True)
            return

        await interaction.response.send_message(result.text, ephemeral=True)


class DiscordBot(discord.Client):
    """
    Discord adapter (MVP).
    Uses discord.py 2.x + app_commands (slash commands) + Views (buttons/selectors).
    """

    def __init__(self, settings: DiscordBotSettings) -> None:
        intents = discord.Intents.default()
        intents.message_content = True  # REQUIRED for reading messages
        intents.guilds = True
        intents.messages = True

        super().__init__(intents=intents)

        self.settings = settings
        self.storage = SQLiteStorage(settings.sqlite_path)
        self.engine = Engine(self.storage)

        self.tree = app_commands.CommandTree(self)

        # Register command groups
        self.monitor_group = app_commands.Group(name="monitor", description="Configure monitored channels (admin only)")
        self.tz_group = app_commands.Group(name="tz", description="Manage your timezone")
        self.dm_group = app_commands.Group(name="dm", description="(Not used on Discord MVP)")
        self.tree.add_command(self.monitor_group)
        self.tree.add_command(self.tz_group)

        self._register_commands()

    async def setup_hook(self) -> None:
        """
        Called when bot starts (event loop is running).
        Register persistent views and sync commands.
        """
        # Now we can add the view (event loop exists)
        self.add_view(ConvertForMeView(self.engine))
        
        # Sync slash commands with Discord
        await self.tree.sync()
        logger.info("Discord commands synced")


    def _register_commands(self) -> None:
        # ---- /monitor add/remove/list (admins only) ----

        @self.monitor_group.command(name="add", description="Add monitored channels")
        async def monitor_add(interaction: discord.Interaction):
            if not interaction.guild:
                await interaction.response.send_message("Use this command in a server.", ephemeral=True)
                return

            if not interaction.user.guild_permissions.administrator:
                await interaction.response.send_message("Admins only.", ephemeral=True)
                return

            view = MonitorAddView(self.storage, str(interaction.guild.id))
            await interaction.response.send_message("Select channels to monitor:", view=view, ephemeral=True)

        @self.monitor_group.command(name="remove", description="Remove monitored channels")
        async def monitor_remove(interaction: discord.Interaction):
            if not interaction.guild:
                await interaction.response.send_message("Use this command in a server.", ephemeral=True)
                return

            if not interaction.user.guild_permissions.administrator:
                await interaction.response.send_message("Admins only.", ephemeral=True)
                return

            monitored = self.storage.discord_list_monitored_channels(str(interaction.guild.id))
            if not monitored:
                await interaction.response.send_message("No monitored channels configured.", ephemeral=True)
                return

            view = MonitorRemoveView(self.storage, str(interaction.guild.id))
            await interaction.response.send_message("Select channels to remove:", view=view, ephemeral=True)

        @self.monitor_group.command(name="list", description="List monitored channels")
        async def monitor_list(interaction: discord.Interaction):
            if not interaction.guild:
                await interaction.response.send_message("Use this command in a server.", ephemeral=True)
                return

            if not interaction.user.guild_permissions.administrator:
                await interaction.response.send_message("Admins only.", ephemeral=True)
                return

            monitored = self.storage.discord_list_monitored_channels(str(interaction.guild.id))
            if not monitored:
                await interaction.response.send_message("No monitored channels configured.", ephemeral=True)
                return

            mentions = "\n".join(f"- <#{cid}>" for cid in monitored)
            await interaction.response.send_message(f"📌 Monitored channels:\n{mentions}", ephemeral=True)

        # ---- /tz set/show/clear ----

        @self.tz_group.command(name="set", description="Set your timezone (IANA format)")
        @app_commands.describe(timezone="Example: Europe/Amsterdam, Asia/Yerevan")
        async def tz_set(interaction: discord.Interaction, timezone: str):
            self.storage.set_user_timezone("discord", str(interaction.user.id), timezone)
            await interaction.response.send_message(f"✅ Timezone set to `{timezone}`", ephemeral=True)

        @self.tz_group.command(name="show", description="Show your current timezone")
        async def tz_show(interaction: discord.Interaction):
            tz = self.storage.get_user_timezone("discord", str(interaction.user.id))
            if tz:
                await interaction.response.send_message(f"Your timezone: `{tz}`", ephemeral=True)
            else:
                await interaction.response.send_message(
                    "You don't have a timezone set. Use `/tz set Europe/Amsterdam`",
                    ephemeral=True,
                )

        @self.tz_group.command(name="clear", description="Clear your timezone")
        async def tz_clear(interaction: discord.Interaction):
            self.storage.clear_user_timezone("discord", str(interaction.user.id))
            await interaction.response.send_message("✅ Your timezone was cleared.", ephemeral=True)

        # ---- /feedback ----

        @self.tree.command(name="feedback", description="Send feedback about the bot")
        @app_commands.describe(text="Your feedback")
        async def feedback(interaction: discord.Interaction, text: str):
            scope_id = str(interaction.guild.id) if interaction.guild else None
            self.storage.save_feedback(platform="discord", user_id=str(interaction.user.id), text=text, scope_id=scope_id)
            await interaction.response.send_message("✅ Thanks! Feedback saved.", ephemeral=True)

        # ---- /delete_me ----

        @self.tree.command(name="delete_me", description="Delete your stored bot data")
        async def delete_me(interaction: discord.Interaction):
            self.storage.delete_user_data("discord", str(interaction.user.id))
            await interaction.response.send_message("✅ Your data has been deleted.", ephemeral=True)

    async def setup_hook(self) -> None:
        # Sync commands globally
        await self.tree.sync()
        logger.info("Discord commands synced.")

    async def on_ready(self) -> None:
        logger.info("Discord bot logged in as %s", self.user)

    # Message listener (new messages only)
    async def on_message(self, message: discord.Message) -> None:
        # Ignore own messages + other bots
        if message.author.bot:
            return

        # Only in guild text channels
        if not message.guild or not isinstance(message.channel, discord.TextChannel):
            return

        guild_id = str(message.guild.id)
        channel_id = str(message.channel.id)

        # Only process monitored channels
        if not self.storage.discord_is_monitored_channel(guild_id, channel_id):
            return

        # MVP: only newly sent messages (not edited) -> on_message covers that
        ctx = DiscordMessageContext(
            guild_id=guild_id,
            channel_id=channel_id,
            sender_id=str(message.author.id),
            sender_is_bot=message.author.bot,
            is_edited=False,
        )

        prompt = self.engine.discord_should_post_button_prompt(message.content or "", ctx)
        if prompt is None:
            return

        # Post public prompt + button as a reply to the original message
        try:
            await message.reply(
                prompt.text,
                view=ConvertForMeView(self.engine),
                mention_author=False,
            )
        except Exception as e:
            logger.exception("Failed to send Discord button prompt: %s", e)

    def run_bot(self) -> None:
        logging.basicConfig(level=logging.INFO)
        super().run(self.settings.token)
