"""The ladder: one question answered at increasing granularity, level by level."""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, JsonValue


class PanelKind(StrEnum):
    KPI = "kpi"
    BAR = "bar"
    TABLE = "table"
    LINE = "line"
    DELTA = "delta"


class SlayerQuery(BaseModel):
    """A SLayer query as data. Kept permissive: SLayer itself is the validator."""

    model_config = ConfigDict(extra="allow")

    source_model: str
    measures: list[str | dict[str, JsonValue]] = Field(min_length=1)
    dimensions: list[str] = Field(default_factory=list)
    time_dimensions: list[dict[str, JsonValue]] = Field(default_factory=list)
    filters: list[str] = Field(default_factory=list)
    limit: int | None = None


class Panel(BaseModel):
    id: str = Field(pattern=r"^[a-z0-9_]+$")
    kind: PanelKind
    title: str
    query: SlayerQuery
    parent: str | None = None
    """Id of the panel in the previous level that this panel refines, if any."""


class Level(BaseModel):
    index: int = Field(ge=0)
    title: str
    panels: list[Panel] = Field(min_length=1)
    rationale: str = ""


class Ladder(BaseModel):
    question: str
    levels: list[Level] = Field(min_length=1)


class ColumnRole(StrEnum):
    DIMENSION = "dimension"
    MEASURE = "measure"


class ValueFormat(StrEnum):
    NUMBER = "number"
    CURRENCY = "currency"
    PERCENT = "percent"


class Column(BaseModel):
    key: str
    label: str
    role: ColumnRole
    format: ValueFormat = ValueFormat.NUMBER


Cell = str | int | float | bool | None


class PanelData(BaseModel):
    """The rows SLayer returned for one panel's query, exactly as computed."""

    columns: list[Column]
    rows: list[dict[str, Cell]]


class ResolvedPanel(Panel):
    data: PanelData


class ResolvedLevel(BaseModel):
    index: int
    title: str
    rationale: str
    panels: list[ResolvedPanel]


class StepKind(StrEnum):
    NOTE = "note"
    TOOL = "tool"
    LEVEL = "level"


class AgentStep(BaseModel):
    """One step of an agent run, in order: a progress note, a tool call, or a level that landed."""

    kind: StepKind
    text: str = ""
    tool: str | None = None
    input: JsonValue = None
    level: int | None = None
    error: str | None = None
    """Why the tool call failed, as the agent was told."""
