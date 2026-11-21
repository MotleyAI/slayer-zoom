# Ladder store

## Purpose and context

Persists ladders together with the query results they were answered with, and replays them. A trace also stores
the narration and the per-level digests (question, headline, summary). Holds the
hand-written ladder for "What is our revenue year to date?" until the agent (#2) writes ladders.

## Building blocks

See the `python` view in `views.c4`.

## Principles

1. A trace holds its ladder and every query result it was answered with, so it replays without SLayer, a database or an API key. [enforced: test:tests/test_traces.py]
2. Replay answers only recorded queries: an unrecorded query is an error, never a guess. [enforced: test:tests/test_traces.py]
3. The ladder store depends only on the ladder domain. [enforced: arch_check:model-truth]

## Rationale

Recorded traces make the demo, the tests and CI independent of the database and of the Anthropic API, and later let
agent runs be compared and replayed. `python -m slayer_zoom.api.record` re-records the demo trace.
