# Granularity slider

## Purpose and context

A continuous control over the answer's detail, and the answer itself: one text that grows as the control moves,
with each panel inline right after the sentence that introduces it. At position 2.4, level 2 is shown in full and
40% of level 3's added words have appeared, in place; a panel appears once its sentence is complete. Clicking a
level name glides to it.

## Building blocks

See the `typescript` view in `views.c4`.

## Principles

1. The slider reads levels and position from answer state and changes them only through `slide`. [review]
2. Moving right only ever adds words and panels, and moving left only removes them: the reader never sees the text rewritten. [enforced: test:web/src/slider/stretch.test.ts]

## Rationale

The slider is the product: the reader should feel each step as the same answer, only finer. Levels are discrete
(each is a set of SLayer queries), but the text between them is not: revealing the next level's words as the
control moves, and showing a chart as the payoff of the sentence that introduces it, hides the moment new data
appears. Every panel the text never introduces still gets a place, so no data is lost to a missing sentence.
