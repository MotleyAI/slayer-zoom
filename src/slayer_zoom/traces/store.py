"""Persisted ladders with the query results they were answered with, and the agent steps that built them.

A trace replays without an API key or a database.
"""

import re
from pathlib import Path

from pydantic import BaseModel

from slayer_zoom.core import (
    AgentStep,
    Digest,
    Ladder,
    PanelData,
    QueryRunner,
    Segment,
    SlayerQuery,
    query_hash,
)

DATA_DIR = Path(__file__).parent / "data"


class Trace(BaseModel):
    ladder: Ladder
    results: dict[str, PanelData]
    """Query hash to the rows SLayer returned when the trace was recorded."""
    steps: list[AgentStep] = []
    """The agent run that built the ladder, in order. Empty for a hand-written ladder."""
    summary: str = ""
    usage: dict[str, int] = {}
    """Tokens the agent run used, by kind."""
    narration: list[Segment] = []
    """The answer's text in reading order; each segment carries the level it appears at."""
    digests: list[Digest] = []
    """Per level: the question it answers, its headline and the summary of the answer so far."""


class TraceMiss(LookupError):
    """The trace has no recorded result for this query."""


class ReplayRunner:
    """A query runner that only answers from a trace's recorded results."""

    def __init__(self, trace: Trace) -> None:
        self._results = trace.results

    def run(self, query: SlayerQuery) -> PanelData:
        key = query_hash(query)
        if key not in self._results:
            raise TraceMiss(f"no recorded result for query {key}")
        return self._results[key]


class RecordingRunner:
    """Runs queries through another runner and keeps every result, so the run can be saved as a trace."""

    def __init__(self, inner: QueryRunner) -> None:
        self._inner = inner
        self.results: dict[str, PanelData] = {}

    def run(self, query: SlayerQuery) -> PanelData:
        data = self._inner.run(query)
        self.results[query_hash(query)] = data
        return data


def normalize_question(question: str) -> str:
    return " ".join(question.lower().strip().rstrip("?.!").split())


def slug(question: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", normalize_question(question)).strip("_")[:60]


def trace_path(name: str, directory: Path = DATA_DIR) -> Path:
    return directory / f"{name}.json"


def load_trace(name: str, directory: Path = DATA_DIR) -> Trace:
    return Trace.model_validate_json(trace_path(name, directory).read_text())


def save_trace(name: str, trace: Trace, directory: Path = DATA_DIR) -> Path:
    path = trace_path(name, directory)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(trace.model_dump_json(indent=2) + "\n")
    return path


def load_traces(directory: Path = DATA_DIR) -> list[Trace]:
    """Every stored trace, agent-built ones first so they win over a hand-written ladder."""
    traces = [Trace.model_validate_json(path.read_text()) for path in sorted(directory.glob("*.json"))]
    return sorted(traces, key=lambda trace: not trace.steps)


def find_trace(question: str, traces: list[Trace]) -> Trace | None:
    wanted = normalize_question(question)
    return next((t for t in traces if normalize_question(t.ladder.question) == wanted), None)
