# Ladder agent

## Purpose and context

Builds the ladder for a question: Claude (`claude-opus-5-5`, adaptive thinking) in the Anthropic SDK Tool Runner,
with tools over the catalog, the business context and the executor. Each level the agent submits is validated,
run and streamed to the reader at once, and the run is kept as a trace of notes, tool calls and levels.

## Building blocks

See the `python` view in `views.c4`.

## Principles

1. Plans, never answers: the agent's only outputs are SLayer queries inside panels, with short titles and rationales. It has no SQL tool and no tool that puts a number in front of the reader. [enforced: test:tests/test_agent_loop.py]
2. A submitted level is shown only after it passes the monotonic rule, SLayer validation of every query, and a run that returns rows for every panel. [enforced: test:tests/test_agent_session.py]
3. Bounded run: one run makes at most a fixed number of tool calls and builds at most six levels; when a cap is hit, the levels already submitted stand. [enforced: test:tests/test_agent_session.py]
4. Explore before proposing: each split dimension is profiled or probed before the level that splits by it. `submit_level` reports dimensions nobody explored. [review]
5. The agent and, from #3, the narrator are the only elements that import the Anthropic SDK. [enforced: test:tests/test_import_law.py]

## Rationale

Every tool is a local call into the embedded SLayer, and the run is interactive, so the loop runs in-process with
the Tool Runner rather than as a Managed Agent. The system prompt (instructions, a worked ladder, the business
context and the model list) is stable per dataset and cached. Server-side refusal fallbacks are on. Progressive
submission lets the reader see level 1 while the agent still explores the next levels.
