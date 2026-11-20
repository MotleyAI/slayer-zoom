import pytest

from slayer_zoom.core import Ladder, Level, Panel, PanelKind, SlayerQuery, monotonic_violations, reconciles


def _panel(pid: str, kind: PanelKind = PanelKind.KPI, parent: str | None = None, *dims: str) -> Panel:
    query = SlayerQuery(source_model="orders", measures=["order_total:sum"], dimensions=list(dims))
    return Panel(id=pid, kind=kind, title=pid, query=query, parent=parent)


def _ladder(*levels: list[Panel]) -> Ladder:
    return Ladder(
        question="What is our revenue year to date?",
        levels=[Level(index=i, title=f"L{i}", panels=panels) for i, panels in enumerate(levels)],
    )


def test_keeping_and_refining_panels_is_monotonic() -> None:
    ladder = _ladder(
        [_panel("total")],
        [_panel("total"), _panel("by_store", PanelKind.BAR, "total", "stores.name")],
        [_panel("total"), _panel("by_store_product", PanelKind.TABLE, "by_store", "stores.name", "type")],
    )
    assert monotonic_violations(ladder) == []


def test_dropping_a_panel_without_refining_it_is_a_violation() -> None:
    ladder = _ladder([_panel("total")], [_panel("other")])
    assert monotonic_violations(ladder) == ["level 1 drops panel total without refining it"]


def test_refining_an_unknown_panel_is_a_violation() -> None:
    ladder = _ladder([_panel("total")], [_panel("total"), _panel("split", PanelKind.BAR, "ghost")])
    assert monotonic_violations(ladder) == ["panel split in level 1 refines unknown panel ghost"]


def test_level_indices_must_follow_positions() -> None:
    ladder = Ladder(question="q", levels=[Level(index=1, title="L1", panels=[_panel("total")])])
    assert monotonic_violations(ladder) == ["level at position 0 has index 1"]


def test_repeated_panel_ids_in_a_level_are_a_violation() -> None:
    ladder = _ladder([_panel("total"), _panel("total")])
    assert monotonic_violations(ladder) == ["level 0 repeats panel id total"]


@pytest.mark.parametrize(
    ("parent", "children", "expected"),
    [
        (100.0, [60.0, 40.0], True),
        (100.0, [33.333, 33.333, 33.334], True),
        (100.0, [60.0, 39.0], False),
    ],
)
def test_reconciles(parent: float, children: list[float], expected: bool) -> None:
    assert reconciles(parent, children) is expected


def test_changing_the_query_of_a_kept_panel_is_a_violation() -> None:
    ladder = _ladder([_panel("total")], [_panel("total", PanelKind.KPI, None, "status")])
    assert monotonic_violations(ladder) == ["level 1 changes the query of kept panel total"]
