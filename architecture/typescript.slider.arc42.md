# Granularity slider

## Purpose and context

The control that moves between levels, and the view of the current level: its rationale and panels, with panels
new at this level marked.

## Building blocks

See the `typescript` view in `views.c4`.

## Principles

1. The slider reads levels and position from answer state and changes them only through `slide`. [review]
2. A panel that a level adds is marked as new, so the reader sees what the step changed. [review]

## Rationale

The slider is the product: the reader should feel each step as the same answer, only finer. Marking what changed
is what makes that legible.
