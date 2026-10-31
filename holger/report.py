"""One-shot leaderboard poster, run by supercronic in the reporter container.

    python -m holger.report --catch-up          # post every due leaderboard (run daily)
    python -m holger.report week [--force]      # post last week's leaderboard now
    python -m holger.report --catch-up --dry-run
    python -m holger.report --catch-up --mark-only   # record due reports as posted without posting

Each period is reconciled from Discord before it is ranked, so reports are correct even if
the collector was down. Posted periods are recorded so nothing is posted twice.
"""

import argparse
import asyncio
import logging
from datetime import datetime

import discord

from holger.config import Config, load_config, setup_logging
from holger.db import Database
from holger.healthcheck import ping
from holger.leaderboard import Post, build_report
from holger.periods import KINDS, Period, due_periods, previous_period
from holger.sync import get_text_channel, sync_range

log = logging.getLogger(__name__)


def select_periods(args: argparse.Namespace, db: Database, now: datetime) -> list[Period]:
    if args.kind is None:
        return due_periods(now, db.posted_keys())
    period = previous_period(args.kind, now)
    if period.key in db.posted_keys() and not args.force:
        log.info("%s %s already posted, use --force to post again", *period.key)
        return []
    return [period]


async def send(channel: discord.TextChannel, posts: list[Post]) -> None:
    for post in posts:
        if not post.meme_id:
            await channel.send(post.content)
            continue
        # Attachment URLs expire, so always fetch a fresh one.
        try:
            meme = await channel.fetch_message(post.meme_id)
        except discord.NotFound:
            log.warning("Meme %d no longer exists", post.meme_id)
            await channel.send(post.content)
            continue
        link = meme.attachments[0].url if meme.attachments else meme.jump_url
        await channel.send(f"{post.content}\n{link}", reference=meme)


async def run(args: argparse.Namespace, config: Config) -> None:
    db = Database(config.db_path)
    periods = select_periods(args, db, datetime.now(config.tz))
    if not periods:
        log.info("Nothing to post")
        return

    if args.mark_only:
        for period in periods:
            db.mark_posted(*period.key)
            log.info("Marked %s %s as posted", *period.key)
        return

    # Only the REST API is needed, so no gateway connection (and no on_ready) is involved.
    async with discord.Client(intents=discord.Intents.default()) as client:
        await client.login(config.token)
        channel = await get_text_channel(client, config.channel_id)
        for period in periods:
            await sync_range(db, channel, period.start, period.end)
            start, end = int(period.start.timestamp()), int(period.end.timestamp())
            posts = build_report(
                period, db.top_memes(start, end), db.top_posters(start, end), db.top_reactors(start, end)
            )
            if args.dry_run:
                print("\n\n".join(p.content + (f"\n[meme {p.meme_id}]" if p.meme_id else "") for p in posts))
                continue
            await send(channel, posts)
            db.mark_posted(*period.key)
            log.info("Posted %s %s", *period.key)


def main() -> None:
    parser = argparse.ArgumentParser(description="Post meme leaderboards")
    parser.add_argument("kind", nargs="?", choices=KINDS, help="post the previous complete period of this kind")
    parser.add_argument("--catch-up", action="store_true", help="post every due period (default without kind)")
    parser.add_argument("--force", action="store_true", help="post even if already posted")
    parser.add_argument("--dry-run", action="store_true", help="print instead of posting")
    parser.add_argument("--mark-only", action="store_true", help="record due periods as posted without posting")
    args = parser.parse_args()
    if args.kind and args.catch_up:
        parser.error("use either a kind or --catch-up")

    config = load_config()
    setup_logging(config.log_level)
    try:
        asyncio.run(run(args, config))
    except Exception:
        log.exception("Report failed")
        if not args.dry_run:
            ping(config.healthcheck_url, fail=True)
        raise SystemExit(1) from None
    if not args.dry_run:
        ping(config.healthcheck_url)


if __name__ == "__main__":
    main()
