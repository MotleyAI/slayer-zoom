# Business context

## Purpose and context

The business context the agent reads for a dataset: the glossary that maps the reader's words to models and
measures, the fiscal calendar, the audience, and known caveats of the data. One Markdown file per dataset, today
`jaffle_shop.md`; later the same context can come from Motley memories.

## Building blocks

See the `python` view in `views.c4`.

## Principles

1. The business context depends on no other element, and only reads its own files. [enforced: arch_check:model-truth]
2. Caveats name what the data cannot answer, so the agent leaves those steps out instead of guessing. [review]

## Rationale

The semantic layer says what can be computed; the context says what the reader means and what to distrust. Keeping
it as plain text lets a data team edit it without touching code.
