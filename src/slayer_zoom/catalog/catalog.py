"""What the semantic layer offers: models, measures, dimensions and joins, plus profiles of dimensions."""

import asyncio
import datetime as dt
import decimal
import sys
from collections.abc import Coroutine, Sequence
from pathlib import Path
from typing import Any, Protocol

from pydantic import BaseModel
from slayer.client.slayer_client import SlayerClient
from slayer.demo import ensure_demo_datasource
from slayer.storage.base import resolve_storage

from slayer_zoom.core import Cell, SlayerQuery

PROFILE_LIMIT = 50
"""Profiles group at most this many values; beyond it the distinct count is reported as capped."""


class ColumnInfo(BaseModel):
    name: str
    type: str | None = None
    label: str | None = None
    description: str | None = None


class MeasureInfo(BaseModel):
    name: str
    formula: str
    label: str | None = None
    description: str | None = None


class JoinInfo(BaseModel):
    target: str
    cardinality: str | None = None


class ModelSummary(BaseModel):
    name: str
    description: str
    measures: list[str]


class ModelInfo(BaseModel):
    name: str
    description: str
    default_time_dimension: str | None = None
    columns: list[ColumnInfo]
    measures: list[MeasureInfo]
    joins: list[JoinInfo]


class ValueShare(BaseModel):
    value: Cell
    rows: int
    share: float


class DimensionProfile(BaseModel):
    model: str
    dimension: str
    rows: int
    distinct: int
    distinct_capped: bool
    top: list[ValueShare]
    top_share: float
    null_share: float
    first: str | None = None
    last: str | None = None


class _Column(Protocol):
    @property
    def name(self) -> str: ...
    @property
    def type(self) -> Any: ...
    @property
    def label(self) -> str | None: ...
    @property
    def description(self) -> str | None: ...


class _Measure(Protocol):
    @property
    def name(self) -> str: ...
    @property
    def formula(self) -> str: ...
    @property
    def label(self) -> str | None: ...
    @property
    def description(self) -> str | None: ...


class _Join(Protocol):
    @property
    def target_model(self) -> str: ...
    @property
    def cardinality(self) -> Any: ...


class _Model(Protocol):
    @property
    def name(self) -> str: ...
    @property
    def description(self) -> str | None: ...
    @property
    def default_time_dimension(self) -> str | None: ...
    @property
    def columns(self) -> Sequence[_Column]: ...
    @property
    def measures(self) -> Sequence[_Measure]: ...
    @property
    def joins(self) -> Sequence[_Join]: ...


class StorageLike(Protocol):
    def list_models(self) -> Coroutine[Any, Any, list[str]]: ...
    def get_model(self, name: str) -> Coroutine[Any, Any, Any]: ...


class _Response(Protocol):
    @property
    def data(self) -> list[dict[str, Any]]: ...


class ClientLike(Protocol):
    def query_sync(self, query: Any, *, dry_run: bool = False) -> _Response: ...


def _text(value: object) -> str | None:
    return None if value is None else str(getattr(value, "value", value))


def _cell(value: object) -> Cell:
    if value is None or isinstance(value, str | int | float | bool):
        return value
    if isinstance(value, decimal.Decimal):
        return float(value)
    if isinstance(value, dt.datetime | dt.date):
        return value.isoformat()
    return str(value)


class Catalog:
    """The semantic layer as the agent sees it. Every read goes through SLayer; there is no SQL here."""

    def __init__(self, storage: StorageLike, client: ClientLike) -> None:
        self._storage = storage
        self._client = client

    def list_models(self) -> list[ModelSummary]:
        names = asyncio.run(self._storage.list_models())
        return [self._summary(self._model(name)) for name in sorted(names)]

    def describe_model(self, name: str) -> ModelInfo:
        model = self._model(name)
        return ModelInfo(
            name=model.name,
            description=model.description or "",
            default_time_dimension=model.default_time_dimension,
            columns=[
                ColumnInfo(name=c.name, type=_text(c.type), label=c.label, description=c.description)
                for c in model.columns
            ],
            measures=[
                MeasureInfo(name=m.name, formula=m.formula, label=m.label, description=m.description)
                for m in model.measures
            ],
            joins=[JoinInfo(target=j.target_model, cardinality=_text(j.cardinality)) for j in model.joins],
        )

    def profile_dimension(self, model: str, dimension: str) -> DimensionProfile:
        """Row count per value (top values first), share of the top value, nulls, and the range of dates."""
        query = {
            "source_model": model,
            "measures": ["*:count"],
            "dimensions": [dimension],
            "order": [{"column": "*:count", "direction": "desc"}],
            "limit": PROFILE_LIMIT + 1,
        }
        rows = self._client.query_sync(query).data
        counts = [(_cell(next(iter(r.values()))), int(list(r.values())[-1] or 0)) for r in rows]
        total = self._row_count(model)
        shares = [ValueShare(value=v, rows=n, share=n / total if total else 0.0) for v, n in counts]
        nulls = sum(n for v, n in counts if v is None)
        first, last = self._date_range(model, dimension)
        return DimensionProfile(
            model=model,
            dimension=dimension,
            rows=total,
            distinct=min(len(counts), PROFILE_LIMIT),
            distinct_capped=len(counts) > PROFILE_LIMIT,
            top=shares[:10],
            top_share=shares[0].share if shares else 0.0,
            null_share=nulls / total if total else 0.0,
            first=first,
            last=last,
        )

    def validate(self, query: SlayerQuery) -> list[str]:
        """SLayer's own validation, without running the query. An empty list means the query is valid."""
        try:
            self._client.query_sync(query.model_dump(mode="json", exclude_none=True), dry_run=True)
        except Exception as error:  # SLayer raises many error types; each message is a validation error
            return [str(error).strip()]
        return []

    def _model(self, name: str) -> _Model:
        model = asyncio.run(self._storage.get_model(name))
        if model is None:
            raise KeyError(f"unknown model {name!r}")
        return model

    @staticmethod
    def _summary(model: _Model) -> ModelSummary:
        return ModelSummary(
            name=model.name,
            description=model.description or "",
            measures=[m.name for m in model.measures],
        )

    def _row_count(self, model: str) -> int:
        rows = self._client.query_sync({"source_model": model, "measures": ["*:count"]}).data
        return int(next(iter(rows[0].values())) or 0) if rows else 0

    def _date_range(self, model: str, dimension: str) -> tuple[str | None, str | None]:
        query = {"source_model": model, "measures": [f"{dimension}:min", f"{dimension}:max"]}
        try:
            rows = self._client.query_sync(query).data
        except Exception:  # min/max is defined for some types only; then there is no range
            return None, None
        values = list(rows[0].values()) if rows else []
        if len(values) != 2 or not all(isinstance(v, dt.date) for v in values):
            return None, None
        return _text(_cell(values[0])), _text(_cell(values[1]))


def demo_catalog(storage_path: str | Path = ".slayer") -> Catalog:
    """A catalog of the SLayer Jaffle Shop demo, building the demo database on first use."""
    path = str(storage_path)
    storage = resolve_storage(path)
    ensure_demo_datasource(storage, storage_path=path, stream=sys.stderr)
    return Catalog(storage, SlayerClient(storage=storage))
