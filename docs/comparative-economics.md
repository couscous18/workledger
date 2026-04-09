# Comparative Economics

Comparative economics is a supported first-class view, but it is downstream of trace-to-work attribution.

`workledger` first answers:

- what work happened?
- how much evidence supports that interpretation?
- which items still need review?
- what observed spend is attached to that work?

Only after that does `wl compare-costs` estimate alternative deployment costs.

## What It Builds On

`wl compare-costs` is grounded in the attributed work ledger:

- observed token usage from normalized observations
- direct cost captured on source spans when available
- direct, allocated, and total cost attached to rolled `WorkUnit`s
- downstream classification context for interpreting where spend lands

## What It Measures

- observed token usage from normalized observations
- direct cost when the source trace provides it
- work-unit context for the rolled workload

## What It Estimates

- proprietary API assumptions
- open-hosted assumptions
- self-hosted GPU assumptions

These estimates are explicit, editable, and secondary to the core trace-to-work model.
They are useful because the work has already been attributed.
