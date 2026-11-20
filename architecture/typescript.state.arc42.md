# Answer state

## Purpose and context

Holds the answer on the client: the question, the levels as they stream in over SSE, the slider position, and
errors. Exposes `ask`, `slide` and a React hook.

## Building blocks

See the `typescript` view in `views.c4`.

## Principles

1. Asking is the only action that calls the server. Sliding is local. [enforced: test:web/src/state/store.test.ts]
2. The slider position stays within the levels that have arrived. [enforced: test:web/src/state/store.test.ts]
3. Answer state depends on no other element of the web app. [enforced: arch_check:model-truth]

## Rationale

All levels arrive with one answer, so moving the slider is instant and costs nothing. Keeping the server call in one
place makes that property testable.
