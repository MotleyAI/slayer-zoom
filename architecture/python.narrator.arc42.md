# Level narrator

## Purpose and context

Writes the answer's text as stretchtext. When a level lands, the narrator (Claude Sonnet 5.5, effort low, with
structured output) inserts one to three short sentences or clauses into the text so far, and introduces each of
the level's new panels with exactly one of them. The text is stored with the trace and replays without an API key.

## Building blocks

See the `python` view in `views.c4`.

## Principles

1. Grounded: every number in the text appears, as rounded, in the result rows of its level. A draft with an ungrounded figure gets one retry with the problems listed; what still fails is dropped. [enforced: test:tests/test_narrator.py]
2. Expands, never rewrites: a level only inserts segments into the previous text; earlier segments stay unchanged and in order. [enforced: test:tests/test_narrator.py]
3. Every new panel gets a place: a panel the draft does not introduce is introduced by its title. [enforced: test:tests/test_narrator.py]
4. The narrator and the agent are the only elements that import the Anthropic SDK. [enforced: test:tests/test_import_law.py]

## Rationale

Levels are discrete, but the reader's experience should not be: text that grows in place lets the slider move
continuously and makes each new chart the natural next thing to read. Writing per level, as the agent's levels
land, keeps the text grounded in exactly the rows the reader can see at that point. Sonnet is fast enough to keep
up with the agent.
