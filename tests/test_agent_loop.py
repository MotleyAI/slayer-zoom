"""The agent loop without the network: a scripted runner stands in for Claude."""

from collections.abc import Iterator
from types import SimpleNamespace
from typing import Any, cast

import pytest
from anthropic.lib.tools import ToolError

from slayer_zoom.agent import MODEL, TOOL_NAMES, LadderSession, build_tools, run_agent
from slayer_zoom.catalog import Catalog
from slayer_zoom.core import StepKind
from slayer_zoom.executor import SlayerExecutor
from slayer_zoom.traces import LADDER, QUESTION


def _message(text: str = "", stop_reason: str = "tool_use") -> SimpleNamespace:
    blocks = [SimpleNamespace(type="text", text=text)] if text else []
    return SimpleNamespace(content=blocks, stop_reason=stop_reason)


class _ScriptedClient:
    """Plays the model: each step calls one tool the way the Tool Runner would, then yields a message."""

    def __init__(self, script: list[tuple[str, str, dict[str, Any]]]) -> None:
        self.script = script
        self.params: dict[str, Any] = {}
        self.beta = SimpleNamespace(messages=SimpleNamespace(tool_runner=self._runner))

    def _runner(self, **params: Any) -> Iterator[SimpleNamespace]:
        self.params = params
        tools = {tool.name: tool for tool in params["tools"]}
        for note, name, payload in self.script:
            yield _message(note)
            tools[name].call(payload)
        yield _message("All done.", stop_reason="end_turn")


def _level(index: int) -> dict[str, Any]:
    level = LADDER.levels[index]
    return {
        "title": level.title,
        "rationale": level.rationale,
        "panels": [p.model_dump(mode="json", exclude_none=True) for p in level.panels],
    }


@pytest.fixture
def session(catalog: Catalog, executor: SlayerExecutor) -> LadderSession:
    return LadderSession(QUESTION, catalog, executor, "context")


def test_the_tool_surface_has_no_sql_and_no_way_to_emit_numbers(session: LadderSession) -> None:
    tools = {tool.name: tool.to_dict() for tool in build_tools(session)}
    assert tuple(tools) == TOOL_NAMES
    assert not any("sql" in name for name in tools)
    submit = cast(dict[str, Any], tools["submit_level"]["input_schema"])
    assert set(submit["properties"]) == {"title", "panels", "rationale"}
    panel = submit["$defs"]["Panel"]["properties"]
    assert set(panel) == {"id", "kind", "title", "query", "parent"}


def test_a_tool_failure_goes_back_to_the_model_as_a_tool_error(session: LadderSession) -> None:
    finish = next(tool for tool in build_tools(session) if tool.name == "finish")
    with pytest.raises(ToolError, match="at least 2"):
        finish.call({"summary": "Too early."})
    assert session.steps[-1].tool == "finish"
    assert "at least 2" in (session.steps[-1].error or "")


def test_runs_the_script_streams_notes_and_stops_when_finished(session: LadderSession) -> None:
    client = _ScriptedClient(
        [
            ("Reading the context.", "read_context", {}),
            ("Building the number.", "submit_level", _level(0)),
            ("Splitting by store.", "submit_level", _level(1)),
            ("", "finish", {"summary": "Revenue, then by store."}),
        ]
    )
    run_agent(session, client, "system")  # type: ignore[arg-type]
    assert session.finished
    assert session.summary == "Revenue, then by store."
    assert [level.index for level in session.levels] == [0, 1]
    notes = [s.text for s in session.steps if s.kind == StepKind.NOTE]
    assert notes == ["Reading the context.", "Building the number.", "Splitting by store."]


def test_sends_the_model_thinking_effort_fallbacks_caching_and_a_bound(session: LadderSession) -> None:
    client = _ScriptedClient([])
    run_agent(session, client, "system")  # type: ignore[arg-type]
    params = client.params
    assert params["model"] == MODEL
    assert params["thinking"] == {"type": "adaptive"}
    assert params["output_config"] == {"effort": "medium"}
    assert params["fallbacks"] == "default"
    assert params["system"][0]["cache_control"] == {"type": "ephemeral"}
    assert params["max_iterations"] == session.budget.max_tool_calls + 5
    assert session.finished
    assert "ended before" in session.summary
