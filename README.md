# Galaxy brain UX experiment by Motley

**Ask a data question once. Pull the answer down to think deeper.**

Most data answers come at one depth: a number, or a dashboard. This experiment answers at every depth at once and
lets the reader choose. The answer starts as one sentence and one number. Pull the handle under it, and the next
depth of analysis unlocks: new sentences are written into the text and their charts unfold. A brain on the
handle grows and glows brighter with each depth, from a plain outline at the single number to radiant at the deepest
analysis. Pull up to fold a depth away.

At the top of the answer, an outline lists every depth: what each unlocked one found, and what is still to come.
Each depth's text opens with the question it answers. When a new depth unlocks, the page follows the new section down as it
writes, pauses at its end so you can see how much was added, then glides back to the top of the answer so you can read
the fuller analysis through, with the new sentences highlighted. Each pull unlocks one depth; the next takes another
deliberate pull. It is the same answer at every depth, only deeper, and every number reconciles with the depth
before it.

## An example

"What is our revenue year to date?" on the Jaffle Shop demo database, as recorded in
`src/slayer_zoom/traces/data/agent_revenue_ytd.json`:

| Depth | What it adds | Text it writes in |
|---|---|---|
| 1 · Number | Revenue YTD | "Gross revenue year to date is $2.03M." |
| 2 · Split | + by store | "Brooklyn leads with $1.07M, followed by Philadelphia at $692.8K…" |
| 3 · Mix | + product mix, top products | "Beverages dominate every store's mix…" |
| 4 · Trend and drivers | + month by month, share and order value by store | "…order volume (98,951 orders in Brooklyn) drives the gap." |
| 5 · Analysis | + year over year, month over month | "Every complete month is well above the same month last year…" |

Each depth's sentences go into the existing text, where they belong, not only at the end, and each chart appears right
after the sentence that introduces it.

## How it works

1. **An agent plans the depths.** Claude (`claude-opus-5-5`, on the Anthropic SDK Tool Runner) reads the semantic
   layer and a business context file (`src/slayer_zoom/context/jaffle_shop.md`). It profiles the dimensions it wants
   to split by, then submits depths one at a time.
   - Each depth is a set of [SLayer](https://github.com/MotleyAI/slayer) queries, and each query is a small variation
     on the one before: another dimension, a `time_shift`, a `change_pct`, a `rank`.
   - The system writes no SQL itself, and every number reconciles with the depth before it.
2. **Each depth is checked before anyone sees it.** It must keep or refine every earlier panel, and every query must
   pass SLayer validation and return rows. Accepted depths stream to the browser as they land, with the agent's
   progress notes.
3. **A narrator writes the text.** Claude (`claude-sonnet-5-5`) inserts a sentence or two per depth into the text so
   far, introducing each new chart.
   - Every figure it writes must appear, as rounded, in that depth's result rows. If one doesn't, the narrator gets
     one retry, and then the sentence is dropped.
   - A chart the narrator skips still appears, introduced by its title.
   - For each depth it also writes the question the depth answers, a headline for the outline and a summary of
     the whole answer so far (stored, not shown yet). Their figures go through the same check, against every depth
     up to this one.
4. **The browser does the rest.** All depths arrive with the answer, so pulling never calls the server. The card and
   charts are drawn with [OpenUI](https://www.openui.com/) components.

Numbers reach the reader only from SLayer results; the models plan and word, and never supply a number.

## Run it

```bash
uv sync --all-groups
uv run uvicorn --factory slayer_zoom.api:create_app --reload   # API on http://localhost:8000
```

```bash
cd web && npm install && npm run dev                          # app on http://localhost:5173
```

Ask one of the recorded questions and pull the handle under the answer down. Keyboard: focus the brain, then use the
arrow keys, Page Up/Down, Home or End.

- What is our revenue year to date?
- How did our stores do last month?
- What do our customers buy?

By default the API replays the recorded traces in `src/slayer_zoom/traces/data/`, from their recorded rows. That
needs no database and no API key; `GET /questions` lists them.

### Live mode

To let the agent answer new questions, run against the SLayer Jaffle Shop demo database (built in `.slayer/` on first
run) with an Anthropic API key. A new question costs about $0.25.

```bash
SLAYER_ZOOM_LIVE=1 ANTHROPIC_API_KEY=... uv run uvicorn --factory slayer_zoom.api:create_app
```

To record a new trace, or narrate a stored one again:

```bash
uv run python -m slayer_zoom.api.record "How are our stores doing this year?"
uv run python -m slayer_zoom.api.record --narrate agent_revenue_ytd
```

## Repository

| Path | What's there |
|---|---|
| `src/slayer_zoom/agent` | The agent that plans the depths: tools, budget, checks |
| `src/slayer_zoom/catalog`, `context` | The semantic layer as the agent sees it, and the business context |
| `src/slayer_zoom/narrator` | The narrator and its figure check |
| `src/slayer_zoom/core` | The shared contract: depths, panels, growing text, invariants |
| `src/slayer_zoom/executor`, `traces`, `api` | Running queries, recording and replaying traces, the streaming API |
| `web/src/slider` | The answer card: outline, pull to unlock, the brain, page scrolling |
| `web/src/panels`, `state` | OpenUI panels, and the answer state fed by the stream |

The Python module keeps its original name, `slayer_zoom`.

## Checks

```bash
uv run pytest -q
npm test --prefix web
uv run ruff check src tests
la-typecheck
la-arch-check
```

## Architecture

The repo uses [living-architecture](https://github.com/MotleyAI/living-architecture). A LikeC4 model in
[`architecture/`](architecture/) is also the import law (`la-arch-check`), and the arc42 file next to each element
holds its principles. Changes go through `/la:pr`, which writes an OpenSpec change for each PR.

## Status

Prototype. The milestones are GitHub issues #1–#5, and the original plan is in [`docs/plan.md`](docs/plan.md).

- M1: a walking skeleton with a hand-written ladder.
- M2: the agent plans the depths.
- M3: the narrator writes text that grows in place.
- M4 (in progress): pull to unlock each depth, with the expanding-brain cue, drawn with OpenUI.

## License

MIT
