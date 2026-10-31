"""Ranking and message formatting. No Discord or database access here."""

from dataclasses import dataclass

from holger.periods import Period

MEDALS = (":first_place:", ":second_place:", ":third_place:")
MEME_CHEERS = (":clap::clap:", ":raised_hands:", ":+1:")
USER_CHEERS = (":joy:", ":smile:", ":upside_down:")


@dataclass(frozen=True)
class Post:
    content: str
    meme_id: int | None = None  # reply to this meme and append its media link


def rank[T](rows: list[tuple[T, int]], places: int = 3, max_entries: int = 5) -> list[tuple[int, T, int]]:
    """(place, key, score) for the top `places` scores, ties sharing a place.

    `rows` must be sorted by score, highest first.
    """
    ranked: list[tuple[int, T, int]] = []
    place = 0
    for i, (key, score) in enumerate(rows):
        if i and score != rows[i - 1][1]:
            place = i
        if place >= places or len(ranked) >= max_entries:
            break
        ranked.append((place, key, score))
    return ranked


def plural(n: int, word: str) -> str:
    return f"{n} {word}" if n == 1 else f"{n} {word}s"


def build_report(
    period: Period,
    memes: list[tuple[int, int, int]],
    posters: list[tuple[int, int]],
    reactors: list[tuple[int, int]],
) -> list[Post]:
    if not posters:
        return [Post(f":trophy: No memes posted in {period.title} :cry:")]

    posts = [Post(f":trophy: Top memes of {period.title} :trophy:")]

    authors = {message_id: author_id for message_id, author_id, _ in memes}
    for place, message_id, score in rank([(m, s) for m, _, s in memes]):
        posts.append(
            Post(
                f"{MEDALS[place]} <@{authors[message_id]}> with {plural(score, 'reaction')} {MEME_CHEERS[place]}",
                meme_id=message_id,
            )
        )

    lines = [f"Top meme posters of {period.title} :rofl:"]
    for place, user_id, posted in rank(posters):
        lines.append(f"{MEDALS[place]} <@{user_id}> with {plural(posted, 'meme')} posted {USER_CHEERS[place]}")
    posts.append(Post("\n".join(lines)))

    if reactors:
        lines = [f"Top meme enjoyers of {period.title} :rofl:"]
        for place, user_id, given in rank(reactors):
            lines.append(f"{MEDALS[place]} <@{user_id}> with {plural(given, 'reaction')} to memes {USER_CHEERS[place]}")
        posts.append(Post("\n".join(lines)))

    return posts
