import pytest

from slayer_zoom.core import PanelData, SlayerQuery, monotonic_violations, query_hash, reconciles
from slayer_zoom.traces import LADDER, ReplayRunner, TraceMiss, load_trace


@pytest.fixture(scope="module")
def trace():
    return load_trace("revenue_ytd")


def test_recorded_trace_is_the_handwritten_ladder(trace) -> None:
    assert trace.ladder == LADDER


def test_handwritten_ladder_is_monotonic() -> None:
    assert monotonic_violations(LADDER) == []


def test_trace_answers_every_panel_without_slayer(trace) -> None:
    runner = ReplayRunner(trace)
    for level in trace.ladder.levels:
        for panel in level.panels:
            assert runner.run(panel.query).rows, panel.id


def test_store_split_reconciles_with_the_total(trace) -> None:
    panels = {p.id: p for level in trace.ladder.levels for p in level.panels}
    total = trace.results[query_hash(panels["total"].query)].rows[0]["orders.revenue"]
    by_store = [row["orders.revenue"] for row in trace.results[query_hash(panels["by_store"].query)].rows]
    assert isinstance(total, float)
    assert reconciles(total, [float(v) for v in by_store if isinstance(v, int | float)])


def test_unrecorded_query_is_a_miss(trace) -> None:
    runner = ReplayRunner(trace)
    query = SlayerQuery(source_model="orders", measures=["order_count"])
    with pytest.raises(TraceMiss):
        runner.run(query)


def test_query_hash_ignores_key_order() -> None:
    a = SlayerQuery.model_validate({"source_model": "orders", "measures": ["x"], "dimensions": ["d"]})
    b = SlayerQuery.model_validate({"dimensions": ["d"], "measures": ["x"], "source_model": "orders"})
    assert query_hash(a) == query_hash(b)
    assert isinstance(PanelData(columns=[], rows=[]), PanelData)
