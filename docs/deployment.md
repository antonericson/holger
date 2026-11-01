# Deployment and operations

## Discord application

A bot token has no scopes of its own. Access comes from the intents, the invite scopes and the
channel permissions. Collector and reporter share one token.

1. **Application** ([developer portal](https://discord.com/developers/applications)): open the
   existing application or create one. Copy the **Application ID**, which is the `client_id` in the
   invite link. Leave **Interactions Endpoint URL** empty, because slash commands arrive over the
   gateway.
2. **Installation:** Installation Contexts **Guild Install** only, Install Link **None**. Set the
   install link before turning Public Bot off, since Discord rejects a private bot with a default
   install link.
3. **Bot:**
   - **Reset Token** and copy it straight into `.env` as `DISCORD_TOKEN`. It is shown only once,
     and resetting it immediately disconnects anything using the old token.
   - **Public Bot** off, **Requires OAuth2 Code Grant** off.
   - Privileged Gateway Intents: **Message Content** on (otherwise attachments and embeds come back
     empty). Server Members and Presence off.
4. **Invite** with the `bot` and `applications.commands` scopes and permissions `84992` (View
   Channel, Read Message History, Send Messages, Embed Links):

   ```
   https://discord.com/oauth2/authorize?client_id=APP_ID&scope=bot+applications.commands&permissions=84992
   ```

   Authorize again if the bot is already in the server but was invited without
   `applications.commands`.
5. **In the server:** enable Developer Mode (User Settings → Advanced), right-click the meme channel
   → **Copy Channel ID** → `.env` `CHANNEL_ID`. Optionally give the bot role nothing server-wide and
   grant the four permissions as an override on the meme channel only.

Not needed: Administrator, Manage Messages, Add Reactions, Attach Files, Mention Everyone. Slash
commands need no portal setup; the collector registers them in the server on every start.

## Unraid

Run it as a **Compose Manager** stack (Community Apps) whose files live on the cache pool, so the
token stays off the flash drive and Appdata Backup covers it:

```
/mnt/nvme_cache/appdata/holger/
├── compose.yaml   ← copied unchanged from this repo
├── .env           ← from .env.example, without APPDATA_DIR
└── data/          ← holger.db
```

1. `mkdir -p /mnt/nvme_cache/appdata/holger/data` and put `compose.yaml` and `.env` in
   `/mnt/nvme_cache/appdata/holger`.
   - Use the pool path, not `/mnt/user/...` or an SMB share, where SQLite locking is unreliable.
     `/mnt/user/appdata` only works if the share has exclusive access.
   - Create the folder first. Otherwise Docker creates it in RAM-backed `/mnt` and the database is
     lost on reboot.
2. Docker tab → Compose → **Add New Stack**, then set:

   | Setting | Value | Why |
   |---|---|---|
   | Compose Source | **External folder** → `/mnt/nvme_cache/appdata/holger` | Files and token stay on the pool, not the FAT32 flash drive |
   | External ENV File Path | empty | `env_file: .env` resolves next to `compose.yaml` |
   | Compose File Discovery | Explicit -f flags | Only `compose.yaml` is used |
   | Override File Management | Automatic | The plugin only manages Unraid labels |

   The default Project folder source stores the token on the flash drive. A Git repository source
   would look for `.env` inside the plugin's clone.
3. Enable autostart for the stack and **Compose Up**.
4. Import the existing history once (see below).
5. Add the stack to **Appdata Backup**, scheduled away from 09:00 so it doesn't stop the reporter
   mid-run.

Only `compose.yaml` is used on Unraid, so the stack pulls the published image instead of building.
The GHCR package is public, so no registry login is needed.

### Secrets

Secrets are plain environment variables from the stack's `.env`.

- **Change a secret:** edit `.env`, **Compose Up**. Both containers are recreated.
- **Leaked token:** reset it in the developer portal, put the new one in `.env`, **Compose Up**.
- **Who can read it:** anyone with Docker access (`docker inspect`), which on Unraid means root.
  Appdata Backup copies include `.env`, so keep the backup destination private.

## Running commands

Run one-off commands inside the running containers. From the Unraid terminal:

```sh
docker exec holger-collector-1 python -m holger.backfill --all
```

Or open the container's **Console** from the Docker tab and run `python -m holger.backfill --all`.
Compose Manager names containers `<stack>-<service>-1`. Closing the terminal stops the command. For
a long run, start it detached with a log file:

```sh
docker exec -d holger-collector-1 sh -c 'python -m holger.backfill --all > /data/backfill.log 2>&1'
tail -f /mnt/nvme_cache/appdata/holger/data/backfill.log
```

### First run

1. `python -m holger.backfill --all` imports the whole channel history, needed for all-time stats
   and the first yearly leaderboard. Every write is committed immediately, so after an interruption
   resume with `--days N`, covering back to the last date in the log.
2. **Switching over from another bot:** if the previous week's leaderboard has already been posted,
   record it without posting:

   ```sh
   docker exec holger-reporter-1 python -m holger.report --catch-up --mark-only
   ```

## Updating

1. Branch and change the code. Run `ruff check . && ruff format --check . && pyright && pytest`.
2. For changes to Discord behaviour, test with a separate development application and test server
   (own token in the local `.env`). `python -m holger.report week --dry-run` prints a report without
   posting.
3. Open a PR. CI runs the checks and builds the image without pushing.
4. Merge to `main`. CI pushes `ghcr.io/antonericson/holger:latest` and `:sha-<commit>`.
5. Unraid → Compose → **Update Stack** (pull and recreate changed containers).
6. Check that the collector log shows "Logged in as …" and the container turns healthy within two
   minutes.

Copy `compose.yaml` to Unraid again only when it changes in the repo, and add any new variable from
`.env.example` to `.env` yourself.

Watch out for:
- **Don't update around 09:00.** Recreating the reporter mid-run can leave a half-posted
  leaderboard. Restarting the collector is always safe.
- **Schema changes don't apply to an existing database.** Stop the stack, delete `holger.db`, start
  it, run `backfill --all`.
- **Rollback:** change `:latest` to a previous `:sha-<commit>` in the stack's `compose.yaml`,
  **Update Stack**. Switch back to `:latest` once fixed.
- **Never run the collector locally with the production token.** Two connections for the same bot
  both answer slash commands.
