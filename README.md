# 🐷Holger - Discord Meme Leaderboard Bot🐷

A Discord bot that posts weekly, monthly, and yearly leaderboards in your server's meme channel. 🥇

Leaderboards include:

- Top memes 🐸 (memes with the most reactions, not counting the poster's own)
- Top meme posters ✉️ (# of images, videos, gifs and links posted)
- Top meme enjoyers 🤣 (# of reactions made to memes posted by other people)

Slash commands: `/stats [user]` and `/leaderboard [week|month|year|all]`.

## How it works

One Docker image runs as two containers:

| Container   | Command                       | Job |
|-------------|-------------------------------|-----|
| `collector` | `python -m holger.collector`  | Always on. Records memes and reactions into SQLite as they happen, catches up on startup, serves slash commands. |
| `reporter`  | `supercronic /app/crontab`    | Runs `python -m holger.report --catch-up` daily. Posts any leaderboard that is due. |

Discord is the source of truth. The database (`/data/holger.db`) can be rebuilt at any time with
`python -m holger.backfill --all`. Before ranking a period the reporter re-syncs it from Discord, so
leaderboards are correct even if the collector was down.

Periods are calendar based (Mon–Sun weeks, calendar months/years) in the `TZ` timezone. Posted
periods are recorded, so a report is never posted twice, and a missed report is posted on the next
run as long as it is within its grace window (3 days for weeks, 7 for months, 14 for years).

## Setup

1. In the [Discord developer portal](https://discord.com/developers/applications), enable the
   **Message Content** intent for the bot.
2. Copy `.env.example` to `.env` and fill in `DISCORD_TOKEN` and `CHANNEL_ID`.
3. `docker compose up -d`
4. Import the existing history once:
   `docker compose exec collector python -m holger.backfill --all`

### Unraid

- Install **Compose Manager** from Community Apps and create a stack with `compose.yaml` and `.env`.
- Point `APPDATA_DIR` at the pool path, e.g. `/mnt/nvme_cache/appdata/holger`, not `/mnt/user/...` or an SMB
  share (SQLite locking is unreliable there). Create the folder first: if it does not exist, Docker creates it
  in RAM-backed `/mnt` and the database is lost on reboot.
- Images are published to `ghcr.io/antonericson/holger` on every push to `main` (`latest`, `sha-…`)
  and on `v*` tags.
- Set `HEALTHCHECK_URL` to a [healthchecks.io](https://healthchecks.io) check with a 1 day period.
  The reporter pings it after every run, so you are alerted if reports stop.

### Switching over from another bot

If the previous week's leaderboard has already been posted elsewhere, record it without posting:
`docker compose exec reporter python -m holger.report --catch-up --mark-only`

## Commands

```sh
python -m holger.report --catch-up             # post every due leaderboard
python -m holger.report week --dry-run         # print last week's leaderboard
python -m holger.report month --force          # post last month's leaderboard again
python -m holger.backfill --days 30            # re-sync the last 30 days
```

## Development

```sh
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
ruff check . && ruff format --check . && pyright && pytest
```

CI runs the same checks before building the image. `ruff format .` fixes formatting.

Without Docker, the database goes to `./data` (set `DATA_DIR` to change it).
