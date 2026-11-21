"""The narrator without the network: a scripted client returns drafts."""

from typing import Any

import pytest

from slayer_zoom.core import ResolvedLevel, expansion_violations, resolve_level, ungrounded_numbers
from slayer_zoom.narrator import MODEL, Draft, DraftInsertion, Narrator
from slayer_zoom.traces import ReplayRunner, load_trace


class _Reply:
    def __init__(self, draft: Draft | None) -> None:
        self._draft = draft

    @property
    def parsed_output(self) -> Draft | None:
        return self._draft

    @property
    def stop_reason(self) -> str | None:
        return "refusal" if self._draft is None else "end_turn"


class _Client:
    def __init__(self, drafts: list[Draft | None]) -> None:
        self.drafts = drafts
        self.calls: list[dict[str, Any]] = []

    @property
    def messages(self) -> "_Client":
        return self

    def parse(self, **params: Any) -> _Reply:
        self.calls.append(params)
        return _Reply(self.drafts.pop(0))


@pytest.fixture(scope="module")
def levels() -> list[ResolvedLevel]:
    trace = load_trace("revenue_ytd")
    return [resolve_level(level, ReplayRunner(trace)) for level in trace.ladder.levels]


def _millions(level: ResolvedLevel) -> str:
    value = level.panels[0].data.rows[0]["orders.revenue"]
    assert isinstance(value, float)
    return f"${value / 1e6:.2f}M"


def _d(*items: DraftInsertion) -> Draft:
    return Draft(insertions=list(items))


def test_inserts_the_draft_and_introduces_each_new_panel(levels: list[ResolvedLevel]) -> None:
    client = _Client(
        [_d(DraftInsertion(id="answer", text=f"Revenue this year is {_millions(levels[0])}.", panel="total"))]
    )
    segments = Narrator("q", client).narrate(levels[0])
    assert [(s.id, s.level, s.panel) for s in segments] == [("answer", 0, "total")]
    assert client.calls[0]["model"] == MODEL
    assert client.calls[0]["output_config"] == {"effort": "low"}


def test_a_made_up_figure_gets_one_retry_with_the_problem(levels: list[ResolvedLevel]) -> None:
    bad = _d(DraftInsertion(id="answer", text="Revenue this year is $9.99M.", panel="total"))
    good = _d(
        DraftInsertion(id="answer", text=f"Revenue this year is {_millions(levels[0])}.", panel="total")
    )
    client = _Client([bad, good])
    segments = Narrator("q", client).narrate(levels[0])
    assert "$9.99M" in client.calls[1]["messages"][0]["content"]
    assert segments[0].text.endswith(f"{_millions(levels[0])}.")


def test_ungrounded_text_is_dropped_and_the_panel_still_appears(levels: list[ResolvedLevel]) -> None:
    bad = _d(DraftInsertion(id="answer", text="Revenue this year is $9.99M.", panel="total"))
    client = _Client([bad, bad])
    segments = Narrator("q", client).narrate(levels[0])
    assert [s.panel for s in segments] == ["total"]
    assert all(not ungrounded_numbers(s.text, levels[0].panels[0].data.rows) for s in segments)


def test_a_refusal_falls_back_to_panel_titles(levels: list[ResolvedLevel]) -> None:
    segments = Narrator("q", _Client([None, None])).narrate(levels[0])
    assert segments[0].text == "Revenue year to date."


def test_later_levels_only_insert(levels: list[ResolvedLevel]) -> None:
    client = _Client(
        [
            _d(
                DraftInsertion(
                    id="answer", text=f"Revenue this year is {_millions(levels[0])}.", panel="total"
                )
            ),
            _d(
                DraftInsertion(
                    id="stores", text="Brooklyn leads the stores.", after="answer", panel="by_store"
                )
            ),
        ]
    )
    narrator = Narrator("q", client)
    first = list(narrator.narrate(levels[0]))
    second = narrator.narrate(levels[1])
    assert expansion_violations(first, second) == []
    assert [s.id for s in second] == ["answer", "stores"]
    assert second[1].level == 1
