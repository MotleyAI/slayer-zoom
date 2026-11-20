"""The business context the agent reads: glossary, calendar, audience and caveats, one file per dataset."""

from pathlib import Path

CONTEXT_DIR = Path(__file__).parent


def load_context(dataset: str = "jaffle_shop") -> str:
    path = CONTEXT_DIR / f"{dataset}.md"
    if not path.is_file():
        raise FileNotFoundError(f"no business context for dataset {dataset!r}")
    return path.read_text()


__all__ = ["CONTEXT_DIR", "load_context"]
