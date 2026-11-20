## Why

M1 proved the slider on a hand-written ladder. The product needs the ladder built for any question: an agent that
explores the semantic layer and the business context and decides which steps are worth showing on this data.

## What Changes

- `catalog` (new): models, measures, dimensions and joins read through SLayer, `profile_dimension` (rows per value,
  top share, nulls, date range) and validation without execution. The demo database builds on first use.
- `context` (new): the Jaffle Shop business context: glossary, calendar, audience and caveats.
- `agent` (new): the ladder agent on the Anthropic SDK Tool Runner (`claude-opus-5-5`, adaptive thinking, effort
  medium, server-side refusal fallbacks, a cached system prompt, a bounded run). Tools: `list_models`,
  `describe_model`, `profile_dimension`, `read_context`, `validate_query`, `probe_query`, `submit_level`, `finish`.
  `submit_level` validates a level (monotonic rule, SLayer validation, rows for every panel) and runs it at once.
  `python -m slayer_zoom.agent.record "<question>"` records a run as a trace.
- `core`: `AgentStep` (note, tool call or level) for traces.
- `traces`: traces carry the agent's steps and summary; a recording runner keeps every result; stored traces are
  found by question, agent-built ones first.
- `api`: `POST /answer` replays a stored trace with its notes in order, or, with `SLAYER_ZOOM_LIVE` and an API key,
  runs the agent and streams `note` and `level` events as they happen. `GET /questions` lists recorded questions.
- web `state` and `slider`: progress notes, a level count that stays open while the agent decides, the summary.

## Impact

- Architecture: three new elements (`catalog`, `context`, `agent`) and their arrows; arc42 files for each; system
  principles 1 (numbers only from SLayer) and 5 (only owners import SLayer and Anthropic) are now enforced by tests.
- Dependencies: `anthropic` (Python). CI still needs no API key: it runs on recorded traces and a scripted runner.
