## ADDED Requirements

### Requirement: Agent-built ladder
For a question with no stored trace, the system SHALL build a ladder with the ladder agent when it runs live with an
API key, and SHALL stream each accepted level to the reader as soon as it has run.

#### Scenario: Live question
- **WHEN** a client posts a new question to `/answer` with `SLAYER_ZOOM_LIVE` and an API key set
- **THEN** it receives `ladder` with no level count, then `note` and `level` events as the agent works, then `done` with the agent's summary

#### Scenario: No API key
- **WHEN** a client posts a question with no stored trace and no API key is set
- **THEN** it receives one `error` event naming the recorded questions

### Requirement: Validated levels
A level the agent submits SHALL reach the reader only if it keeps or refines every panel of the previous level,
every query passes SLayer validation, and every panel returns rows. Otherwise the agent SHALL receive the errors.

#### Scenario: A level that drops a panel
- **WHEN** the agent submits a level that drops a panel of the previous level without refining it
- **THEN** the level is rejected with an error naming the panel, and nothing new is shown

### Requirement: Plans, never answers
The agent's tools SHALL offer no SQL and no way to put a number in front of the reader: a level is only a title, a
rationale and panels made of SLayer queries.

#### Scenario: Tool surface
- **WHEN** the agent's tools are listed
- **THEN** they are list_models, describe_model, profile_dimension, read_context, validate_query, probe_query, submit_level and finish

### Requirement: Bounded run
One agent run SHALL make at most a fixed number of tool calls and build at most six levels. When a cap is hit, the
levels already accepted SHALL stand.

#### Scenario: Budget exhausted
- **WHEN** the agent calls a tool after its tool-call budget is spent
- **THEN** the call fails, the run ends, and the accepted levels remain

### Requirement: Replayable agent runs
An agent run SHALL be storable as a trace of its notes, tool calls, levels and query results, and a stored trace
SHALL replay with its notes in their recorded order, without an API key or a database.

#### Scenario: Replaying an agent trace
- **WHEN** a client posts the question of a stored agent trace
- **THEN** it receives the trace's notes and levels in recorded order, then `done` with its summary
