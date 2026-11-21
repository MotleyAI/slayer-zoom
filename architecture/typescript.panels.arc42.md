# Panel renderers

## Purpose and context

Renders one resolved panel by kind: KPI, bar, table, line and delta, from its columns and rows. The slider places
each panel inline in the answer's text, after the sentence that introduces it.

## Building blocks

See the `typescript` view in `views.c4`.

## Principles

1. A panel formats values and scales marks; it never derives a number to show. [review]
2. Each kind renders from the panel's columns and rows alone. [review]

## Rationale

What the reader sees must match what SLayer returned. Formatting (currency, percent, month names) and scaling bars
to the largest value are presentation; sums, shares and changes come from SLayer queries.
