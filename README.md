# slayer-zoom

**One question, answered at the granularity you choose.**

Ask a data question once. The answer comes with a slider. All the way left, it is one number. Each step to the right
adds detail: the split by store, then by product, then by segment, then trends, comparisons and drivers. The answer is
the same at every step, only finer.

An agent builds the ladder. It explores the semantic layer and the business context, and decides which steps are worth
showing for this question on this data. [SLayer](https://github.com/MotleyAI/slayer) makes each step cheap: every step
is a small variation on the same query (another dimension, a `time_shift`, a `change_pct`, a `rank`), so the system
writes no new SQL for any step, and every number reconciles with the step before it.

| Level | "What is our revenue year to date?" |
|---|---|
| 0 Number | Revenue YTD |
| 1 Split | + by store |
| 2 Mix | + store × product type, top products |
| 3 Segments | + new vs returning customers, monthly trend |
| 4 Analysis | + year over year, month over month, share of total, biggest movers |

> Status: prototype, milestone M1 (walking skeleton with a hand-written ladder). See the [plan](docs/plan.md).

## Run it

```bash
uv sync
uv run uvicorn --factory slayer_zoom.api:create_app --reload   # http://localhost:8000/health
```

```bash
cd web && npm install && npm run dev            # http://localhost:5173
```

Ask "What is our revenue year to date?" and move the slider. By default the API replays the recorded trace in
`src/slayer_zoom/traces/data/`, so it needs no database and no API key. To answer from the live SLayer Jaffle Shop
demo database instead (built in `.slayer/` on first run), set `SLAYER_ZOOM_LIVE=1`. To re-record the trace after
changing the ladder:

```bash
uv run python -m slayer_zoom.api.record
```

## Checks

```bash
uv run pytest -q
npm test --prefix web
uv run ruff check src tests
la-typecheck
la-arch-check
```

## Architecture

The repo uses [living-architecture](https://github.com/MotleyAI/living-architecture): a LikeC4 model in
[`architecture/`](architecture/) that is also the import law (`la-arch-check`), with normative principles in
arc42 files next to it. Changes go through `/la:pr`, which writes an OpenSpec change for each PR.

## License

MIT
