"""Persisted ladders with the query results they were answered with.

A trace replays without an API key or a database.
"""

from pathlib import Path

from pydantic import BaseModel

from slayer_zoom.core import Ladder, PanelData, SlayerQuery, query_hash

DATA_DIR = Path(__file__).parent / "data"


class Trace(BaseModel):
    ladder: Ladder
    results: dict[str, PanelData]
    """Query hash to the rows SLayer returned when the trace was recorded."""


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


def trace_path(name: str) -> Path:
    return DATA_DIR / f"{name}.json"


def load_trace(name: str) -> Trace:
    return Trace.model_validate_json(trace_path(name).read_text())


def save_trace(name: str, trace: Trace) -> Path:
    path = trace_path(name)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(trace.model_dump_json(indent=2) + "\n")
    return path
