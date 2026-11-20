import json
import os
import queue
import threading
from collections.abc import Callable, Iterator
from typing import Any

from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from slayer_zoom.agent import Emit, EventKind, answer_live
from slayer_zoom.core import Ladder, QueryRunner, ResolvedLevel, StepKind, resolve_level
from slayer_zoom.executor import demo_executor
from slayer_zoom.traces import ReplayRunner, Trace, find_trace, load_traces

Agent = Callable[[str, Emit], Trace | None]
"""Builds a ladder for a question, emitting notes and levels as they happen."""


class AnswerRequest(BaseModel):
    question: str


def _sse(event: str, data: object) -> str:
    payload = data.model_dump(mode="json") if isinstance(data, BaseModel) else data
    return f"event: {event}\ndata: {json.dumps(payload)}\n\n"


def _live() -> bool:
    return bool(os.environ.get("SLAYER_ZOOM_LIVE"))


def _storage() -> str:
    return os.environ.get("SLAYER_ZOOM_STORAGE", ".slayer")


def _default_agent() -> Agent | None:
    """The live agent needs the live demo database and an API key; otherwise only stored traces answer."""
    if not (_live() and os.environ.get("ANTHROPIC_API_KEY")):
        return None
    return lambda question, emit: answer_live(question, emit=emit, storage_path=_storage())


def replay(trace: Trace, runner: QueryRunner) -> Iterator[str]:
    """A stored trace as the event stream a live run produces: notes and levels in recorded order."""
    ladder = trace.ladder
    yield _sse("ladder", {"question": ladder.question, "levels": len(ladder.levels)})
    levels = {level.index: level for level in ladder.levels}
    landed: set[int] = set()
    for step in trace.steps:
        if step.kind == StepKind.LEVEL and step.level in levels:
            landed.add(step.level)
            yield _sse("level", resolve_level(levels[step.level], runner))
        elif step.kind != StepKind.LEVEL and step.text:
            yield _sse("note", {"text": step.text})
    for level in ladder.levels:
        if level.index not in landed:
            yield _sse("level", resolve_level(level, runner))
    yield _sse("done", {"summary": trace.summary})


def run_live(question: str, agent: Agent) -> Iterator[str]:
    """Runs the agent in a thread and streams its notes and levels as they land."""
    events: queue.Queue[tuple[str, object]] = queue.Queue()

    def emit(kind: EventKind, data: object) -> None:
        events.put((kind, data))

    def work() -> None:
        try:
            trace = agent(question, emit)
            events.put(("done", {"summary": trace.summary if trace else ""}))
        except Exception as error:  # the stream must end with a message, whatever failed
            events.put(("error", {"message": f"The agent failed: {error}"}))

    threading.Thread(target=work, daemon=True).start()
    yield _sse("ladder", {"question": question, "levels": None})
    while True:
        kind, data = events.get()
        if kind == "level" and isinstance(data, ResolvedLevel):
            yield _sse("level", data)
        else:
            yield _sse(kind, data)
        if kind in ("done", "error"):
            return


def create_app(
    traces: list[Trace] | None = None,
    runner: QueryRunner | None = None,
    agent: Agent | None = None,
) -> FastAPI:
    app = FastAPI(title="slayer-zoom")
    stored = traces if traces is not None else load_traces()
    live_runner = runner or (demo_executor(_storage()) if _live() else None)
    live_agent = agent or _default_agent()

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/schema/ladder")
    def ladder_schema() -> dict[str, Any]:
        return Ladder.model_json_schema()

    @app.get("/questions")
    def questions() -> dict[str, Any]:
        recorded = list(dict.fromkeys(t.ladder.question for t in stored))
        return {"recorded": recorded, "live": live_agent is not None}

    @app.post("/answer")
    def answer(request: AnswerRequest) -> StreamingResponse:
        def events() -> Iterator[str]:
            if trace := find_trace(request.question, stored):
                yield from replay(trace, live_runner or ReplayRunner(trace))
            elif live_agent is not None:
                yield from run_live(request.question, live_agent)
            else:
                asked = "; ".join(dict.fromkeys(t.ladder.question for t in stored))
                yield _sse(
                    "error", {"message": f"No API key here, so only recorded questions answer: {asked}"}
                )

        return StreamingResponse(events(), media_type="text/event-stream")

    return app
