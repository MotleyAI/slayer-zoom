# Resizable answer

## Purpose and context

The answer and its depth control in one: an OpenUI card that always shows the answer at its current depth, in full,
with each panel inline right after the sentence that introduces it. The card opens with an outline of every depth (the
headline of each unlocked depth, the title of each depth still to come; clicking one goes there). Each depth's first
sentence carries its question as a heading. The reader pulls the handle on the card's bottom
edge down to unlock the next depth: the pull opens room while a brain on the handle charges, and past a threshold the
next depth writes itself into the text, word by word in place, and its charts unfold. Pulling up folds a depth away.
The brain grows and glows brighter at each depth; the depth names live in its tooltip and accessible label. Near the
bottom of the window the page scrolls, so a pull can go on. Once a new depth unlocks, the page tours it: it follows the
new section down as it writes, pauses at its end, then glides back up to the start of the answer at a readable pace,
so the reader sees how much was added and can read the fuller analysis from the top. The text the depth added stays
marked until a few seconds after. Any scrolling of the reader's own ends the tour.

## Building blocks

See the `typescript` view in `views.c4`.

## Principles

1. The answer reads levels and position from answer state and changes them only through `slide`. [review]
2. Unlocking a depth only ever adds words and panels, and folding it only removes them: the reader never sees the text rewritten. [enforced: test:web/src/slider/stretch.test.ts]
3. Each depth always shows the same complete text, and a press unlocks at most one depth, only past the threshold. [enforced: test:web/src/slider/pull.test.ts]

## Rationale

Each depth should feel like a new, deeper answer, not more of the same text uncovered. Levels are discrete (each is
a set of SLayer queries), so the control is discrete too: a pull is a deliberate ask for the next depth, and the
charge and the brain make the step visible before it happens. Writing the new sentences into the existing text, and
unfolding each chart after the sentence that introduces it, keeps the answer one text that only grows. The outline
answers "where am I in this analysis?": it shows what each step found and what is still to come. A deeper depth is a
fuller analysis, best read from the top: the tour shows its extent first, then brings the reader back there with
what is new marked. One depth per press is a hard cushion against unlocking more than the reader meant to. Every panel the text never introduces still gets a place, so
no data is lost to a missing sentence.
