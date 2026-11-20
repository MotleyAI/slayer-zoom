import pytest

from slayer_zoom.core import (
    AgentStep,
    PanelData,
    SlayerQuery,
    StepKind,
    monotonic_violations,
    query_hash,
    reconciles,
)
from slayer_zoom.traces import (
    LADDER,
    RecordingRunner,
    ReplayRunner,
    TraceMiss,
    find_trace,
    load_trace,
    load_traces,
    save_trace,
    slug,
)


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


def test_agent_traces_come_first_and_questions_match_loosely(trace, tmp_path) -> None:
    agent = trace.model_copy(update={"steps": [AgentStep(kind=StepKind.NOTE, text="hi")]})
    save_trace("a_handwritten", trace, tmp_path)
    save_trace("b_agent", agent, tmp_path)
    traces = load_traces(tmp_path)
    assert traces[0].steps
    assert find_trace("  WHAT is our revenue year to date ", traces) is traces[0]
    assert find_trace("How many stores?", traces) is None


def test_recording_runner_keeps_every_result(trace) -> None:
    recorder = RecordingRunner(ReplayRunner(trace))
    query = trace.ladder.levels[0].panels[0].query
    assert recorder.run(query) == trace.results[query_hash(query)]
    assert list(recorder.results) == [query_hash(query)]


def test_slugs_are_file_names() -> None:
    assert slug("What is our revenue, year to date?") == "what_is_our_revenue_year_to_date"
