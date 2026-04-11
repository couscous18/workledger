# Trace To Work

Traces are execution records.
Teams still need a higher-level unit they can review, attribute, and reason about.

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

It creates a durable boundary around the work so downstream decisions attach to something accountable instead of to disconnected spans.

## What `WorkUnit` Preserves

- title and summary
- objective and actor context
- source span lineage
- evidence refs
- review state
- trust state
- direct cost, allocated cost, and total cost

## Why This Matters

Once work is rolled into `WorkUnit`s, teams can ask better questions:

- what did this agent run actually add up to?
- which outputs are costly but still low-trust?
- which items should stay in a review queue instead of being presented as settled?
- where should policy or economics attach?

This is the difference between telemetry detail and accountable work attribution.

## Why Ambiguity Matters

Some traces do not cleanly resolve.

`workledger` keeps that visible through review-needed states instead of pretending every trace already maps to a confident answer.

That reviewability is part of the primitive, not an afterthought.

## What Comes After

Once work has been attributed, you can layer on:

- review queues and overrides
- policy classification
- economics

Those are useful, but they are downstream of trace-to-work attribution.
