# FAQ

## Is this an accounting tool?

No. The core contribution is trace-to-work attribution. Software capex review stays in the repo as a downstream example.

## What does it do that a trace viewer does not?

It turns raw traces into `WorkUnit`s with evidence, lineage, review-needed states, and work-attached cost. A trace viewer shows execution detail; `workledger` makes the work legible.

## Does it attach cost to work or only to raw spans?

It attaches cost to work. `ObservationSpan` preserves source-level direct cost, and `WorkUnit` carries direct, allocated, and total cost so teams can reason about spend at the work level.

## Why lead with Hugging Face public datasets?

Because public traces are now a practical way to show the trace-to-work primitive in the open-agent ecosystem.

## Is economics still supported?

Yes. It is available through reports and `wl compare-costs`, and it stays grounded in the attributed work ledger. It is downstream of the core trace-to-work layer, but it is still a real supported capability.

## Does it collect traces?

No. It consumes traces. `workledger` is not a tracing backend.
