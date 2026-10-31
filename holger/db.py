"""SQLite storage. Discord is the source of truth; everything here can be rebuilt with backfill."""

import sqlite3
import time
from collections.abc import Iterable
from pathlib import Path
from typing import TypedDict

ALL_TIME = (0, 2**62)


class UserStats(TypedDict):
    posted: int
    received: int
    given: int
    best: tuple[int, int] | None  # (message_id, reactions)


SCHEMA = """
CREATE TABLE IF NOT EXISTS messages (
    message_id INTEGER PRIMARY KEY,
    channel_id INTEGER NOT NULL,
    author_id  INTEGER NOT NULL,
    created_at INTEGER NOT NULL,
    deleted    INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS messages_created_at ON messages(created_at);

CREATE TABLE IF NOT EXISTS reactions (
    message_id INTEGER NOT NULL,
    user_id    INTEGER NOT NULL,
    emoji      TEXT NOT NULL,
    PRIMARY KEY (message_id, user_id, emoji)
);
CREATE INDEX IF NOT EXISTS reactions_user ON reactions(user_id);

CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    name    TEXT,
    is_bot  INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS reports (
    period_type  TEXT NOT NULL,
    period_start TEXT NOT NULL,
    posted_at    INTEGER NOT NULL,
    PRIMARY KEY (period_type, period_start)
);

-- Reactions that count: not on deleted memes, not by the meme's author, not by bots.
CREATE VIEW IF NOT EXISTS valid_reactions AS
SELECT r.message_id, r.user_id, r.emoji, m.author_id, m.created_at
FROM reactions r
JOIN messages m ON m.message_id = r.message_id
LEFT JOIN users u ON u.user_id = r.user_id
WHERE m.deleted = 0
  AND r.user_id != m.author_id
  AND COALESCE(u.is_bot, 0) = 0;
"""


