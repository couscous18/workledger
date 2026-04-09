# FAQ

## Is this an accounting tool?

No. The core contribution is trace-to-work attribution. Software capex review stays in the repo as a downstream example.

## What does it do that a trace viewer does not?

It turns raw traces into `WorkUnit`s with evidence, lineage, and review-needed states. A trace viewer shows execution detail; `workledger` makes the work legible.

## Why lead with Hugging Face public datasets?

Because public traces are now a practical way to show the missing layer between traces and work in the open-agent ecosystem.

## Is economics still supported?

Yes. It is still available through reports and `wl compare-costs`, but it is a downstream interpretation, not the lead story.

## Does it collect traces?

No. It consumes traces. `workledger` is not a tracing backend.
