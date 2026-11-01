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
`python -m holger.backfill --all`. Leaderboards are posted at 09:00: weekly on Mondays, monthly on
the 1st and yearly on 1 January, and a missed one is posted on the next run.

- [Architecture](docs/architecture.md): design, periods and catch-up, data model, design decisions
- [Deployment and operations](docs/deployment.md): Discord application, Unraid stack, secrets,
  first run, updating

## Quick start

1. Create a Discord application with the **Message Content** intent and invite the bot to the meme
   channel ([details](docs/deployment.md#discord-application)).
2. Copy `.env.example` to `.env` and fill in `DISCORD_TOKEN` and `CHANNEL_ID`.
3. `docker compose up -d --build`. Locally, `compose.override.yaml` builds the image from source.
4. Import the existing history once:
   `docker compose exec collector python -m holger.backfill --all`

On Unraid, see [Deployment and operations](docs/deployment.md#unraid).

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

CI runs the same checks before building the image. `ruff format .` fixes formatting. For the release
flow, see [Updating](docs/deployment.md#updating).

Without Docker, the database goes to `./data` (set `DATA_DIR` to change it).