class Database:
    def __init__(self, path: Path | str):
        self.conn = sqlite3.connect(path)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA busy_timeout=10000")
        self.conn.executescript(SCHEMA)

    def close(self) -> None:
        self.conn.close()

    # Writes

    def upsert_user(self, user_id: int, name: str, is_bot: bool) -> None:
        with self.conn:
            self.conn.execute(
                "INSERT INTO users (user_id, name, is_bot) VALUES (?, ?, ?)"
                " ON CONFLICT (user_id) DO UPDATE SET name = excluded.name, is_bot = excluded.is_bot",
                (user_id, name, int(is_bot)),
            )

    def upsert_message(self, message_id: int, channel_id: int, author_id: int, created_at: int) -> None:
        with self.conn:
            self.conn.execute(
                "INSERT INTO messages (message_id, channel_id, author_id, created_at) VALUES (?, ?, ?, ?)"
                " ON CONFLICT (message_id) DO UPDATE SET deleted = 0",
                (message_id, channel_id, author_id, created_at),
            )

    def mark_deleted(self, message_ids: Iterable[int]) -> None:
        with self.conn:
            self.conn.executemany(
                "UPDATE messages SET deleted = 1 WHERE message_id = ?",
                [(message_id,) for message_id in message_ids],
            )

    def add_reaction(self, message_id: int, user_id: int, emoji: str) -> None:
        # Only reactions on tracked memes are stored.
        with self.conn:
            self.conn.execute(
                "INSERT OR IGNORE INTO reactions (message_id, user_id, emoji)"
                " SELECT ?, ?, ? WHERE EXISTS (SELECT 1 FROM messages WHERE message_id = ?)",
                (message_id, user_id, emoji, message_id),
            )

    def remove_reaction(self, message_id: int, user_id: int, emoji: str) -> None:
        with self.conn:
            self.conn.execute(
                "DELETE FROM reactions WHERE message_id = ? AND user_id = ? AND emoji = ?",
                (message_id, user_id, emoji),
            )

    def clear_reactions(self, message_id: int, emoji: str | None = None) -> None:
        with self.conn:
            if emoji is None:
                self.conn.execute("DELETE FROM reactions WHERE message_id = ?", (message_id,))
            else:
                self.conn.execute("DELETE FROM reactions WHERE message_id = ? AND emoji = ?", (message_id, emoji))

    def set_reactions(self, message_id: int, emoji: str, user_ids: Iterable[int]) -> None:
        """Replace who reacted with `emoji` on a message."""
        with self.conn:
            self.conn.execute("DELETE FROM reactions WHERE message_id = ? AND emoji = ?", (message_id, emoji))
            self.conn.executemany(
                "INSERT INTO reactions (message_id, user_id, emoji) VALUES (?, ?, ?)",
                [(message_id, user_id, emoji) for user_id in set(user_ids)],
            )

    def mark_posted(self, period_type: str, period_start: str) -> None:
        with self.conn:
            self.conn.execute(
                "INSERT OR REPLACE INTO reports (period_type, period_start, posted_at) VALUES (?, ?, ?)",
                (period_type, period_start, int(time.time())),
            )

    # Reads

    def reaction_counts(self, message_id: int) -> dict[str, int]:
        rows = self.conn.execute(
            "SELECT emoji, COUNT(*) FROM reactions WHERE message_id = ? GROUP BY emoji", (message_id,)
        )
        return dict(rows.fetchall())

    def last_message_id(self) -> int | None:
        return self.conn.execute("SELECT MAX(message_id) FROM messages").fetchone()[0]

    def message_ids_between(self, start: int, end: int) -> set[int]:
        rows = self.conn.execute(
            "SELECT message_id FROM messages WHERE deleted = 0 AND created_at >= ? AND created_at < ?",
            (start, end),
        )
        return {row[0] for row in rows}

    def posted_keys(self) -> set[tuple[str, str]]:
        return set(self.conn.execute("SELECT period_type, period_start FROM reports").fetchall())

    def top_memes(self, start: int, end: int) -> list[tuple[int, int, int]]:
        """(message_id, author_id, reactions) for memes with at least one reaction, best first."""
        return self.conn.execute(
            "SELECT message_id, author_id, COUNT(*) AS score FROM valid_reactions"
            " WHERE created_at >= ? AND created_at < ?"
            " GROUP BY message_id ORDER BY score DESC, MIN(created_at)",
            (start, end),
        ).fetchall()

    def top_posters(self, start: int, end: int) -> list[tuple[int, int]]:
        """(user_id, memes posted), most first."""
        return self.conn.execute(
            "SELECT author_id, COUNT(*) AS posted FROM messages"
            " WHERE deleted = 0 AND created_at >= ? AND created_at < ?"
            " GROUP BY author_id ORDER BY posted DESC, MIN(created_at)",
            (start, end),
        ).fetchall()

    def top_reactors(self, start: int, end: int) -> list[tuple[int, int]]:
        """(user_id, reactions given to other people's memes), most first."""
        return self.conn.execute(
            "SELECT user_id, COUNT(*) AS given FROM valid_reactions"
            " WHERE created_at >= ? AND created_at < ?"
            " GROUP BY user_id ORDER BY given DESC",
            (start, end),
        ).fetchall()

    def user_stats(self, user_id: int) -> UserStats:
        posted = self.conn.execute(
            "SELECT COUNT(*) FROM messages WHERE deleted = 0 AND author_id = ?", (user_id,)
        ).fetchone()[0]
        received = self.conn.execute("SELECT COUNT(*) FROM valid_reactions WHERE author_id = ?", (user_id,)).fetchone()[
            0
        ]
        given = self.conn.execute("SELECT COUNT(*) FROM valid_reactions WHERE user_id = ?", (user_id,)).fetchone()[0]
        best = self.conn.execute(
            "SELECT message_id, COUNT(*) AS score FROM valid_reactions WHERE author_id = ?"
            " GROUP BY message_id ORDER BY score DESC, MIN(created_at) LIMIT 1",
            (user_id,),
        ).fetchone()
        return {"posted": posted, "received": received, "given": given, "best": best}
