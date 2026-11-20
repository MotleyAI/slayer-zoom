"""The two ladder invariants: monotonic disclosure and reconciliation."""

import math
from collections.abc import Iterable

from slayer_zoom.core.models import Ladder, Level


def monotonic_violations(ladder: Ladder) -> list[str]:
    """Each level keeps every panel of the one before, query unchanged, or refines it with a child panel."""
    problems: list[str] = []
    for position, level in enumerate(ladder.levels):
        if level.index != position:
            problems.append(f"level at position {position} has index {level.index}")
        problems.extend(_duplicate_ids(level))
    for previous, current in zip(ladder.levels, ladder.levels[1:], strict=False):
        problems.extend(_next_level_violations(previous, current))
    return problems


def reconciles(parent_value: float, child_values: Iterable[float], *, abs_tol: float = 0.01) -> bool:
    """The children of a split sum to the parent value, within rounding."""
    return math.isclose(parent_value, math.fsum(child_values), rel_tol=1e-9, abs_tol=abs_tol)


def _duplicate_ids(level: Level) -> list[str]:
    ids = [panel.id for panel in level.panels]
    return [f"level {level.index} repeats panel id {pid}" for pid in sorted(set(ids)) if ids.count(pid) > 1]


def _next_level_violations(previous: Level, current: Level) -> list[str]:
    problems: list[str] = []
    current_ids = {panel.id for panel in current.panels}
    refined = {panel.parent for panel in current.panels if panel.parent is not None}
    previous_ids = {panel.id for panel in previous.panels}
    current_queries = {panel.id: panel.query for panel in current.panels}
    for panel in previous.panels:
        if panel.id in current_queries and current_queries[panel.id] != panel.query:
            problems.append(f"level {current.index} changes the query of kept panel {panel.id}")
        if panel.id not in current_ids and panel.id not in refined:
            problems.append(f"level {current.index} drops panel {panel.id} without refining it")
    for panel in current.panels:
        if panel.parent is not None and panel.parent not in previous_ids:
            problems.append(f"panel {panel.id} in level {current.index} refines unknown panel {panel.parent}")
    return problems
