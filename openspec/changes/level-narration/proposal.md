## Why

The slider moved in steps: each level swapped in new panels at once. The answer should feel continuous, the same
answer only finer, with no visible jump when new data appears. Text that grows in place can carry that: as the
reader drags, the next level's words appear inside the existing text, and each new chart arrives as the payoff of
the sentence that introduces it.

## What Changes

- `core`: stretchtext types (`Segment`, `Insertion`), `insert_segments`, `text_at`, the expansion invariant and
  `ungrounded_numbers`, which finds figures in a text that no result value rounds to.
- `narrator` (new): Claude Sonnet 5.5 with structured output writes each level as insertions into the text so far,
  introducing each new panel exactly once. Ungrounded figures get one retry, then are dropped; a panel the draft
  does not introduce gets its title.
- `traces`: traces carry the narration.
- `api`: replay sends a `narration` event after each level; a live run narrates each level in a second thread as
  the agent's levels land. `python -m slayer_zoom.api.record` records agent runs with narration, adds narration to
  a stored trace (`--narrate NAME`), or re-records the hand-written ladder (`--handwritten`).
- web `state`: narration and a continuous position, clamped to the last level with text.
- web `slider`: a continuous control; the answer is one growing text with panels inline after the sentence that
  introduces them; words fade in as they are revealed; clicking a level name glides to it.

## Impact

- Architecture: new element `narrator` with arrows api→narrator and narrator→core; its arc42 file; system
  principle 4 (numbers in narration appear in result rows) is enforced; the slider and panels arc42 describe the
  continuous control and inline panels.
- The stored traces are narrated once (a few cents each); replay stays free and needs no key.
