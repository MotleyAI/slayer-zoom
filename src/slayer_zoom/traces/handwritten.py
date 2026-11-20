"""The hand-written ladder for the M1 walking skeleton. The agent (#2) replaces it."""

from pydantic import JsonValue

from slayer_zoom.core import Ladder, Level, Panel, PanelKind, SlayerQuery

QUESTION = "What is our revenue year to date?"

_YTD: dict[str, JsonValue] = {"dimension": "ordered_at", "granularity": "year", "date_range": "this year"}
_YTD_ITEMS: dict[str, JsonValue] = {
    "dimension": "orders.ordered_at",
    "granularity": "year",
    "date_range": "this year",
}
_MONTHS_YTD: dict[str, JsonValue] = {
    "dimension": "ordered_at",
    "granularity": "month",
    "date_range": "this year",
}
_COMPLETE_MONTHS: dict[str, JsonValue] = {
    "dimension": "ordered_at",
    "granularity": "month",
    "date_range": ["this year", "last month"],
}

_CURRENCY: dict[str, JsonValue] = {"type": "currency", "symbol": "$", "precision": 0}
_CENTS: dict[str, JsonValue] = {"type": "currency", "symbol": "$", "precision": 2}
_PERCENT: dict[str, JsonValue] = {"type": "percent", "precision": 1}


def _m(formula: str, name: str, label: str, fmt: dict[str, JsonValue] | None = None) -> dict[str, JsonValue]:
    measure: dict[str, JsonValue] = {"formula": formula, "name": name, "label": label}
    if fmt is not None:
        measure["format"] = fmt
    return measure


REVENUE = _m("total_revenue", "revenue", "Revenue", _CURRENCY)
UNITS = _m("units_sold", "units", "Units sold")

TOTAL = Panel(
    id="total",
    kind=PanelKind.KPI,
    title="Revenue year to date",
    query=SlayerQuery(source_model="orders", measures=[REVENUE], time_dimensions=[_YTD]),
)
BY_STORE = Panel(
    id="by_store",
    kind=PanelKind.BAR,
    title="By store",
    parent="total",
    query=SlayerQuery(
        source_model="orders", measures=[REVENUE], dimensions=["stores.name"], time_dimensions=[_YTD]
    ),
)
STORE_MIX = Panel(
    id="store_mix",
    kind=PanelKind.TABLE,
    title="Units sold by store and product type",
    parent="by_store",
    query=SlayerQuery(
        source_model="items",
        measures=[UNITS],
        dimensions=["orders.stores.name", "products.type"],
        time_dimensions=[_YTD_ITEMS],
    ),
)
TOP_PRODUCTS = Panel(
    id="top_products",
    kind=PanelKind.BAR,
    title="Top products by units sold",
    query=SlayerQuery.model_validate(
        {
            "source_model": "items",
            "measures": [UNITS],
            "dimensions": ["products.name"],
            "time_dimensions": [_YTD_ITEMS],
            "order": [{"column": "units", "direction": "desc"}],
            "limit": 5,
        }
    ),
)
MONTHLY = Panel(
    id="monthly",
    kind=PanelKind.LINE,
    title="Month by month",
    parent="total",
    query=SlayerQuery(
        source_model="orders",
        measures=[REVENUE, _m("cumsum(total_revenue)", "running_total", "Running total", _CURRENCY)],
        time_dimensions=[_MONTHS_YTD],
    ),
)
STORE_DRIVERS = Panel(
    id="store_drivers",
    kind=PanelKind.TABLE,
    title="Share, orders, customers and order value by store",
    parent="by_store",
    query=SlayerQuery(
        source_model="orders",
        measures=[
            REVENUE,
            _m("total_revenue / sum(order_total, partition_by=[])", "share", "Share of revenue", _PERCENT),
            _m("order_count", "orders", "Orders"),
            _m("unique_customers", "customers", "Customers"),
            _m(
                "avg_order_value", "aov", "Average order", {"type": "currency", "symbol": "$", "precision": 2}
            ),
        ],
        dimensions=["stores.name"],
        time_dimensions=[_YTD],
    ),
)
MONTHLY_CHANGE = Panel(
    id="monthly_change",
    kind=PanelKind.DELTA,
    title="Complete months against last year and the month before",
    parent="monthly",
    query=SlayerQuery(
        source_model="orders",
        measures=[
            REVENUE,
            _m("time_shift(total_revenue, -1, 'year')", "last_year", "Same month last year", _CURRENCY),
            _m("total_revenue / time_shift(total_revenue, -1, 'year') - 1", "yoy", "vs last year", _PERCENT),
            _m("change_pct(total_revenue)", "mom", "vs previous month", _PERCENT),
        ],
        time_dimensions=[_COMPLETE_MONTHS],
    ),
)

LADDER = Ladder(
    question=QUESTION,
    levels=[
        Level(index=0, title="Number", panels=[TOTAL], rationale="The answer in one number."),
        Level(index=1, title="Split", panels=[TOTAL, BY_STORE], rationale="Where the revenue comes from."),
        Level(
            index=2,
            title="Mix",
            panels=[TOTAL, BY_STORE, STORE_MIX, TOP_PRODUCTS],
            rationale=(
                "What each store sells. The demo model has no revenue per product line, so this uses units."
            ),
        ),
        Level(
            index=3,
            title="Trend and drivers",
            panels=[TOTAL, BY_STORE, STORE_MIX, TOP_PRODUCTS, MONTHLY, STORE_DRIVERS],
            rationale="How the year built up, and what drives each store's revenue.",
        ),
        Level(
            index=4,
            title="Analysis",
            panels=[TOTAL, BY_STORE, STORE_MIX, TOP_PRODUCTS, MONTHLY, STORE_DRIVERS, MONTHLY_CHANGE],
            rationale="How each complete month compares with last year and with the month before.",
        ),
    ],
)
