"""Reconcile the database with Discord's message history."""

import logging
from datetime import UTC, datetime

import discord

from holger.db import Database

log = logging.getLogger(__name__)

UNKNOWN_EMOJI = 10014


async def get_text_channel(client: discord.Client, channel_id: int) -> discord.TextChannel:
    channel = client.get_channel(channel_id) or await client.fetch_channel(channel_id)
    if not isinstance(channel, discord.TextChannel):
        raise RuntimeError(f"Channel {channel_id} is not a text channel")
    return channel


def emoji_key(emoji: discord.PartialEmoji | discord.Emoji | str) -> str:
    """Stable key: the character for unicode emoji, the id for custom emoji (names can change)."""
    if isinstance(emoji, str):
        return emoji
    return str(emoji.id) if emoji.id else emoji.name


def is_meme(message: discord.Message) -> bool:
    return not message.author.bot and bool(message.attachments or message.embeds)


async def sync_message(db: Database, message: discord.Message) -> bool:
    """Store a meme and its reactions. Returns False if the message is not a meme."""
    if not is_meme(message):
        return False

    db.upsert_user(message.author.id, message.author.name, message.author.bot)
    db.upsert_message(message.id, message.channel.id, message.author.id, int(message.created_at.timestamp()))

    stored = db.reaction_counts(message.id)
    seen: set[str] = set()
    for reaction in message.reactions:
        key = emoji_key(reaction.emoji)
        seen.add(key)
        # Only ask Discord who reacted when the count differs from what we have.
        if stored.get(key) == reaction.count:
            continue
        try:
            users = [user async for user in reaction.users()]
            if reaction.burst_count:
                users += [user async for user in reaction.users(type=discord.ReactionType.burst)]
        except discord.HTTPException as e:
            if e.code != UNKNOWN_EMOJI:
                raise
            # Custom emoji deleted from the server: Discord still shows the count but won't list who reacted.
            log.warning("Skipping deleted emoji %s on message %d", reaction.emoji, message.id)
            continue
        for user in users:
            db.upsert_user(user.id, user.name, user.bot)
        db.set_reactions(message.id, key, (user.id for user in users))

    for key in stored.keys() - seen:
        db.clear_reactions(message.id, key)
    return True


async def sync_range(
    db: Database,
    channel: discord.TextChannel,
    after: datetime,
    before: datetime | None = None,
) -> int:
    """Sync every meme posted in [after, before) and mark memes missing from Discord as deleted."""
    end = before or datetime.now(UTC)
    log.info("Syncing %s to %s", after.isoformat(), end.isoformat())

    seen: set[int] = set()
    scanned = 0
    async for message in channel.history(after=after, before=end, limit=None, oldest_first=True):
        scanned += 1
        if await sync_message(db, message):
            seen.add(message.id)
        if scanned % 500 == 0:
            log.info("Scanned %d messages (up to %s)", scanned, message.created_at.date())

    missing = db.message_ids_between(int(after.timestamp()), int(end.timestamp())) - seen
    if missing:
        log.info("Marking %d memes as deleted", len(missing))
        db.mark_deleted(missing)

    log.info("Synced %d memes from %d messages", len(seen), scanned)
    return len(seen)
