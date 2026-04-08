# FAQ

## Is this only for accounting or software capex?

No. The core product is trace compression plus work intelligence. Software capex review is one bundled use case, not the homepage story.

## What does it do that a trace viewer does not?

It introduces `WorkUnit` as a ledger layer above raw traces. It rolls spans into units of work, adds cost and trust context, preserves review-worthy ambiguity, and compares deployment-economics scenarios on top of the same normalized data.

## Why lead with agent work ledger?

Because that is the most legible proof of the primitive. Once work is ledgered, the same foundation can support reporting, governance, policy packs, and software capex review.

## Can it compare proprietary APIs with open or self-hosted models?

Yes, as an estimator. WorkLedger measures observed token usage and direct cost, then compares that workload against transparent open-hosted or self-hosted assumptions that you can edit.

## Does this automate accounting decisions?

No. It produces candidate interpretations with evidence, explanations, confidence, and review states.

## Why DuckDB?

Because V1 is local-first and analytical. DuckDB gives simple inspectability, SQL, and Parquet export in one small dependency.
