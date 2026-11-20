"""Runs panel queries through SLayer and caches each result by query hash."""

import datetime as dt
import decimal
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Protocol

from slayer.client.slayer_client import SlayerClient
from slayer.demo import ensure_demo_datasource
from slayer.storage.base import resolve_storage

from slayer_zoom.core import Cell, Column, ColumnRole, PanelData, SlayerQuery, ValueFormat, query_hash


class _FieldMeta(Protocol):
    @property
    def label(self) -> str | None: ...
    @property
    def format(self) -> Any: ...


class _Attributes(Protocol):
    @property
    def dimensions(self) -> Mapping[str, _FieldMeta]: ...
    @property
    def measures(self) -> Mapping[str, _FieldMeta]: ...


class _Response(Protocol):
    @property
    def data(self) -> list[dict[str, Any]]: ...
    @property
    def columns(self) -> list[str]: ...
    @property
    def attributes(self) -> _Attributes: ...


class SlayerLike(Protocol):
    def query_sync(self, query: Any) -> _Response: ...


def _cell(value: object) -> Cell:
    if value is None or isinstance(value, str | int | float | bool):
        return value
    if isinstance(value, decimal.Decimal):
        return float(value)
    if isinstance(value, dt.datetime | dt.date):
        return value.isoformat()
    return str(value)


def _format_of(kind: object) -> ValueFormat | None:
    text = str(kind or "").lower()
    if "currency" in text:
        return ValueFormat.CURRENCY
    if "percent" in text:
        return ValueFormat.PERCENT
    return None


def _declared_formats(query: SlayerQuery) -> dict[str, ValueFormat]:
    """Formats the query itself declares on named measures. SLayer drops them on computed measures."""
    declared: dict[str, ValueFormat] = {}
    for measure in query.measures:
        if isinstance(measure, dict) and isinstance(fmt := measure.get("format"), dict):
            if (found := _format_of(fmt.get("type"))) is not None:
                declared[str(measure.get("name"))] = found
    return declared


def _format(key: str, meta: _FieldMeta | None, declared: dict[str, ValueFormat]) -> ValueFormat:
    found = _format_of(getattr(getattr(meta, "format", None), "type", None))
    return found or declared.get(key.rsplit(".", 1)[-1], ValueFormat.NUMBER)


def _label(key: str, meta: _FieldMeta | None) -> str:
    return (meta.label if meta and meta.label else key.rsplit(".", 1)[-1]).strip()


class SlayerExecutor:
    """A query runner over a SLayer client. Each distinct query runs at most once."""

    def __init__(self, client: SlayerLike) -> None:
        self._client = client
        self._cache: dict[str, PanelData] = {}

    def run(self, query: SlayerQuery) -> PanelData:
        key = query_hash(query)
        if key not in self._cache:
            self._cache[key] = self._execute(query)
        return self._cache[key]

    def _execute(self, query: SlayerQuery) -> PanelData:
        response = self._client.query_sync(query.model_dump(mode="json", exclude_none=True))
        dims, measures = response.attributes.dimensions, response.attributes.measures
        declared = _declared_formats(query)
        columns = [
            Column(
                key=k,
                label=_label(k, measures[k]),
                role=ColumnRole.MEASURE,
                format=_format(k, measures[k], declared),
            )
            if k in measures
            else Column(key=k, label=_label(k, dims.get(k)), role=ColumnRole.DIMENSION)
            for k in response.columns
        ]
        rows = [{k: _cell(v) for k, v in row.items()} for row in response.data]
        return PanelData(columns=columns, rows=rows)


def demo_executor(storage_path: str | Path = ".slayer") -> SlayerExecutor:
    """An executor on the SLayer Jaffle Shop demo, building the demo database on first use."""
    path = str(storage_path)
    storage = resolve_storage(path)
    ensure_demo_datasource(storage, storage_path=path, stream=sys.stderr)
    return SlayerExecutor(SlayerClient(storage=storage))
