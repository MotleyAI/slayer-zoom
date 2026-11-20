"""One agent run: the tools the ladder agent may call, their checks, and the record of what it did.

The agent plans and never answers: its only outputs are SLayer queries inside panels, and short titles and
rationales. Every number the reader sees comes from running those queries.
"""

import json
from collections.abc import Callable
from typing import Literal

from pydantic import BaseModel, JsonValue, ValidationError

from slayer_zoom.catalog import Catalog
from slayer_zoom.core import (
    AgentStep,
    Ladder,
    Level,
    Panel,
    QueryRunner,
    ResolvedLevel,
    SlayerQuery,
    StepKind,
    monotonic_violations,
    resolve_level,
)

PROBE_ROWS = 20
PREVIEW_ROWS = 5

EventKind = Literal["note", "level"]
Emit = Callable[[EventKind, object], None]


class Budget(BaseModel):
    """Caps on one run. When a cap is hit the levels already submitted stand."""

    max_tool_calls: int = 40
    min_levels: int = 2
    max_levels: int = 6


class ToolFailure(ValueError):
    """A tool call the agent should correct: the message goes back to it as the tool's error."""


def _json(value: object) -> str:
    return json.dumps(value, default=str, ensure_ascii=False)


def _dimensions(query: SlayerQuery) -> list[str]:
    return list(query.dimensions)


class LadderSession:
    def __init__(
        self,
        question: str,
        catalog: Catalog,
        runner: QueryRunner,
        context: str,
        budget: Budget | None = None,
        emit: Emit | None = None,
    ) -> None:
        self.question = question
        self.context = context
        self.budget = budget or Budget()
        self._catalog = catalog
        self._runner = runner
        self._emit = emit or (lambda kind, data: None)
        self.levels: list[Level] = []
        self.resolved: list[ResolvedLevel] = []
        self.steps: list[AgentStep] = []
        self.tool_calls = 0
        self.finished = False
        self.summary = ""
        self.usage: dict[str, int] = {}
        self._explored: set[str] = set()

    # Progress

    def fail(self, error: str) -> None:
        """Records why the last tool call failed, so the trace shows rejected levels and their errors."""
        tools = [step for step in self.steps if step.kind == StepKind.TOOL]
        if tools:
            tools[-1].error = error

    def note(self, text: str) -> None:
        self.steps.append(AgentStep(kind=StepKind.NOTE, text=text))
        self._emit("note", {"text": text})

    def _call(self, tool: str, label: str, payload: JsonValue = None) -> None:
        if self.finished:
            raise ToolFailure("The ladder is finished; no more tool calls.")
        if self.tool_calls >= self.budget.max_tool_calls:
            self.finished = True
            self.summary = (
                self.summary or "Stopped at the tool-call budget; the levels already submitted stand."
            )
            raise ToolFailure("Tool-call budget exhausted. The levels already submitted stand; stop now.")
        self.tool_calls += 1
        self.steps.append(AgentStep(kind=StepKind.TOOL, text=label, tool=tool, input=payload))
        self._emit("note", {"text": label})

    # Tools

    def list_models(self) -> str:
        self._call("list_models", "Reading the semantic layer")
        return _json([m.model_dump() for m in self._catalog.list_models()])

    def describe_model(self, name: str) -> str:
        self._call("describe_model", f"Reading the {name} model", {"name": name})
        try:
            return self._catalog.describe_model(name).model_dump_json(exclude_none=True)
        except KeyError as error:
            raise ToolFailure(str(error)) from error

    def profile_dimension(self, model: str, dimension: str) -> str:
        self._call(
            "profile_dimension", f"Profiling {dimension} in {model}", {"model": model, "dimension": dimension}
        )
        try:
            profile = self._catalog.profile_dimension(model, dimension)
        except Exception as error:
            raise ToolFailure(f"Cannot profile {dimension} in {model}: {error}") from error
        self._explored.add(dimension)
        return profile.model_dump_json(exclude_none=True)

    def read_context(self) -> str:
        self._call("read_context", "Reading the business context")
        return self.context

    def validate_query(self, query: SlayerQuery) -> str:
        self._call("validate_query", "Validating a query", query.model_dump(mode="json", exclude_none=True))
        errors = self._catalog.validate(query)
        return "valid" if not errors else _json({"errors": errors})

    def probe_query(self, query: SlayerQuery) -> str:
        """Runs a small query, at most PROBE_ROWS rows, to check that a step is viable."""
        capped = query.model_copy(update={"limit": min(query.limit or PROBE_ROWS, PROBE_ROWS)})
        self._call(
            "probe_query", "Checking a query on the data", capped.model_dump(mode="json", exclude_none=True)
        )
        if errors := self._catalog.validate(capped):
            raise ToolFailure(_json({"errors": errors}))
        try:
            data = self._runner.run(capped)
        except Exception as error:
            raise ToolFailure(f"The query failed: {error}") from error
        self._explored.update(_dimensions(capped))
        return _json({"columns": [c.key for c in data.columns], "rows": data.rows})

    def submit_level(self, title: str, panels: list[Panel], rationale: str) -> str:
        index = len(self.levels)
        self._call(
            "submit_level", f"Building level {index + 1}: {title}", {"title": title, "panels": len(panels)}
        )
        if index >= self.budget.max_levels:
            raise ToolFailure(f"The ladder already has {index} levels, the most allowed. Call finish.")
        try:
            level = Level(index=index, title=title, panels=panels, rationale=rationale)
        except ValidationError as error:
            raise ToolFailure(str(error)) from error
        problems = monotonic_violations(Ladder(question=self.question, levels=[*self.levels, level]))
        for panel in level.panels:
            problems += [f"panel {panel.id}: {e}" for e in self._catalog.validate(panel.query)]
        if problems:
            raise ToolFailure(_json({"errors": problems}))
        try:
            resolved = resolve_level(level, self._runner)
        except Exception as error:
            raise ToolFailure(f"A panel query failed when run: {error}") from error
        if empty := [p.id for p in resolved.panels if not p.data.rows]:
            raise ToolFailure(f"These panels returned no rows: {', '.join(empty)}. Fix or drop them.")
        self.levels.append(level)
        self.resolved.append(resolved)
        self.steps.append(AgentStep(kind=StepKind.LEVEL, text=title, level=index))
        self._emit("level", resolved)
        return _json(
            {"accepted": index, "preview": self._preview(resolved), "unexplored": self._unexplored(level)}
        )

    def finish(self, summary: str) -> str:
        if len(self.levels) < self.budget.min_levels:
            self._call("finish", "Finishing")
            raise ToolFailure(f"Submit at least {self.budget.min_levels} levels before finishing.")
        self._call("finish", "Finishing")
        self.finished = True
        self.summary = summary
        return "finished"

    # Results

    def ladder(self) -> Ladder | None:
        return Ladder(question=self.question, levels=self.levels) if self.levels else None

    def _unexplored(self, level: Level) -> list[str]:
        """Split dimensions no profile or probe looked at first. Reported, not blocked (see the arc42)."""
        return sorted({d for p in level.panels for d in _dimensions(p.query)} - self._explored)

    @staticmethod
    def _preview(level: ResolvedLevel) -> dict[str, object]:
        return {p.id: {"rows": len(p.data.rows), "first": p.data.rows[:PREVIEW_ROWS]} for p in level.panels}
