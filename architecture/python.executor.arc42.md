# Query executor

## Purpose and context

Runs a panel's SLayer query and returns its columns and rows: role, label and display format per column, and
values converted to JSON types. Today it runs on the SLayer Jaffle Shop demo database through the embedded client.

## Building blocks

See the `python` view in `views.c4`.

## Principles

1. The executor and, from #2, the catalog are the only elements that import SLayer. [review]
2. Each distinct query runs at most once per executor: results are cached by query hash. [enforced: test:tests/test_executor.py]
3. The executor converts types (decimals, dates) and never changes a value SLayer returned. [enforced: test:tests/test_executor.py]

## Rationale

Caching by query hash is what keeps a ladder cheap: levels repeat their parents' panels, so most panels of a level
were already computed one level down. The display format the query declares is applied when SLayer leaves a
computed measure without one.
