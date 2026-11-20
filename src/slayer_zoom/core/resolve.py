"""Turning a ladder level into a resolved level, through any query runner."""

import hashlib
import json
from typing import Protocol

from slayer_zoom.core.models import Level, PanelData, ResolvedLevel, ResolvedPanel, SlayerQuery


class QueryRunner(Protocol):
    def run(self, query: SlayerQuery) -> PanelData: ...


def query_hash(query: SlayerQuery) -> str:
    """A stable key for a query: the same query always gets the same hash."""
    canonical = json.dumps(
        query.model_dump(mode="json", exclude_none=True), sort_keys=True, separators=(",", ":")
    )
    return hashlib.sha256(canonical.encode()).hexdigest()[:16]


def resolve_level(level: Level, runner: QueryRunner) -> ResolvedLevel:
    panels = [ResolvedPanel(**panel.model_dump(), data=runner.run(panel.query)) for panel in level.panels]
    return ResolvedLevel(index=level.index, title=level.title, rationale=level.rationale, panels=panels)
