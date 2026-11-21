"""Writes the answer's text, level by level, as insertions into the text so far. Every figure is checked."""

import json
import re
from typing import Any, Protocol

import anthropic
from pydantic import BaseModel, Field

from slayer_zoom.core import (
    Insertion,
    ResolvedLevel,
    ResolvedPanel,
    Segment,
    insert_segments,
    ungrounded_numbers,
)
from slayer_zoom.narrator.prompts import INSTRUCTIONS

MODEL = "claude-sonnet-5-5"
MAX_TOKENS = 4000
EFFORT = "low"
ROWS_SHOWN = 30
_ID = re.compile(r"[a-z0-9_]+")


class DraftInsertion(BaseModel):
    id: str
    text: str
    after: str | None = None
    panel: str | None = None


class Draft(BaseModel):
    insertions: list[DraftInsertion] = Field(default_factory=list)


class _Response(Protocol):
    @property
    def parsed_output(self) -> Draft | None: ...
    @property
    def stop_reason(self) -> str | None: ...


class _Messages(Protocol):
    def parse(self, **params: Any) -> _Response: ...


class ClientLike(Protocol):
    @property
    def messages(self) -> _Messages: ...


def _panel_brief(panel: ResolvedPanel) -> dict[str, object]:
    return {
        "id": panel.id,
        "kind": panel.kind.value,
        "title": panel.title,
        "columns": [{"key": c.key, "label": c.label, "format": c.format.value} for c in panel.data.columns],
        "rows": panel.data.rows[:ROWS_SHOWN],
    }


def _fallback(panel: ResolvedPanel, level: int, used: set[str]) -> Segment:
    sid = f"{panel.id}_intro"
    while sid in used:
        sid += "_x"
    return Segment(id=sid, level=level, text=f"{panel.title.rstrip('.')}.", panel=panel.id)


def live_narrator(question: str) -> "Narrator":
    """A narrator on the Anthropic API; needs ANTHROPIC_API_KEY."""
    return Narrator(question, anthropic.Anthropic())


class Narrator:
    """One narrator per answer: it keeps the text so far and extends it as each level lands."""

    def __init__(self, question: str, client: ClientLike | anthropic.Anthropic) -> None:
        self.question = question
        self.segments: list[Segment] = []
        self._client = client

    def narrate(self, level: ResolvedLevel) -> list[Segment]:
        """Extends the text with this level's insertions and returns the whole text."""
        introduced = {s.panel for s in self.segments if s.panel}
        new_panels = [p for p in level.panels if p.id not in introduced]
        rows = [row for panel in level.panels for row in panel.data.rows]
        insertions = self._draft(level, new_panels, rows)
        self.segments = self._apply(level.index, insertions, new_panels)
        return self.segments

    def _draft(
        self, level: ResolvedLevel, new_panels: list[ResolvedPanel], rows: list[dict]
    ) -> list[Insertion]:
        feedback = ""
        insertions: list[Insertion] = []
        for _ in range(2):
            insertions = self._ask(level, new_panels, feedback)
            problems = self._problems(insertions, new_panels, rows)
            if not problems:
                return insertions
            feedback = "Your previous answer had these problems; fix them:\n- " + "\n- ".join(problems)
        new_ids = {p.id for p in new_panels}
        return [
            i
            for i in insertions
            if not ungrounded_numbers(i.segment.text, rows) and i.segment.panel in new_ids | {None}
        ]

    def _ask(self, level: ResolvedLevel, new_panels: list[ResolvedPanel], feedback: str) -> list[Insertion]:
        brief = {
            "question": self.question,
            "level": level.index + 1,
            "level_title": level.title,
            "level_rationale": level.rationale,
            "text_so_far": [{"id": s.id, "text": s.text, "panel": s.panel} for s in self.segments],
            "new_panels": [_panel_brief(p) for p in new_panels],
            "earlier_panels": [_panel_brief(p) for p in level.panels if p not in new_panels],
        }
        response = self._client.messages.parse(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=INSTRUCTIONS,
            messages=[
                {
                    "role": "user",
                    "content": json.dumps(brief, default=str) + ("\n\n" + feedback if feedback else ""),
                }
            ],
            output_config={"effort": EFFORT},
            output_format=Draft,
        )
        draft = response.parsed_output if response.stop_reason != "refusal" else None
        used = {s.id for s in self.segments}
        insertions: list[Insertion] = []
        for item in draft.insertions if draft else []:
            sid = item.id if _ID.fullmatch(item.id) and item.id not in used else f"l{level.index}_{len(used)}"
            used.add(sid)
            segment = Segment(id=sid, level=level.index, text=item.text.strip(), panel=item.panel)
            insertions.append(Insertion(segment=segment, after=item.after))
        return insertions

    def _problems(
        self, insertions: list[Insertion], new_panels: list[ResolvedPanel], rows: list[dict]
    ) -> list[str]:
        problems: list[str] = []
        known = {s.id for s in self.segments} | {i.segment.id for i in insertions}
        new_ids = {p.id for p in new_panels}
        introduced = [i.segment.panel for i in insertions if i.segment.panel]
        for insertion in insertions:
            segment = insertion.segment
            if bad := ungrounded_numbers(segment.text, rows):
                problems.append(f"{segment.id}: figures not in the rows: {', '.join(bad)}")
            if insertion.after is not None and insertion.after not in known:
                problems.append(f"{segment.id}: follows unknown segment {insertion.after}")
            if segment.panel and segment.panel not in new_ids:
                problems.append(f"{segment.id}: panel {segment.panel} is not a new panel of this level")
        for panel_id in sorted(new_ids):
            if introduced.count(panel_id) != 1:
                problems.append(f"panel {panel_id} must be introduced exactly once")
        if not insertions:
            problems.append("no insertions")
        return problems

    def _apply(
        self, level: int, insertions: list[Insertion], new_panels: list[ResolvedPanel]
    ) -> list[Segment]:
        known = {s.id for s in self.segments}
        placed: list[Insertion] = []
        seen_panels: set[str] = set()
        for insertion in insertions:
            panel = insertion.segment.panel
            if panel in seen_panels:
                insertion = Insertion(
                    segment=insertion.segment.model_copy(update={"panel": None}), after=insertion.after
                )
            if insertion.after is not None and insertion.after not in known:
                insertion = Insertion(
                    segment=insertion.segment, after=None if not known else self.segments[-1].id
                )
            known.add(insertion.segment.id)
            seen_panels.add(insertion.segment.panel or "")
            placed.append(insertion)
        segments = insert_segments(self.segments, placed)
        used = {s.id for s in segments}
        for panel in new_panels:
            if panel.id not in seen_panels:
                fallback = _fallback(panel, level, used)
                used.add(fallback.id)
                segments.append(fallback)
        return segments
