import math

import pytest

from slayer_zoom.catalog import Catalog
from slayer_zoom.core import SlayerQuery


def test_lists_models_with_their_measures(catalog: Catalog) -> None:
    models = {m.name: m for m in catalog.list_models()}
    assert {"orders", "items", "stores", "products"} <= set(models)
    assert "total_revenue" in models["orders"].measures


def test_describes_columns_measures_and_joins(catalog: Catalog) -> None:
    orders = catalog.describe_model("orders")
    columns = {c.name: c for c in orders.columns}
    assert columns["ordered_at"].type == "DATE"
    assert {j.target for j in orders.joins} >= {"stores", "customers"}
    assert orders.default_time_dimension == "ordered_at"


def test_unknown_model_is_a_key_error(catalog: Catalog) -> None:
    with pytest.raises(KeyError):
        catalog.describe_model("nope")


def test_profiles_a_joined_dimension(catalog: Catalog) -> None:
    profile = catalog.profile_dimension("orders", "stores.name")
    assert profile.distinct == 4
    assert not profile.distinct_capped
    assert profile.top[0].value == "Brooklyn"
    assert math.isclose(sum(v.share for v in profile.top), 1.0)
    assert profile.null_share == 0
    assert profile.first is None


def test_profiles_the_date_range_of_a_time_dimension(catalog: Catalog) -> None:
    profile = catalog.profile_dimension("orders", "ordered_at")
    assert profile.distinct_capped
    assert profile.first is not None
    assert profile.last is not None
    assert profile.first < profile.last


def test_validates_without_running(catalog: Catalog) -> None:
    assert catalog.validate(SlayerQuery(source_model="orders", measures=["total_revenue"])) == []
    errors = catalog.validate(SlayerQuery(source_model="orders", measures=["nope"]))
    assert len(errors) == 1
    assert "nope" in errors[0]
