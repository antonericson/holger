# Architecture

## Guiding principle

Discord is the source of truth. The SQLite database is a rebuildable index of the meme channel
(`python -m holger.backfill --all`), so losing it costs nothing. Posting leaderboards is a one-shot
process run on a schedule, independent of the always-on part.

## Components

One Docker image runs as two containers in one compose stack. Both mount the same `/data` folder.

```
┌──────────────── compose stack ─────────────────┐
│  collector   python -m holger.collector        │  always on, gateway events
│  reporter    supercronic /app/crontab          │  daily one-shot report run
│     └── both mount /data                       │  → holger.db (SQLite, WAL)
└────────────────────────────────────────────────┘
```

**Collector** (always on)
- Records memes, reactions, edits and deletes into SQLite, keyed on Discord IDs.
- On every start or full reconnect, syncs from the last seen message (or the last `RESCAN_DAYS`,
  whichever is earlier), so downtime loses nothing.
- Serves `/stats [user]` (posts, reactions, best meme, most used and received emoji) and
  `/leaderboard [week|month|year|all]`. Responses never ping anyone.
- Touches a heartbeat file every minute for the Docker healthcheck.

**Reporter** (one-shot, run by supercronic)
- Uses only the REST API. It never waits for a gateway `on_ready`, so it can't hang.
- Re-syncs the period from Discord before ranking, so reports are correct even if the collector was
  down all week.
- Runs `--catch-up` daily: posts every period not yet recorded in `reports`, within its grace window.
- Exits non-zero on failure, and each run is limited to 15 minutes by `timeout` in the `crontab`.

## Periods and catch-up

Periods are calendar based in the `TZ` timezone: Monday–Sunday weeks, calendar months and calendar
years. The reporter runs daily at 09:00:

| Leaderboard | Posted | Covers | Grace window |
|---|---|---|---|
| Weekly | Every Monday | Previous Monday 00:00 – Sunday 23:59 | 3 days |
| Monthly | The 1st | The previous calendar month | 7 days |
| Yearly | 1 January | The previous year | 14 days |

- Leaderboards due on the same day are posted in the order week → month → year.
- A leaderboard missed because the server was down is posted by the next run inside its grace window.
  Older ones are skipped.
- Posted periods are recorded in `reports`, so retries or double runs never post twice.
- The time is set in `crontab` and the days in `holger/periods.py`. Without `TZ` everything is in UTC.

## Syncing

`holger/sync.py` is the only code that reconciles the database with Discord.

- A message is a meme if a non-bot user posted it with an attachment or embed.
- Reactions are fetched user by user only when Discord's count differs from the stored count, which
  keeps full-year re-syncs cheap.
- Memes stored for a synced range but no longer in Discord are marked deleted.
- Reactions with a custom emoji that has been deleted from the server are skipped, because Discord
  no longer lists who used them.

## Data model

```
messages(message_id PK, channel_id, author_id, created_at, deleted)    -- memes only
reactions(message_id, user_id, emoji, PK(message_id, user_id, emoji))  -- emoji = character or custom emoji id
users(user_id PK, name, is_bot)
reports(period_type, period_start, posted_at, PK(period_type, period_start))
valid_reactions  -- view: excludes deleted memes, self-reactions and bot reactions
```

- **Raw facts only.** Stats are derived with queries. Stored counters drift when an event is missed
  or a reaction is removed.
- **No images or attachment URLs.** Discord keeps the files, and attachment URLs are signed and
  expire. Reports fetch the message to get a fresh URL.
- **No migrations.** The schema is created with `CREATE ... IF NOT EXISTS` and never altered. When
  the schema changes, delete `holger.db` and run `backfill --all`.
- WAL mode and a busy timeout let the collector, reporter and manual commands share the file.

## Code layout

| Module | Job |
|---|---|
| `holger/collector.py` | Always-on bot, gateway events, heartbeat |
| `holger/report.py` | One-shot reporter CLI |
| `holger/backfill.py` | History import CLI (`--all` / `--days N`) |
| `holger/sync.py` | Discord → database reconciliation |
| `holger/db.py` | SQLite schema, writes and leaderboard queries |
| `holger/periods.py` | Calendar periods and grace windows (pure) |
| `holger/leaderboard.py` | Ranking with ties and message formatting (pure) |
| `holger/commands.py` | Slash commands |
| `holger/healthcheck.py` | Docker healthcheck (heartbeat file age) |
| `holger/config.py` | Configuration from the environment |

## Reliability

- `restart: unless-stopped` on both containers.
- Dependencies pinned and baked into the image.
- Collector healthcheck on the heartbeat file.
- Reporter failures show as non-zero exits in its container log.
- Edge cases covered by tests: fewer than three memes, ties, no reactions.
- The database lives on a local disk path, not a FUSE or network share, where SQLite locking is
  unreliable.

## Design decisions

- **SQLite** over MongoDB or Postgres: no extra server, one file to back up, and the queries (count
  per user, top N, date range) are what SQL is good at. The data is small (around 10k messages and
  50k reactions a year).
- **Scheduler inside the reporter container (supercronic)** over:
  - an in-process scheduler in the always-on bot, which would only post if the bot were up at that
    moment;
  - cron on the host, which keeps the schedule outside the repo;
  - Ofelia, which needs the Docker socket.
- **No external monitoring** (e.g. healthchecks.io). Monitoring is the collector healthcheck and the
  reporter's container log.
- **No auto-updates** (e.g. Watchtower). Releases are deployed by hand so an untested image can't go
  live unattended, possibly during a report run.
