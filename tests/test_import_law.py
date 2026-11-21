"""Only the elements that own an integration import its client (system principle 5)."""

import ast
from pathlib import Path

import pytest

PACKAGE = Path(__file__).parents[1] / "src" / "slayer_zoom"
OWNERS = {"slayer": {"catalog", "executor"}, "anthropic": {"agent", "narrator"}}


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text())
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names |= {alias.name.split(".")[0] for alias in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            names.add(node.module.split(".")[0])
    return names


@pytest.mark.parametrize("client", sorted(OWNERS))
def test_only_owners_import_the_client(client: str) -> None:
    importers = {
        path.relative_to(PACKAGE).parts[0] for path in PACKAGE.rglob("*.py") if client in _imports(path)
    }
    assert importers
    assert importers <= OWNERS[client]
