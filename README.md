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
   **Message Content** intent for the bot and turn off **Public Bot**.
2. Invite the bot with the `bot` and `applications.commands` scopes and permissions `84992`
   (View Channel, Read Message History, Send Messages, Embed Links):
   `https://discord.com/oauth2/authorize?client_id=APP_ID&scope=bot+applications.commands&permissions=84992`.
   It only needs them in the meme channel, so you can grant them as a channel override instead of
   server-wide.
3. Copy `.env.example` to `.env` and fill in `DISCORD_TOKEN` and `CHANNEL_ID`.
4. `docker compose up -d --build`. Locally, `compose.override.yaml` builds the image from source.
5. Import the existing history once:
   `docker compose exec collector python -m holger.backfill --all`

### Unraid

Run it as a **Compose Manager** stack (Community Apps) whose files live on the cache pool, so the token stays
off the flash drive and Appdata Backup covers it:

```
/mnt/nvme_cache/appdata/holger/
├── compose.yaml   ← copied unchanged from this repo
├── .env           ← from .env.example, without APPDATA_DIR
└── data/          ← holger.db
```

1. `mkdir -p /mnt/nvme_cache/appdata/holger/data` and put `compose.yaml` and `.env` in
   `/mnt/nvme_cache/appdata/holger`. Use the pool path, not `/mnt/user/...` or an SMB share: SQLite locking is
   unreliable there.
2. Docker tab → Compose → **Add New Stack**, then set:
   - Compose Source: **External folder** → `/mnt/nvme_cache/appdata/holger`
   - External ENV File Path: empty (`env_file: .env` resolves next to `compose.yaml`)
   - Compose File Discovery: Explicit -f flags
   - Override File Management: Automatic
3. **Compose Up**, then run the backfill from step 5 above.

Only `compose.yaml` is used on Unraid, so the stack pulls the published image instead of building.
New releases need **Update Stack** only. Copy `compose.yaml` again only when it changes in the repo, and add any
new variable from `.env.example` to `.env` yourself. To change a secret, edit `.env` and **Compose Up**.

- Images are published to `ghcr.io/antonericson/holger` on every push to `main` (`latest`, `sha-…`)
  and on `v*` tags.

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
