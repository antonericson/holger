from datetime import datetime
from zoneinfo import ZoneInfo

from holger.periods import current_period, due_periods, previous_period

TZ = ZoneInfo("Europe/Stockholm")


def at(*args: int) -> datetime:
    return datetime(*args, tzinfo=TZ)


def test_previous_week_is_monday_to_monday() -> None:
    p = previous_period("week", at(2026, 10, 28, 9))  # Wednesday
    assert (p.start, p.end) == (at(2026, 10, 19), at(2026, 10, 26))
    assert p.title == "week 43"


def test_previous_month_and_year() -> None:
    p = previous_period("month", at(2026, 3, 1, 9))
    assert (p.start, p.end) == (at(2026, 2, 1), at(2026, 3, 1))
    assert p.title == "February 2026"
    p = previous_period("year", at(2027, 1, 1, 9))
    assert (p.start, p.end) == (at(2026, 1, 1), at(2027, 1, 1))


def test_current_period_ends_now() -> None:
    now = at(2026, 10, 31, 12)
    assert current_period("month", now).start == at(2026, 10, 1)
    assert current_period("month", now).end == now


def test_due_on_monday_only_week() -> None:
    due = due_periods(at(2026, 10, 26, 9), posted=set())
    assert [p.kind for p in due] == ["week"]


def test_due_on_new_year_all_three() -> None:
    due = due_periods(at(2027, 1, 1, 9), posted=set())  # a Friday
    assert [p.kind for p in due] == ["month", "year"]
    due = due_periods(at(2029, 1, 1, 9), posted=set())  # a Monday
    assert [p.kind for p in due] == ["week", "month", "year"]


def test_catches_up_within_grace_but_not_after() -> None:
    assert [p.kind for p in due_periods(at(2026, 10, 28, 9), set())] == ["week"]
    assert due_periods(at(2026, 10, 30, 9), set()) == []


def test_posted_periods_are_not_due() -> None:
    now = at(2026, 10, 26, 9)
    posted = {previous_period("week", now).key}
    assert due_periods(now, posted) == []
