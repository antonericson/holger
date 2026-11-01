from pathlib import Path

import pytest

from holger.db import ALL_TIME, Database

ALICE, BOB, CAROL, BOT = 1, 2, 3, 99


@pytest.fixture
def db(tmp_path: Path) -> Database:
    db = Database(tmp_path / "test.db")
    db.upsert_user(BOT, "holger", is_bot=True)
    db.upsert_message(100, 1, ALICE, created_at=10)
    db.upsert_message(101, 1, BOB, created_at=20)
    db.upsert_message(102, 1, ALICE, created_at=30)
    return db


def test_top_memes_excludes_self_and_bot_reactions(db: Database) -> None:
    db.set_reactions(100, "😂", [ALICE, BOB, CAROL, BOT])
    db.add_reaction(100, BOB, "🔥")
    db.add_reaction(101, ALICE, "😂")
    assert db.top_memes(*ALL_TIME) == [(100, ALICE, 3), (101, BOB, 1)]


def test_memes_without_reactions_are_not_ranked(db: Database) -> None:
    assert db.top_memes(*ALL_TIME) == []
    assert db.top_posters(*ALL_TIME) == [(ALICE, 2), (BOB, 1)]


def test_period_bounds_are_half_open(db: Database) -> None:
    assert db.top_posters(10, 30) == [(ALICE, 1), (BOB, 1)]


def test_deleted_memes_do_not_count(db: Database) -> None:
    db.add_reaction(100, BOB, "😂")
    db.mark_deleted([100])
    assert db.top_memes(*ALL_TIME) == []
    assert db.top_posters(*ALL_TIME) == [(BOB, 1), (ALICE, 1)]  # tie: earliest post first
    db.upsert_message(100, 1, ALICE, created_at=10)  # seen again in history
    assert db.top_memes(*ALL_TIME) == [(100, ALICE, 1)]


def test_reactions_on_untracked_messages_are_ignored(db: Database) -> None:
    db.add_reaction(555, BOB, "😂")
    assert db.reaction_counts(555) == {}


def test_top_reactors_and_user_stats(db: Database) -> None:
    db.set_reactions(100, "😂", [BOB, CAROL])
    db.set_reactions(102, "😂", [BOB])
    db.add_reaction(101, BOB, "😂")  # own meme, not counted
    assert db.top_reactors(*ALL_TIME) == [(BOB, 2), (CAROL, 1)]
    assert db.user_stats(ALICE) == {
        "posted": 2,
        "received": 3,
        "given": 0,
        "best": (100, 2),
        "used_emoji": None,
        "received_emoji": ("😂", 3),
    }


def test_user_stats_top_emoji(db: Database) -> None:
    db.set_reactions(100, "😂", [BOB, CAROL])
    db.add_reaction(100, BOB, "🔥")
    db.add_reaction(102, BOB, "🔥")
    db.add_reaction(101, BOB, "123456")  # own meme, not counted
    db.add_reaction(101, ALICE, "123456")
    db.add_reaction(101, CAROL, "123456")
    bob = db.user_stats(BOB)
    assert bob["used_emoji"] == ("🔥", 2)
    assert bob["received_emoji"] == ("123456", 2)


def test_remove_and_clear_reactions(db: Database) -> None:
    db.set_reactions(100, "😂", [BOB, CAROL])
    db.add_reaction(100, BOB, "🔥")
    db.remove_reaction(100, CAROL, "😂")
    assert db.reaction_counts(100) == {"😂": 1, "🔥": 1}
    db.clear_reactions(100, "🔥")
    assert db.reaction_counts(100) == {"😂": 1}
    db.clear_reactions(100)
    assert db.reaction_counts(100) == {}


def test_reports_are_recorded(db: Database) -> None:
    db.mark_posted("week", "2026-10-19")
    assert db.posted_keys() == {("week", "2026-10-19")}
