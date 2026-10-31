"""Import channel history into the database.

    python -m holger.backfill --all      # everything since the channel was created
    python -m holger.backfill --days 30

Safe to re-run at any time; it rebuilds the database from Discord.
"""

import argparse
import asyncio
from datetime import UTC, datetime, timedelta

import discord

from holger.config import Config, load_config, setup_logging
from holger.db import Database
from holger.sync import get_text_channel, sync_range


async def run(args: argparse.Namespace, config: Config) -> None:
    db = Database(config.db_path)
    async with discord.Client(intents=discord.Intents.default()) as client:
        await client.login(config.token)
        channel = await get_text_channel(client, config.channel_id)
        # The channel's own id is its creation time, so --all starts there.
        since = discord.utils.snowflake_time(channel.id) if args.all else datetime.now(UTC) - timedelta(days=args.days)
        await sync_range(db, channel, since)


def main() -> None:
    parser = argparse.ArgumentParser(description="Import meme channel history")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--all", action="store_true", help="import the whole channel history")
    group.add_argument("--days", type=int, help="import the last N days")
    args = parser.parse_args()

    config = load_config()
    setup_logging(config.log_level)
    asyncio.run(run(args, config))


if __name__ == "__main__":
    main()
