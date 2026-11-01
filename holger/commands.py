"""Slash commands. Replies never ping anyone."""

from datetime import datetime

import discord
from discord import app_commands

from holger.config import Config
from holger.db import ALL_TIME, Database
from holger.leaderboard import MEDALS, plural, rank
from holger.periods import current_period

NO_PINGS = discord.AllowedMentions.none()


def jump_url(guild_id: int | None, channel_id: int, message_id: int) -> str:
    return f"https://discord.com/channels/{guild_id or '@me'}/{channel_id}/{message_id}"


def top_emoji(client: discord.Client, ranked: list[tuple[str, int]]) -> tuple[str, int] | None:
    """The most used emoji that can still be shown: unicode, or a custom emoji still on the server.

    Custom emoji are stored by id, and one that has been deleted can't be rendered.
    """
    for key, n in ranked:
        if not key.isdigit():
            return key, n
        if emoji := client.get_emoji(int(key)):
            return str(emoji), n
    return None


def register_commands(tree: app_commands.CommandTree[discord.Client], db: Database, config: Config) -> None:
    @tree.command(description="Show meme statistics for you or someone else")
    @app_commands.describe(user="Whose stats to show (default: you)")
    async def stats(interaction: discord.Interaction, user: discord.User | discord.Member | None = None) -> None:
        target = user or interaction.user
        s = db.user_stats(target.id)
        lines = [
            f"**Meme stats for {target.mention}** (all time)",
            f"Memes posted: {s['posted']}",
            f"Reactions received: {s['received']}",
            f"Reactions given: {s['given']}",
        ]
        if used := top_emoji(interaction.client, s["used_emoji"]):
            lines.append(f"Certified {used[0]} enjoyer ({plural(used[1], 'time')})")
        if received := top_emoji(interaction.client, s["received_emoji"]):
            lines.append(f"Their memes mostly get {received[0]} ({plural(received[1], 'time')})")
        if s["best"]:
            message_id, score = s["best"]
            url = jump_url(interaction.guild_id, config.channel_id, message_id)
            lines.append(f"Best meme: {url} ({plural(score, 'reaction')})")
        await interaction.response.send_message("\n".join(lines), allowed_mentions=NO_PINGS)

    @tree.command(description="Show the meme leaderboard so far")
    @app_commands.describe(period="Which period (default: this week)")
    @app_commands.choices(
        period=[
            app_commands.Choice(name="This week", value="week"),
            app_commands.Choice(name="This month", value="month"),
            app_commands.Choice(name="This year", value="year"),
            app_commands.Choice(name="All time", value="all"),
        ]
    )
    async def leaderboard(interaction: discord.Interaction, period: str = "week") -> None:
        if period == "all":
            title, (start, end) = "all time", ALL_TIME
        else:
            p = current_period(period, datetime.now(config.tz))
            title, start, end = f"this {period}", int(p.start.timestamp()), int(p.end.timestamp())

        memes = db.top_memes(start, end)
        posters = db.top_posters(start, end)
        reactors = db.top_reactors(start, end)

        lines = [f":trophy: **Leaderboard for {title}**"]
        authors = {message_id: author_id for message_id, author_id, _ in memes}
        for place, message_id, score in rank([(m, s) for m, _, s in memes]):
            url = jump_url(interaction.guild_id, config.channel_id, message_id)
            lines.append(f"{MEDALS[place]} <@{authors[message_id]}> {plural(score, 'reaction')} {url}")
        lines.append("**Posters**")
        lines += [f"{MEDALS[p]} <@{u}> {plural(n, 'meme')}" for p, u, n in rank(posters)]
        lines.append("**Enjoyers**")
        lines += [f"{MEDALS[p]} <@{u}> {plural(n, 'reaction')}" for p, u, n in rank(reactors)]
        if not memes and not posters:
            lines = [f"No memes for {title} yet :cry:"]

        await interaction.response.send_message("\n".join(lines), allowed_mentions=NO_PINGS, suppress_embeds=True)
