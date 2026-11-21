import pytest

from slayer_zoom.core import (
    Insertion,
    Segment,
    expansion_violations,
    insert_segments,
    text_at,
    ungrounded_numbers,
)


def _s(sid: str, level: int, text: str = "x") -> Segment:
    return Segment(id=sid, level=level, text=text)


def test_insertions_land_after_their_anchor_in_order() -> None:
    base = [_s("a", 0), _s("b", 0)]
    grown = insert_segments(
        base, [Insertion(segment=_s("c", 1), after="a"), Insertion(segment=_s("d", 1), after="a")]
    )
    assert [s.id for s in grown] == ["a", "c", "d", "b"]
    assert [s.id for s in insert_segments(base, [Insertion(segment=_s("z", 1))])] == ["z", "a", "b"]


def test_insertion_rejects_unknown_anchors_and_reused_ids() -> None:
    base = [_s("a", 0)]
    ghost = [Insertion(segment=_s("c", 1), after="ghost")]
    reused = [Insertion(segment=_s("a", 1))]
    with pytest.raises(ValueError, match="unknown"):
        insert_segments(base, ghost)
    with pytest.raises(ValueError, match="already used"):
        insert_segments(base, reused)


def test_text_at_a_level_is_every_segment_up_to_it() -> None:
    segments = [_s("a", 0), _s("c", 1), _s("b", 0)]
    assert [s.id for s in text_at(segments, 0)] == ["a", "b"]


def test_expansion_keeps_earlier_segments_unchanged_and_in_order() -> None:
    before = [_s("a", 0), _s("b", 0)]
    assert expansion_violations(before, [_s("a", 0), _s("c", 1), _s("b", 0)]) == []
    assert expansion_violations(before, [_s("b", 0), _s("a", 0)])
    assert expansion_violations(before, [_s("a", 0, "changed"), _s("b", 0)])
    assert expansion_violations(before, [_s("a", 0)])


ROWS = [
    {"orders.revenue": 2058332.71, "orders.share": 0.4123, "orders.change": -0.0318, "orders.orders": 12345}
]


@pytest.mark.parametrize(
    "text",
    [
        "Revenue is $2.06M.",
        "Revenue is $2,058,333.",
        "Revenue is about $2.1M, 41% of it in Brooklyn.",
        "Brooklyn takes 41.2% of revenue, down 3.2% on last month.",
        "There were 12,345 orders across 4 stores in 2026.",
    ],
)
def test_figures_that_round_from_the_rows_are_grounded(text: str) -> None:
    assert ungrounded_numbers(text, ROWS) == []


@pytest.mark.parametrize(
    ("text", "bad"),
    [
        ("Revenue is $2.5M.", ["$2.5M"]),
        ("Brooklyn takes 45% of revenue.", ["45%"]),
        ("We had 13,000 orders.", ["13,000"]),
    ],
)
def test_made_up_figures_are_caught(text: str, bad: list[str]) -> None:
    assert ungrounded_numbers(text, ROWS) == bad
