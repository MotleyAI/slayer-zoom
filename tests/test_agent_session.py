import json

import pytest

from slayer_zoom.agent import Budget, LadderSession, ToolFailure
from slayer_zoom.catalog import Catalog
from slayer_zoom.core import Panel, PanelKind, ResolvedLevel, SlayerQuery, StepKind
from slayer_zoom.executor import SlayerExecutor
from slayer_zoom.traces import LADDER, QUESTION


@pytest.fixture
def events() -> list[tuple[str, object]]:
    return []


@pytest.fixture
def session(catalog: Catalog, executor: SlayerExecutor, events: list[tuple[str, object]]) -> LadderSession:
    return LadderSession(
        QUESTION, catalog, executor, "context", emit=lambda kind, data: events.append((kind, data))
    )


def _submit(session: LadderSession, index: int) -> dict:
    level = LADDER.levels[index]
    return json.loads(session.submit_level(level.title, level.panels, level.rationale))


def test_accepts_the_handwritten_ladder_level_by_level(session: LadderSession, events: list) -> None:
    for index in range(len(LADDER.levels)):
        assert _submit(session, index)["accepted"] == index
    assert session.ladder() == LADDER
    landed = [data for kind, data in events if kind == "level"]
    assert [level.index for level in landed if isinstance(level, ResolvedLevel)] == [0, 1, 2, 3, 4]
    assert [s.level for s in session.steps if s.kind == StepKind.LEVEL] == [0, 1, 2, 3, 4]


def test_rejects_a_level_that_drops_a_panel(session: LadderSession, events: list) -> None:
    _submit(session, 0)
    by_store = LADDER.levels[1].panels[1].model_copy(update={"parent": None})
    with pytest.raises(ToolFailure, match="drops panel total"):
        session.submit_level("Split", [by_store], "Where it comes from.")
    assert len(session.levels) == 1
    assert sum(kind == "level" for kind, _ in events) == 1


def test_rejects_a_query_the_semantic_layer_does_not_know(session: LadderSession) -> None:
    bad = Panel(
        id="bad", kind=PanelKind.KPI, title="Bad", query=SlayerQuery(source_model="orders", measures=["nope"])
    )
    with pytest.raises(ToolFailure, match="panel bad"):
        session.submit_level("Number", [bad], "The answer.")
    assert session.levels == []


def test_rejects_a_panel_without_rows(session: LadderSession) -> None:
    query = SlayerQuery(
        source_model="orders", measures=["order_count"], filters=["status = 'nope'"], dimensions=["status"]
    )
    empty = Panel(id="empty", kind=PanelKind.BAR, title="Empty", query=query)
    with pytest.raises(ToolFailure, match="no rows"):
        session.submit_level("Number", [empty], "Nothing.")


def test_reports_split_dimensions_nobody_explored(session: LadderSession) -> None:
    _submit(session, 0)
    assert _submit(session, 1)["unexplored"] == ["stores.name"]


def test_a_profile_counts_as_exploring(session: LadderSession) -> None:
    session.profile_dimension("orders", "stores.name")
    _submit(session, 0)
    assert _submit(session, 1)["unexplored"] == []


def test_probe_returns_at_most_twenty_rows(session: LadderSession) -> None:
    result = json.loads(
        session.probe_query(
            SlayerQuery(source_model="orders", measures=["order_count"], dimensions=["customer_id"])
        )
    )
    assert len(result["rows"]) == 20


def test_finish_needs_two_levels(session: LadderSession) -> None:
    _submit(session, 0)
    with pytest.raises(ToolFailure, match="at least 2"):
        session.finish("Done.")
    _submit(session, 1)
    assert session.finish("Done.") == "finished"
    with pytest.raises(ToolFailure, match="finished"):
        session.list_models()


def test_budget_stops_the_run_and_keeps_levels(catalog: Catalog, executor: SlayerExecutor) -> None:
    session = LadderSession(QUESTION, catalog, executor, "context", budget=Budget(max_tool_calls=2))
    _submit(session, 0)
    session.read_context()
    with pytest.raises(ToolFailure, match="budget"):
        session.list_models()
    assert session.finished
    assert len(session.levels) == 1


def test_every_tool_call_is_a_step_and_a_note(session: LadderSession, events: list) -> None:
    session.read_context()
    session.describe_model("orders")
    tools = [s.tool for s in session.steps if s.kind == StepKind.TOOL]
    assert tools == ["read_context", "describe_model"]
    assert [kind for kind, _ in events] == ["note", "note"]
