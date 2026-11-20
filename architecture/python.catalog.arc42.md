# SLayer catalog

## Purpose and context

What the semantic layer offers, read through SLayer: the models with their columns, saved measures and joins, a
profile of any dimension (rows per value, the top value's share, nulls, the date range), and SLayer's own query
validation without running the query. The agent explores the data through this element.

## Building blocks

See the `python` view in `views.c4`.

## Principles

1. The catalog reads the semantic layer only through SLayer: it writes no SQL. [review]
2. The catalog and the executor are the only elements that import SLayer. [enforced: test:tests/test_import_law.py]
3. A profile reports what SLayer counted and caps the distinct values it lists, so a profile stays small on any dimension. [enforced: test:tests/test_catalog.py]

## Rationale

The agent decides which splits are worth showing from profiles: a dimension with one dominant value, or a time
dimension that does not reach back a year, changes the ladder. Keeping profiles and validation in SLayer means the
agent sees the same model the executor runs.
