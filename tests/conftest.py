from pathlib import Path

import pytest

from slayer_zoom.catalog import Catalog, demo_catalog
from slayer_zoom.executor import SlayerExecutor, demo_executor


@pytest.fixture(scope="session")
def demo_storage(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """The SLayer Jaffle Shop demo, built once per test session in a temporary folder."""
    return tmp_path_factory.mktemp("demo") / ".slayer"


@pytest.fixture(scope="session")
def catalog(demo_storage: Path) -> Catalog:
    return demo_catalog(demo_storage)


@pytest.fixture(scope="session")
def executor(demo_storage: Path, catalog: Catalog) -> SlayerExecutor:
    return demo_executor(demo_storage)
