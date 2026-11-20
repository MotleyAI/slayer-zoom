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

> Status: prototype, milestone M2 (the ladder agent). See the [plan](docs/plan.md).

## Run it

```bash
uv sync
uv run uvicorn --factory slayer_zoom.api:create_app --reload   # http://localhost:8000/health
```

```bash
cd web && npm install && npm run dev            # http://localhost:5173
```

Ask "What is our revenue year to date?" and move the slider. By default the API replays the recorded traces in
`src/slayer_zoom/traces/data/`, so it needs no database and no API key; `GET /questions` lists them.

To let the agent answer new questions, run against the live SLayer Jaffle Shop demo database (built in `.slayer/`
on first run) with an Anthropic API key:

```bash
SLAYER_ZOOM_LIVE=1 ANTHROPIC_API_KEY=... uv run uvicorn --factory slayer_zoom.api:create_app
```

The agent (`claude-opus-5-5` in the Anthropic SDK Tool Runner) reads the semantic layer and
`src/slayer_zoom/context/jaffle_shop.md`, profiles the dimensions it wants to split by, and submits levels one at a
time; each level is validated, run and streamed as soon as it is accepted, with the agent's progress notes. A recorded
question still replays for free. To record a new trace:

```bash
uv run python -m slayer_zoom.agent.record "How are our stores doing this year?"
```

`python -m slayer_zoom.api.record` re-records the hand-written M1 ladder.

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
