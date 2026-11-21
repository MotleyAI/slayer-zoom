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
from slayer_zoom.core import Ladder, ResolvedLevel, Segment, StepKind, resolve_level, text_at
from slayer_zoom.narrator import Narrator, live_narrator
from slayer_zoom.traces import ReplayRunner, Trace, find_trace, load_traces

Agent = Callable[[str, Emit], Trace | None]
"""Builds a ladder for a question, emitting notes and levels as they happen."""
NarratorFactory = Callable[[str], Narrator]
"""Makes the narrator that writes one answer's text."""


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


def _narration(level: int, segments: list[Segment]) -> str:
    return _sse("narration", {"level": level, "segments": [s.model_dump(mode="json") for s in segments]})


def replay(trace: Trace) -> Iterator[str]:
    """A stored trace as the event stream a live run produces: notes, levels and text in recorded order.

    Always from the recorded results, so the text and the charts come from the same rows.
    """
    runner = ReplayRunner(trace)
    ladder = trace.ladder
    yield _sse("ladder", {"question": ladder.question, "levels": len(ladder.levels)})
    levels = {level.index: level for level in ladder.levels}
    order = [s.level for s in trace.steps if s.kind == StepKind.LEVEL and s.level in levels]
    order += [index for index in levels if index not in order]
    pending = list(trace.steps)
    for index in order:
        while pending and not (pending[0].kind == StepKind.LEVEL and pending[0].level == index):
            step = pending.pop(0)
            if step.kind != StepKind.LEVEL and step.text:
                yield _sse("note", {"text": step.text})
        if pending:
            pending.pop(0)
        yield _sse("level", resolve_level(levels[index], runner))
        if trace.narration:
            yield _narration(index, text_at(trace.narration, index))
    for step in pending:
        if step.kind != StepKind.LEVEL and step.text:
            yield _sse("note", {"text": step.text})
    yield _sse("done", {"summary": trace.summary})


def run_live(question: str, agent: Agent, narrator: NarratorFactory | None = None) -> Iterator[str]:
    """Runs the agent in a thread, narrates each level in a second thread, and streams both as they land."""
    events: queue.Queue[tuple[str, object]] = queue.Queue()
    landed: queue.Queue[ResolvedLevel | None] = queue.Queue()

    def emit(kind: EventKind, data: object) -> None:
        events.put((kind, data))
        if kind == "level" and isinstance(data, ResolvedLevel):
            landed.put(data)

    def narrate() -> None:
        writer = narrator(question) if narrator else None
        while (level := landed.get()) is not None:
            if writer is None:
                continue
            try:
                events.put(("narration", (level.index, list(writer.narrate(level)))))
            except Exception as error:  # a level without text still shows its panels
                events.put(("note", {"text": f"No text for level {level.index + 1}: {error}"}))

    def work() -> None:
        try:
            trace = agent(question, emit)
            summary: dict[str, object] = {"summary": trace.summary if trace else ""}
        except Exception as error:  # the stream must end with a message, whatever failed
            summary = {"message": f"The agent failed: {error}"}
        landed.put(None)
        writer_thread.join()
        events.put(("error" if "message" in summary else "done", summary))

    writer_thread = threading.Thread(target=narrate, daemon=True)
    writer_thread.start()
    threading.Thread(target=work, daemon=True).start()
    yield _sse("ladder", {"question": question, "levels": None})
    while True:
        kind, data = events.get()
        if kind == "narration" and isinstance(data, tuple):
            yield _narration(*data)
        else:
            yield _sse(kind, data)
        if kind in ("done", "error"):
            return


def create_app(
    traces: list[Trace] | None = None,
    agent: Agent | None = None,
    narrator: NarratorFactory | None = None,
) -> FastAPI:
    app = FastAPI(title="slayer-zoom")
    stored = traces if traces is not None else load_traces()
    live_agent = agent or _default_agent()
    live_writer = narrator or (live_narrator if live_agent is not None and agent is None else None)

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
                yield from replay(trace)
            elif live_agent is not None:
                yield from run_live(request.question, live_agent, live_writer)
            else:
                asked = "; ".join(dict.fromkeys(t.ladder.question for t in stored))
                yield _sse(
                    "error", {"message": f"No API key here, so only recorded questions answer: {asked}"}
                )

        return StreamingResponse(events(), media_type="text/event-stream")

    return app
