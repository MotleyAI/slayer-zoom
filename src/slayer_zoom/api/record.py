"""Record the hand-written ladder against the live demo database: `python -m slayer_zoom.api.record`."""

from slayer_zoom.core import query_hash
from slayer_zoom.executor import demo_executor
from slayer_zoom.traces import LADDER, Trace, save_trace

DEMO_TRACE = "revenue_ytd"


def main() -> None:
    executor = demo_executor()
    queries = {query_hash(p.query): p.query for level in LADDER.levels for p in level.panels}
    results = {key: executor.run(query) for key, query in queries.items()}
    print(save_trace(DEMO_TRACE, Trace(ladder=LADDER, results=results)))


if __name__ == "__main__":
    main()
