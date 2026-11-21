"""Stretchtext: the answer as one text that grows level by level, and the checks that keep it honest.

Level n's text is every segment with `level <= n`, in reading order. A level only inserts segments; it never
rewrites or reorders earlier ones. A segment may introduce a panel, which the reader sees right after it.
"""

import re
from collections.abc import Iterable

from pydantic import BaseModel, Field

from slayer_zoom.core.models import Cell


class Segment(BaseModel):
    id: str = Field(pattern=r"^[a-z0-9_]+$")
    level: int = Field(ge=0)
    text: str
    panel: str | None = None
    """Id of the panel shown right after this segment, if it introduces one."""


class Digest(BaseModel):
    """What a depth adds, at a glance: the question it answers, its finding in a few words, and a summary of
    the whole answer so far. The summary is the one part of the text that is rewritten at each depth."""

    level: int = Field(ge=0)
    question: str
    headline: str
    summary: str


def digest_at(digests: list[Digest], level: int) -> list[Digest]:
    return [d for d in digests if d.level <= level]


class Insertion(BaseModel):
    """A new segment and where it goes: after the segment with id `after`, or at the start when it is None."""

    segment: Segment
    after: str | None = None


def text_at(segments: list[Segment], level: int) -> list[Segment]:
    return [s for s in segments if s.level <= level]


def insert_segments(segments: list[Segment], insertions: Iterable[Insertion]) -> list[Segment]:
    """Places each insertion after its anchor. Insertions after the same anchor keep their given order."""
    result = list(segments)
    known = {s.id for s in segments}
    last_after: dict[str | None, str] = {}
    for insertion in insertions:
        if insertion.segment.id in known:
            raise ValueError(f"segment id {insertion.segment.id} is already used")
        if insertion.after is not None and insertion.after not in known:
            raise ValueError(f"segment {insertion.segment.id} follows unknown segment {insertion.after}")
        anchor = last_after.get(insertion.after, insertion.after)
        position = 0 if anchor is None else next(i for i, s in enumerate(result) if s.id == anchor) + 1
        result.insert(position, insertion.segment)
        known.add(insertion.segment.id)
        last_after[insertion.after] = insertion.segment.id
    return result


def expansion_violations(before: list[Segment], after: list[Segment]) -> list[str]:
    """The later text keeps every earlier segment, unchanged and in the same order."""
    kept = [s for s in after if s.id in {b.id for b in before}]
    if kept != before:
        return ["the new text rewrites, drops or reorders earlier segments"]
    return []


_NUMBER = re.compile(r"(?<![\w.])(\$)?(\d{1,3}(?:,\d{3})+|\d+)(\.\d+)?\s?(%|[KMB]\b)?", re.IGNORECASE)
_SCALE = {"": 1.0, "k": 1e3, "m": 1e6, "b": 1e9}


def _numbers(rows: Iterable[dict[str, Cell]]) -> list[float]:
    return [
        float(v)
        for row in rows
        for v in row.values()
        if isinstance(v, int | float) and not isinstance(v, bool)
    ]


def _matches(stated: float, decimals: int, scale: float, percent: bool, value: float) -> bool:
    """The stated figure is the value as a reader sees it: rounded, sign dropped, scaled or a percent."""
    candidates = [value * 100, value] if percent else [value / scale]
    return any(abs(abs(shown) - stated) <= 10.0**-decimals / 2 + 1e-9 for shown in candidates)


def ungrounded_numbers(text: str, rows: Iterable[dict[str, Cell]]) -> list[str]:
    """Numbers in the text no result value rounds to. Years and small counts in digits are allowed."""
    values = _numbers(rows)
    problems: list[str] = []
    for match in _NUMBER.finditer(text):
        currency, whole, fraction, suffix = match.groups()
        stated = float(whole.replace(",", "") + (fraction or ""))
        suffix = (suffix or "").lower()
        if not currency and not fraction and not suffix and (stated <= 12 or 1990 <= stated <= 2100):
            continue
        decimals = len(fraction) - 1 if fraction else 0
        if not any(_matches(stated, decimals, _SCALE.get(suffix, 1.0), suffix == "%", v) for v in values):
            problems.append(match.group(0).strip())
    return problems
