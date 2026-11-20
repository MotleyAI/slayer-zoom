## Why

The slider is the product. Before an agent builds ladders (#2), the UX has to be proven on real SLayer results: one
question, five levels, each level the same answer at a finer grain, and a slider that moves between them instantly.

## What Changes

- `core`: resolved panel and level types (columns with role, label and format; rows), `query_hash`, `resolve_level`
  and the `QueryRunner` protocol.
- `executor` (new): runs panel queries through the embedded SLayer client on the Jaffle Shop demo, caches results by
  query hash, converts decimals and dates to JSON values, applies the format a query declares when SLayer drops it.
- `traces` (new): the hand-written 5-level ladder for "What is our revenue year to date?", the trace format (ladder
  plus recorded results) and a replay runner that never guesses an unrecorded query.
- `api`: `POST /answer` streams `ladder`, one `level` per level and `done` as server-sent events; the app is now built
  by `create_app()`; `python -m slayer_zoom.api.record` re-records the demo trace.
- web `state` (new): store with `ask` (the only server call) and `slide`, SSE parsing, React hook.
- web `panels` (new): KPI, bar, table, line and delta renderers.
- web `slider` (new): the control and the current level's panels, with panels new at the level marked.
- vitest for the web state; CI runs it.

## Impact

- Architecture: five new elements and their arrows in `architecture/model.c4`; arc42 files for each; the system
  principles "slide never calls the LLM or DB" and "replayable without an API key" are now enforced by tests.
- Dependencies: `motley-slayer` (Python), `vitest` (web, dev).
