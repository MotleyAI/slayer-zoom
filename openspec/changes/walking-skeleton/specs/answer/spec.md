## ADDED Requirements

### Requirement: Streamed answer
The API SHALL answer a question with a server-sent event stream: one `ladder` event with the number of levels, one
`level` event per level in order, each carrying every panel with its columns and rows, then a `done` event.

#### Scenario: Demo question
- **WHEN** a client posts "What is our revenue year to date?" to `/answer`
- **THEN** it receives `ladder`, five `level` events with indices 0 to 4, and `done`

#### Scenario: Other question before the agent exists
- **WHEN** a client posts any other question
- **THEN** it receives one `error` event naming the demo question

### Requirement: Free slide
Moving the slider SHALL NOT call the server, an LLM or a database.

#### Scenario: Sliding after an answer
- **WHEN** the reader moves the slider any number of times after asking
- **THEN** the server has been called once, for the question

### Requirement: Replay without credentials
A recorded trace SHALL answer every panel of its ladder without SLayer, a database or an API key, and SHALL refuse
a query it did not record.

#### Scenario: Replaying the demo trace
- **WHEN** the API runs without `SLAYER_ZOOM_LIVE`
- **THEN** every level resolves from the recorded results

### Requirement: Splits reconcile
In the demo ladder, the store split SHALL sum to the total revenue, within rounding.

#### Scenario: Revenue by store
- **WHEN** the trace is loaded
- **THEN** the sum of revenue by store equals revenue year to date
