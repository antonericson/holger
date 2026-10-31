"""Always-on bot: records memes and reactions as they happen and serves slash commands.

Reports do not depend on this process; see holger.report.
"""

import asyncio
import logging
from datetime import UTC, datetime, timedelta

import discord
from discord import app_commands
from discord.ext import tasks

from holger.commands import register_commands
from holger.config import Config, load_config, setup_logging
from holger.db import Database
from holger.sync import emoji_key, get_text_channel, sync_message, sync_range

log = logging.getLogger(__name__)


class Collector(discord.Client):
    def __init__(self, config: Config, db: Database):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(intents=intents)
        self.config = config
        self.db = db
        self.tree = app_commands.CommandTree(self)
        self.channel: discord.TextChannel | None = None
        self.catch_up_lock = asyncio.Lock()

    async def setup_hook(self) -> None:
        register_commands(self.tree, self.db, self.config)
        self.heartbeat.start()

    async def on_ready(self) -> None:
        log.info("Logged in as %s", self.user)
        if self.channel is None:
            self.channel = await get_text_channel(self, self.config.channel_id)
            # Guild commands update instantly, unlike global ones.
            self.tree.copy_global_to(guild=self.channel.guild)
            await self.tree.sync(guild=self.channel.guild)
        # on_ready also fires after a full reconnect, so this covers any downtime.
        await self.catch_up(self.channel)

    async def catch_up(self, channel: discord.TextChannel) -> None:
        if self.catch_up_lock.locked():
            return
        async with self.catch_up_lock:
            after = datetime.now(UTC) - timedelta(days=self.config.rescan_days)
            last_id = self.db.last_message_id()
            if last_id:
                after = min(after, discord.utils.snowflake_time(last_id))
            await sync_range(self.db, channel, after)

    @tasks.loop(minutes=1)
    async def heartbeat(self) -> None:
        if self.is_ready() and not self.is_closed():
            self.config.heartbeat_path.touch()

    def in_channel(self, channel_id: int) -> bool:
        return channel_id == self.config.channel_id

    async def on_message(self, message: discord.Message) -> None:
        if self.in_channel(message.channel.id):
            await sync_message(self.db, message)

    async def on_raw_message_edit(self, payload: discord.RawMessageUpdateEvent) -> None:
        # Link embeds usually arrive as an edit shortly after the message is posted.
        if self.channel is None or not self.in_channel(payload.channel_id):
            return
        try:
            message = await self.channel.fetch_message(payload.message_id)
        except discord.NotFound:
            return
        await sync_message(self.db, message)

    async def on_raw_message_delete(self, payload: discord.RawMessageDeleteEvent) -> None:
        if self.in_channel(payload.channel_id):
            self.db.mark_deleted([payload.message_id])

    async def on_raw_bulk_message_delete(self, payload: discord.RawBulkMessageDeleteEvent) -> None:
        if self.in_channel(payload.channel_id):
            self.db.mark_deleted(payload.message_ids)

    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent) -> None:
        if not self.in_channel(payload.channel_id):
            return
        if payload.member:
            self.db.upsert_user(payload.member.id, payload.member.name, payload.member.bot)
        self.db.add_reaction(payload.message_id, payload.user_id, emoji_key(payload.emoji))

    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent) -> None:
        if self.in_channel(payload.channel_id):
            self.db.remove_reaction(payload.message_id, payload.user_id, emoji_key(payload.emoji))

    async def on_raw_reaction_clear(self, payload: discord.RawReactionClearEvent) -> None:
        if self.in_channel(payload.channel_id):
            self.db.clear_reactions(payload.message_id)

    async def on_raw_reaction_clear_emoji(self, payload: discord.RawReactionClearEmojiEvent) -> None:
        if self.in_channel(payload.channel_id):
            self.db.clear_reactions(payload.message_id, emoji_key(payload.emoji))


def main() -> None:
    config = load_config()
    setup_logging(config.log_level)
    Collector(config, Database(config.db_path)).run(config.token, log_handler=None)


if __name__ == "__main__":
    main()
