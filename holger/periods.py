"""Calendar periods (week/month/year) and which leaderboards are due."""

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

KINDS = ("week", "month", "year")

# How late a report may still be posted, e.g. after the server was down.
GRACE = {
    "week": timedelta(days=3),
    "month": timedelta(days=7),
    "year": timedelta(days=14),
}


@dataclass(frozen=True)
class Period:
    kind: str
    start: datetime  # inclusive, timezone-aware
    end: datetime  # exclusive, timezone-aware

    @property
    def key(self) -> tuple[str, str]:
        return self.kind, self.start.date().isoformat()

    @property
    def title(self) -> str:
        if self.kind == "week":
            return f"week {self.start.isocalendar().week}"
        if self.kind == "month":
            return self.start.strftime("%B %Y")
        return str(self.start.year)


def _period_start(kind: str, day: date) -> date:
    if kind == "week":
        return day - timedelta(days=day.weekday())
    if kind == "month":
        return day.replace(day=1)
    if kind == "year":
        return day.replace(month=1, day=1)
    raise ValueError(f"Unknown period kind {kind!r}")


def _midnight(day: date, now: datetime) -> datetime:
    return datetime.combine(day, time(), tzinfo=now.tzinfo)


def current_period(kind: str, now: datetime) -> Period:
    """The period that contains `now`, ending at `now`."""
    return Period(kind, _midnight(_period_start(kind, now.date()), now), now)


def previous_period(kind: str, now: datetime) -> Period:
    """The last complete period before the one containing `now`."""
    end = _period_start(kind, now.date())
    start = _period_start(kind, end - timedelta(days=1))
    return Period(kind, _midnight(start, now), _midnight(end, now))


def due_periods(now: datetime, posted: set[tuple[str, str]]) -> list[Period]:
    """Previous periods that have not been posted and are still within their grace window."""
    due: list[Period] = []
    for kind in KINDS:
        period = previous_period(kind, now)
        if period.key not in posted and now - period.end <= GRACE[kind]:
            due.append(period)
    return due
