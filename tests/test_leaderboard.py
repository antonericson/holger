from datetime import datetime
from zoneinfo import ZoneInfo

from holger.leaderboard import MEDALS, build_report, plural, rank
from holger.periods import previous_period

PERIOD = previous_period("week", datetime(2026, 10, 28, tzinfo=ZoneInfo("UTC")))


def test_rank_shares_places_on_ties() -> None:
    rows = [("a", 5), ("b", 5), ("c", 3), ("d", 2), ("e", 1)]
    assert rank(rows) == [(0, "a", 5), (0, "b", 5), (2, "c", 3)]


def test_rank_caps_entries() -> None:
    rows = [(k, 1) for k in "abcdefg"]
    assert len(rank(rows)) == 5


def test_rank_with_fewer_than_three() -> None:
    assert rank([("a", 1)]) == [(0, "a", 1)]
    assert rank([]) == []


def test_plural() -> None:
    assert plural(1, "meme") == "1 meme"
    assert plural(2, "meme") == "2 memes"
    assert plural(0, "meme") == "0 memes"


def test_report_with_no_memes() -> None:
    posts = build_report(PERIOD, [], [], [])
    assert len(posts) == 1
    assert posts[0].meme_id is None
    assert PERIOD.title in posts[0].content


def test_report_with_unreacted_memes_still_lists_posters() -> None:
    posts = build_report(PERIOD, [], [(1, 2)], [])
    assert [p.meme_id for p in posts] == [None, None]
    assert "<@1>" in posts[1].content
    assert "2 memes" in posts[1].content


def test_report_replies_to_winning_memes() -> None:
    posts = build_report(PERIOD, [(100, 1, 4), (101, 2, 1)], [(1, 1), (2, 1)], [(3, 5)])
    assert PERIOD.title in posts[0].content
    assert [p.meme_id for p in posts] == [None, 100, 101, None, None]
    assert posts[1].content.startswith(MEDALS[0])
    assert "<@1>" in posts[1].content
    assert "4 reactions" in posts[1].content
    assert posts[2].content.startswith(MEDALS[1])
    assert "1 reaction" in posts[2].content
    assert "1 reactions" not in posts[2].content
    assert "<@3>" in posts[4].content
    assert "5 reactions" in posts[4].content
