import json
import os
from collections.abc import Iterator
from typing import Any

from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from slayer_zoom.core import Ladder, QueryRunner, resolve_level
from slayer_zoom.executor import demo_executor
from slayer_zoom.traces import ReplayRunner, Trace, load_trace

DEMO_TRACE = "revenue_ytd"


class AnswerRequest(BaseModel):
    question: str


def _sse(event: str, data: object) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


def _normalize(question: str) -> str:
    return " ".join(question.lower().strip(" ?").split())


def _default_runner(trace: Trace) -> QueryRunner:
    """Replay the trace unless SLAYER_ZOOM_LIVE asks for the live demo database."""
    if os.environ.get("SLAYER_ZOOM_LIVE"):
        return demo_executor(os.environ.get("SLAYER_ZOOM_STORAGE", ".slayer"))
    return ReplayRunner(trace)


def create_app(trace: Trace | None = None, runner: QueryRunner | None = None) -> FastAPI:
    app = FastAPI(title="slayer-zoom")
    loaded = trace or load_trace(DEMO_TRACE)
    queries = runner or _default_runner(loaded)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/schema/ladder")
    def ladder_schema() -> dict[str, Any]:
        return Ladder.model_json_schema()

    @app.post("/answer")
    def answer(request: AnswerRequest) -> StreamingResponse:
        def events() -> Iterator[str]:
            ladder = loaded.ladder
            if _normalize(request.question) != _normalize(ladder.question):
                yield _sse("error", {"message": f"Until the ladder agent lands (#2), ask: {ladder.question}"})
                return
            yield _sse("ladder", {"question": ladder.question, "levels": len(ladder.levels)})
            for level in ladder.levels:
                yield _sse("level", resolve_level(level, queries).model_dump(mode="json"))
            yield _sse("done", {})

        return StreamingResponse(events(), media_type="text/event-stream")

    return app
