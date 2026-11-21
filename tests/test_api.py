import json
from typing import cast

from fastapi.testclient import TestClient

from slayer_zoom.agent import Emit
from slayer_zoom.api import create_app
from slayer_zoom.api.app import NarratorFactory
from slayer_zoom.core import AgentStep, Digest, ResolvedLevel, Segment, StepKind, resolve_level
from slayer_zoom.traces import QUESTION, ReplayRunner, Trace, load_trace


def _events(body: str) -> list[tuple[str, dict]]:
    events = []
    for block in body.strip().split("\n\n"):
        lines = dict(line.split(": ", 1) for line in block.splitlines())
        events.append((lines["event"], json.loads(lines["data"])))
    return events


def test_health() -> None:
    client = TestClient(create_app())
    assert client.get("/health").json() == {"status": "ok"}


def test_ladder_schema_names_the_levels() -> None:
    schema = TestClient(create_app()).get("/schema/ladder").json()
    assert schema["title"] == "Ladder"
    assert "levels" in schema["properties"]


def test_answer_streams_every_level_from_the_trace() -> None:
    app = create_app(traces=[load_trace("revenue_ytd")])
    response = TestClient(app).post("/answer", json={"question": "what is our revenue year to date"})
    assert response.headers["content-type"].startswith("text/event-stream")
    events = _events(response.text)
    kinds = [kind for kind, _ in events]
    assert [k for k in kinds if k != "narration"] == [
        "ladder",
        "level",
        "level",
        "level",
        "level",
        "level",
        "done",
    ]
    assert kinds.count("narration") == 5
    levels = [data for kind, data in events if kind == "level"]
    assert [level["index"] for level in levels] == [0, 1, 2, 3, 4]
    assert levels[0]["panels"][0]["data"]["rows"][0]["orders.revenue"] > 0


def test_other_questions_get_a_pointer_to_the_demo_question() -> None:
    events = _events(TestClient(create_app()).post("/answer", json={"question": "How many stores?"}).text)
    assert events[0][0] == "error"
    assert QUESTION in events[0][1]["message"]


def _agent_trace() -> Trace:
    """The demo trace dressed as an agent run: notes and tool steps between its first two levels."""
    recorded = load_trace("revenue_ytd")
    ladder = recorded.ladder.model_copy(update={"levels": recorded.ladder.levels[:2]})
    steps = [
        AgentStep(kind=StepKind.NOTE, text="Reading the context."),
        AgentStep(kind=StepKind.TOOL, text="Profiling stores.name in orders", tool="profile_dimension"),
        AgentStep(kind=StepKind.LEVEL, text="Number", level=0),
        AgentStep(kind=StepKind.LEVEL, text="Split", level=1),
    ]
    return recorded.model_copy(
        update={"ladder": ladder, "steps": steps, "summary": "Revenue, then by store.", "narration": []}
    )


def test_replays_an_agent_trace_with_its_notes_in_order() -> None:
    client = TestClient(create_app(traces=[_agent_trace()]))
    events = _events(client.post("/answer", json={"question": QUESTION}).text)
    assert [kind for kind, _ in events] == ["ladder", "note", "note", "level", "level", "done"]
    assert events[1][1] == {"text": "Reading the context."}
    assert events[-1][1] == {"summary": "Revenue, then by store."}


def test_streams_a_live_agent_run_as_it_happens() -> None:
    level = _agent_trace().ladder.levels[0]

    def agent(question: str, emit: Emit) -> Trace | None:
        emit("note", {"text": f"Thinking about {question}"})
        emit("level", resolve_level(level, ReplayRunner(load_trace("revenue_ytd"))))
        return _agent_trace()

    client = TestClient(create_app(traces=[], agent=agent))
    events = _events(client.post("/answer", json={"question": "How many orders?"}).text)
    assert [kind for kind, _ in events] == ["ladder", "note", "level", "done"]
    assert events[0][1] == {"question": "How many orders?", "levels": None}
    assert events[2][1]["panels"][0]["data"]["rows"]


def test_a_failing_agent_ends_the_stream_with_an_error() -> None:
    def agent(question: str, emit: Emit) -> Trace | None:
        raise RuntimeError("no credit")

    events = _events(
        TestClient(create_app(traces=[], agent=agent)).post("/answer", json={"question": "x"}).text
    )
    assert events[-1] == ("error", {"message": "The agent failed: no credit"})


def test_lists_the_recorded_questions() -> None:
    body = TestClient(create_app(traces=[_agent_trace()])).get("/questions").json()
    assert body == {"recorded": [QUESTION], "live": False}


def test_replay_sends_the_text_up_to_each_level_after_it() -> None:
    narration = [
        Segment(id="answer", level=0, text="Revenue is up.", panel="total"),
        Segment(id="stores", level=1, text="Brooklyn leads.", panel="by_store"),
    ]
    digests = [
        Digest(level=0, question="How much?", headline="Up", summary="Revenue is up."),
        Digest(level=1, question="Where from?", headline="Brooklyn", summary="Up, led by Brooklyn."),
    ]
    trace = _agent_trace().model_copy(update={"narration": narration, "digests": digests})
    events = _events(TestClient(create_app(traces=[trace])).post("/answer", json={"question": QUESTION}).text)
    texts = [[s["id"] for s in data["segments"]] for kind, data in events if kind == "narration"]
    assert texts == [["answer"], ["answer", "stores"]]
    summaries = [[d["summary"] for d in data["digests"]] for kind, data in events if kind == "narration"]
    assert summaries == [["Revenue is up."], ["Revenue is up.", "Up, led by Brooklyn."]]
    kinds = [kind for kind, _ in events]
    assert kinds.index("narration") == kinds.index("level") + 1


class _FakeNarrator:
    def __init__(self, question: str) -> None:
        self.segments: list[Segment] = []
        self.digests: list[Digest] = []

    def narrate(self, level: ResolvedLevel) -> list[Segment]:
        self.segments.append(Segment(id=f"s{level.index}", level=level.index, text="Text."))
        self.digests.append(Digest(level=level.index, question="Why?", headline="Up", summary="Up."))
        return self.segments


def test_a_live_run_narrates_each_level_before_it_is_done() -> None:
    level = _agent_trace().ladder.levels[0]

    def agent(question: str, emit: Emit) -> Trace | None:
        emit("level", resolve_level(level, ReplayRunner(load_trace("revenue_ytd"))))
        return _agent_trace()

    app = create_app(traces=[], agent=agent, narrator=cast(NarratorFactory, _FakeNarrator))
    events = _events(TestClient(app).post("/answer", json={"question": "How many orders?"}).text)
    assert [kind for kind, _ in events] == ["ladder", "level", "narration", "done"]
    assert events[2][1] == {
        "level": 0,
        "segments": [{"id": "s0", "level": 0, "text": "Text.", "panel": None}],
        "digests": [{"level": 0, "question": "Why?", "headline": "Up", "summary": "Up."}],
    }
