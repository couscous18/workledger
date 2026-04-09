# Trace To Work

Traces are execution records.
Work needs a higher-level unit.

That is why `WorkUnit` exists.

## Why A Higher-Level Unit Is Necessary

One agent task can contain:

- multiple messages
- several tool calls
- retries
- guardrails
- human review

Those events are useful, but they are not yet the work itself.

`WorkUnit` rolls related observations into one unit that a person can inspect and reason about.

## What `WorkUnit` Preserves

- title and summary
- source span lineage
- evidence refs
- review state
- trust state

## Why Ambiguity Matters

Some traces do not cleanly resolve.

`workledger` keeps that visible through review-needed states instead of pretending every trace already maps to a confident answer.

## What Comes After

Once work has been attributed, you can layer on:

- policy classification
- review queues
- economics

Those are useful, but they are downstream of trace-to-work attribution.
