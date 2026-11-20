import datetime as dt
import decimal
from collections.abc import Mapping
from types import SimpleNamespace
from typing import Any

from slayer_zoom.core import ColumnRole, SlayerQuery, ValueFormat
from slayer_zoom.executor import SlayerExecutor

QUERY = SlayerQuery.model_validate(
    {
        "source_model": "orders",
        "measures": [
            {"formula": "total_revenue", "name": "revenue", "label": "Revenue"},
            {
                "formula": "change_pct(total_revenue)",
                "name": "mom",
                "label": "MoM",
                "format": {"type": "percent"},
            },
        ],
        "dimensions": ["stores.name"],
    }
)


class FakeSlayer:
    def __init__(self) -> None:
        self.calls: list[Mapping[str, Any]] = []

    def query_sync(self, query: Mapping[str, Any]) -> Any:
        self.calls.append(query)
        meta = SimpleNamespace
        return SimpleNamespace(
            columns=["orders.stores.name", "orders.revenue", "orders.mom"],
            data=[
                {
                    "orders.stores.name": "Brooklyn",
                    "orders.revenue": decimal.Decimal("10.50"),
                    "orders.mom": 0.1,
                },
                {"orders.stores.name": dt.date(2026, 1, 1), "orders.revenue": 4.5, "orders.mom": None},
            ],
            attributes=SimpleNamespace(
                dimensions={"orders.stores.name": meta(label="Store", format=None)},
                measures={
                    "orders.revenue": meta(label="Revenue", format=meta(type="currency")),
                    "orders.mom": meta(label="MoM", format=meta(type="float")),
                },
            ),
        )


def test_columns_carry_roles_labels_and_formats() -> None:
    data = SlayerExecutor(FakeSlayer()).run(QUERY)
    assert [(c.label, c.role, c.format) for c in data.columns] == [
        ("Store", ColumnRole.DIMENSION, ValueFormat.NUMBER),
        ("Revenue", ColumnRole.MEASURE, ValueFormat.CURRENCY),
        ("MoM", ColumnRole.MEASURE, ValueFormat.PERCENT),
    ]


def test_cells_become_json_values() -> None:
    rows = SlayerExecutor(FakeSlayer()).run(QUERY).rows
    assert rows[0]["orders.revenue"] == 10.5
    assert rows[1]["orders.stores.name"] == "2026-01-01"
    assert rows[1]["orders.mom"] is None


def test_each_query_runs_once() -> None:
    client = FakeSlayer()
    executor = SlayerExecutor(client)
    executor.run(QUERY)
    executor.run(SlayerQuery.model_validate(QUERY.model_dump()))
    assert len(client.calls) == 1
